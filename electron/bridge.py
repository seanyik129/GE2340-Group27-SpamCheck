"""Local JSON bridge for the frozen report model."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def run(request):
    evidence = json.loads((ROOT / "results/new200/metrics.json").read_text(encoding="utf-8"))
    model_path = ROOT / "data/student/expanded250/candidate.joblib"
    if not model_path.is_file():
        raise ValueError("The validated expanded250 model is missing. Open the local project containing the model.")
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != evidence["model_sha256"]:
        raise ValueError("The model file differs from the frozen model used in the report.")
    if request["action"] == "info":
        return {"threshold": evidence["threshold"], "metrics": evidence["metrics"]}
    if request["action"] != "predict":
        raise ValueError("Unknown request.")
    import joblib
    from spamcheck.models import predict_bundle
    bundle = joblib.load(model_path)
    if bundle["threshold"] != evidence["threshold"]:
        raise ValueError("The model threshold differs from the report.")
    result = predict_bundle(bundle, request["text"])
    return {key: result[key] for key in (
        "label", "probability", "threshold", "explanation", "language_note"
    )}


if __name__ == "__main__":
    try:
        response = {"result": run(json.load(sys.stdin))}
    except ValueError as error:
        response = {"error": str(error)}
    except Exception:
        response = {"error": "Prediction could not run. Check the project Python environment."}
    print(json.dumps(response, ensure_ascii=True))
