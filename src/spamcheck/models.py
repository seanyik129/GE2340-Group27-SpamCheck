import re
import time
from pathlib import Path
import numpy as np
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from .preprocessing import TextColumn, StructuralColumn, prepare

# Fixed before inspecting outcomes. Rules are NOT a probability model.
RULES = [(r"\bfree\b", 1.0, "free"), (r"\b(?:win|won|winner|prize|jackpot)\b", 2.0, "prize / winner"),
         (r"\bclaim\b", 2.0, "claim"), (r"\b(?:urgent|limited|expires?)\b", 1.0, "urgency"),
         (r"\b(?:cash|credit|loan|bonus)\b", 1.0, "money promotion"),
         (r"\b(?:offer|discount|subscribe|unsubscribe|reply stop)\b", 1.5, "bulk promotion"),
         (r"\b(?:call now|text now|click|apply now)\b", 1.5, "call to action")]

def rule_details(record):
    items = [{"feature": name, "contribution": weight} for regex, weight, name in RULES if re.search(regex, record["text"])]
    if record["structural"][4] > 0: items.append({"feature": "URL present", "contribution": 0.5})
    if record["structural"][5] > 0: items.append({"feature": "shortened URL", "contribution": 1.0})
    if record["structural"][7] > 0: items.append({"feature": "currency symbol", "contribution": 0.5})
    return items

def rule_scores(records):
    return np.array([sum(r["contribution"] for r in rule_details(x)) for x in records])

def make_b(C=4.0, class_weight="balanced", variant="full"):
    branches = [("word", Pipeline([("text", TextColumn()), ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=15000, sublinear_tf=True))]))]
    weights = {"word": 1.0}
    if variant != "word":
        branches.append(("char", Pipeline([("text", TextColumn()), ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), min_df=2, max_features=30000, sublinear_tf=True))])))
        weights["char"] = 0.7
    if variant == "full":
        branches.append(("structure", StructuralColumn())); weights["structure"] = 0.5
    return Pipeline([("features", FeatureUnion(branches, transformer_weights=weights)),
                     ("classifier", LogisticRegression(C=C, class_weight=class_weight, solver="liblinear", max_iter=2000, random_state=27))])

class MiniLMEncoder:
    """Official fixed FP32 ONNX encoder; attention-mask mean pooling + L2."""
    def __init__(self, directory):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        directory = Path(directory)
        opts = ort.SessionOptions(); opts.intra_op_num_threads = 2; opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory/"model.onnx"), sess_options=opts, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.from_file(str(directory/"tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self.inputs = {x.name for x in self.session.get_inputs()}

    def encode(self, texts, batch_size=32):
        batches=[]
        for start in range(0,len(texts),batch_size):
            enc = self.tokenizer.encode_batch(texts[start:start+batch_size])
            feed={"input_ids":np.asarray([e.ids for e in enc],dtype=np.int64),
                  "attention_mask":np.asarray([e.attention_mask for e in enc],dtype=np.int64),
                  "token_type_ids":np.asarray([e.type_ids for e in enc],dtype=np.int64)}
            hidden=self.session.run(None,{k:v for k,v in feed.items() if k in self.inputs})[0]
            if hidden.ndim == 3:
                mask=feed["attention_mask"][:,:,None]
                vectors=(hidden*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1)
            else: vectors=hidden
            vectors=vectors/np.maximum(np.linalg.norm(vectors,axis=1,keepdims=True),1e-12)
            batches.append(vectors.astype(np.float32))
            if len(texts)>64: print(f"  encoded {min(start+batch_size,len(texts))}/{len(texts)}",flush=True)
        return np.vstack(batches)

def explain_b(model, record, top_k=8):
    features=model.named_steps["features"]
    x=features.transform([record]).tocsr()
    classifier=model.named_steps["classifier"]
    coefficients=classifier.coef_[0]
    names=features.get_feature_names_out()
    values=x.data*coefficients[x.indices]
    contributions=[{"feature":str(names[i]),"contribution":float(v)} for i,v in zip(x.indices,values)]
    positive=sorted((r for r in contributions if r["contribution"]>0),key=lambda r:-r["contribution"])
    negative=sorted((r for r in contributions if r["contribution"]<0),key=lambda r:r["contribution"])
    intercept=float(classifier.intercept_[0]); total=intercept+sum(r["contribution"] for r in contributions)
    logit=float(model.decision_function([record])[0])
    if not np.isclose(total,logit,atol=1e-8): raise RuntimeError("Explanation did not reconstruct the model logit.")
    return {"positive":positive[:top_k],"negative":negative[:top_k],"intercept":intercept,
            "all_feature_sum":float(values.sum()),"logit":logit,
            "unshown_contribution":float(values.sum()-sum(r["contribution"] for r in positive[:top_k]+negative[:top_k]))}

def predict_bundle(bundle, text):
    record=prepare_for_bundle(bundle,text)
    start=time.perf_counter()
    probability=float(bundle["model"].predict_proba([record])[0,1])
    explanation=explain_b(bundle["model"],record)
    result={"label":"spam" if probability>=bundle["threshold"] else "legitimate",
            "probability":probability,"threshold":bundle["threshold"],"explanation":explanation,
            "rule_score":float(rule_scores([record])[0]),"rule_threshold":bundle["rule_threshold"],
            "masked_text":record["text"],"elapsed_ms":(time.perf_counter()-start)*1000}
    letters=[c for c in text if c.isalpha()]
    result["language_note"]="English benchmark only; this message may be outside the evaluated language domain." if letters and sum(ord(c)<128 for c in letters)/len(letters)<0.8 else ""
    return result

def prepare_for_bundle(bundle,text):
    version=bundle.get('preprocessing','legacy-v1')
    if version=='legacy-v1':return prepare(text)
    if version=='iana-v2':
        from .preprocessing_v2 import prepare_v2
        if bundle.get('iana_sha256'):
            import hashlib
            path=Path(__file__).resolve().parents[2]/'data/reference/iana-tlds.txt'
            if hashlib.sha256(path.read_bytes()).hexdigest()!=bundle['iana_sha256']:
                raise ValueError('IANA snapshot differs from training; restore the pinned snapshot.')
        return prepare_v2(text)
    raise ValueError('Unknown model preprocessing version: '+str(version))

def load_release(root,release=None):
    import json,joblib
    root=Path(root)
    if release is None:
        pointer=root/'artifacts/active_release.json'
        release=json.loads(pointer.read_text(encoding='utf-8'))['release'] if pointer.exists() else 'v1'
    if release not in {'v1','v2'}:raise ValueError('Release must be v1 or v2.')
    art=root/'artifacts' if release=='v1' else root/'artifacts/v2'
    result=root/'results' if release=='v1' else root/'results/v2'
    return joblib.load(art/'model_b.joblib'),result,release
