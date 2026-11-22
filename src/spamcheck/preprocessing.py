"""Identical train/inference preprocessing; raw structural values precede masking."""
import hashlib
import re
import unicodedata
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", re.I)
URL = re.compile(r"(?:https?://|www\.)\S+|\b(?:[a-z0-9-]+\.)+(?:com|org|net|edu|info|biz|io|co|uk|hk)(?:/[^\s]*)?\b", re.I)
PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{5,}\d(?!\w)")
LONG_NUMBER = re.compile(r"\b\d{5,}\b")
SHORT_URL = re.compile(r"\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd)\b", re.I)
STRUCTURAL_NAMES = ["log message length", "digit ratio", "uppercase ratio", "exclamation count", "URL count", "shortened URL present", "phone or long number present", "currency symbol count"]

def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())

def mask_contacts(text):
    text = EMAIL.sub(" EMAILTOKEN ", normalized(text))
    text = URL.sub(" URLTOKEN ", text)
    text = PHONE.sub(lambda m: " PHONETOKEN " if sum(c.isdigit() for c in m[0]) >= 7 else m[0], text)
    return " ".join(LONG_NUMBER.sub(" NUMBERTOKEN ", text).split())

def prepare(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter a non-empty message.")
    if len(text) > 10000:
        raise ValueError("Messages must be at most 10,000 characters.")
    raw = normalized(text)
    n = max(len(raw), 1)
    letters = sum(c.isalpha() for c in raw)
    phones = any(sum(c.isdigit() for c in m[0]) >= 7 for m in PHONE.finditer(raw)) or bool(LONG_NUMBER.search(raw))
    structural = [float(np.log1p(n)/8), sum(c.isdigit() for c in raw)/n,
                  sum(c.isupper() for c in raw)/max(letters, 1), min(raw.count("!"),10)/10,
                  min(len(URL.findall(raw)),5)/5, float(bool(SHORT_URL.search(raw))),
                  float(phones), min(sum(raw.count(c) for c in "$£€"),5)/5]
    return {"text": mask_contacts(raw).lower(), "structural": structural}

def canonical(text):
    safe = mask_contacts(text).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", re.sub(r"\d+", " number ", safe)).split())

def text_id(text):
    return hashlib.sha256(normalized(text).lower().encode("utf-8")).hexdigest()[:20]

class TextColumn(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        return [r["text"] for r in X]
    def get_feature_names_out(self, input_features=None):
        return np.array(["text"], dtype=object)

class StructuralColumn(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        return np.asarray([r["structural"] for r in X], dtype=np.float64)
    def get_feature_names_out(self, input_features=None):
        return np.asarray(STRUCTURAL_NAMES, dtype=object)
