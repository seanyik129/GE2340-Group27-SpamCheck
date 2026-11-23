"""Test model import in a disposable checkout with handwritten messages."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import joblib
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "results/new200/metrics.json"
MODEL_PATH = ROOT / "data/student/expanded250/candidate.joblib"
sys.path.insert(0, str(ROOT / "src"))

from spamcheck.models import make_b, predict_bundle
from spamcheck.preprocessing_v2 import prepare_v2


def bridge(action, **fields):
    completed = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", str(ROOT / "electron/bridge.py")],
        input=json.dumps({"action": action, **fields}, ensure_ascii=False),
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def main():
    if MODEL_PATH.exists():
        raise ValueError("Use an empty test checkout to avoid replacing an installed model.")

    training = [
        ("Claim your free cash prize today. Reply WIN to receive your reward!", 1),
        ("Congratulations, claim your free prize! Enter now to win a cash reward.", 1),
        ("Win a cash prize today! Reply WIN to claim your free reward.", 1),
        ("Our project group meets at the library tomorrow. Bring your notes.", 0),
        ("Please bring the project notes to our group meeting at the library.", 0),
        ("Our project group will meet at the library at 3 pm.", 0),
    ]
    model = make_b(variant="text")
    model.fit([prepare_v2(text) for text, _ in training], [label for _, label in training])
    bundle = {
        "model": model,
        "threshold": 0.5,
        "rule_threshold": 0.0,
        "preprocessing": "iana-v2",
        "iana_sha256": hashlib.sha256((ROOT / "data/reference/iana-tlds.txt").read_bytes()).hexdigest(),
    }
    samples = [
        "Win a free prize! Reply WIN to claim your cash reward today.",
        "The project group meets at the library after class. Bring your notes.",
    ]
    expected = [1, 0]
    labels = [int(predict_bundle(bundle, text)["label"] == "spam") for text in samples]
    tn, fp, fn, tp = map(int, confusion_matrix(expected, labels, labels=[0, 1]).ravel())
    precision, recall, f1, _ = precision_recall_fscore_support(
        expected, labels, average="binary", zero_division=0
    )
    metrics = {
        "n": 2, "spam_n": 1, "legitimate_n": 1, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1, "false_positive_rate": float(fp),
    }

    with TemporaryDirectory() as temporary:
        directory = Path(temporary)
        invalid = directory / "wrong.joblib"
        invalid.write_bytes(b"Incorrect model file")
        assert "does not match" in bridge("install", path=str(invalid))["error"]
        assert not MODEL_PATH.exists()

        candidate = directory / "model fixture café.joblib"
        joblib.dump(bundle, candidate)
        blob = candidate.read_bytes()
        EVIDENCE_PATH.write_text(json.dumps({
            "model_sha256": hashlib.sha256(blob).hexdigest(),
            "threshold": bundle["threshold"],
            "metrics": metrics,
        }), encoding="utf-8")
        assert bridge("install", path=str(candidate)) == bridge("info") == {
            "result": {"threshold": bundle["threshold"], "metrics": metrics}
        }
        assert MODEL_PATH.read_bytes() == blob
        assert "does not match" in bridge("install", path=str(invalid))["error"]
        assert MODEL_PATH.read_bytes() == blob

    print("Model import passed with a synthetic fixture in the test checkout.")


if __name__ == "__main__":
    main()
