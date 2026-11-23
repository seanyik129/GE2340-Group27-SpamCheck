"""Local JSON bridge for model selection and inference."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = ROOT / "models/candidate.joblib"
CUSTOM_MODEL_PATH = ROOT / "data/desktop/active-model.skops"
EVIDENCE_PATH = ROOT / "results/new200/metrics.json"
sys.path.insert(0, str(ROOT / "src"))

def save_custom_model(model_bytes):
    CUSTOM_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(dir=CUSTOM_MODEL_PATH.parent, suffix=".skops", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(model_bytes)
        temporary_path.replace(CUSTOM_MODEL_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_default_model():
    import joblib

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    model_bytes = DEFAULT_MODEL_PATH.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != evidence["model_sha256"]:
        raise ValueError("The default model does not match the report. Restore models/candidate.joblib from Git.")
    bundle = joblib.load(BytesIO(model_bytes))
    if bundle["threshold"] != evidence["threshold"]:
        raise ValueError("The default model threshold differs from the report.")
    return bundle, {
        "threshold": evidence["threshold"],
        "metrics": evidence["metrics"],
        "is_default": True,
        "model_sha256": evidence["model_sha256"],
    }


def load_custom_model(model_bytes):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from skops.io import loads

    trusted_types = ["spamcheck.preprocessing.TextColumn", "spamcheck.preprocessing.StructuralColumn"]
    try:
        bundle = loads(model_bytes, trusted=trusted_types)
    except Exception as error:
        raise ValueError("Choose a compatible SpamCheck .skops model exported using the project dependencies.") from error

    model = bundle.get("model") if isinstance(bundle, dict) else None
    classifier = model.named_steps.get("classifier") if isinstance(model, Pipeline) else None
    if (not isinstance(classifier, LogisticRegression)
            or list(getattr(classifier, "classes_", [])) != [0, 1]
            or not isinstance(bundle.get("threshold"), (int, float))
            or not 0 <= bundle["threshold"] <= 1):
        raise ValueError("The model must be a fitted SpamCheck classifier with a decision threshold between 0 and 1.")
    return bundle


def custom_model_info(bundle):
    return {"threshold": bundle["threshold"], "metrics": None, "is_default": False}


def run(request):
    from spamcheck.models import predict_bundle, prepare_for_bundle

    action = request["action"]
    if action == "install":
        path = Path(request["path"])
        if path.suffix.lower() != ".skops":
            raise ValueError("Choose an exported SpamCheck .skops model.")
        model_bytes = path.read_bytes()
        bundle = load_custom_model(model_bytes)
        predict_bundle(bundle, "SpamCheck model check")
        save_custom_model(model_bytes)
        return custom_model_info(bundle)

    if action not in {"info", "predict", "restore"}:
        raise ValueError("Unknown request.")
    if action == "restore" or not CUSTOM_MODEL_PATH.exists():
        bundle, info = load_default_model()
    else:
        bundle = load_custom_model(CUSTOM_MODEL_PATH.read_bytes())
        info = custom_model_info(bundle)
    if action == "predict":
        result = predict_bundle(bundle, request["text"])
        return {key: result[key] for key in (
            "label", "probability", "threshold", "explanation", "language_note"
        )}

    prepare_for_bundle(bundle, "SpamCheck")
    if action == "restore":
        CUSTOM_MODEL_PATH.unlink(missing_ok=True)
    return info


if __name__ == "__main__":
    try:
        response = {"result": run(json.load(sys.stdin.buffer))}
    except FileNotFoundError as error:
        path = Path(error.filename)
        name = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        response = {"error": f"Missing {name}. Restore the file or clone the repository again."}
    except ImportError:
        response = {"error": "Python dependencies could not load. Install them using the setup steps in README.md."}
    except PermissionError:
        response = {"error": "SpamCheck could not access the model file. Check access to the file and project folder."}
    except ValueError as error:
        response = {"error": str(error)}
    except Exception:
        response = {"error": "The local model could not run. Check the model file and desktop setup."}
    print(json.dumps(response, ensure_ascii=True))
