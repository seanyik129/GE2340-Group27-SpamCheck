"""Local JSON bridge for the frozen report model."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data/student/expanded250/candidate.joblib"
EVIDENCE_PATH = ROOT / "results/new200/metrics.json"
sys.path.insert(0, str(ROOT / "src"))


def install_model(model_bytes):
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(dir=MODEL_PATH.parent, suffix=".joblib", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(model_bytes)
        temporary_path.replace(MODEL_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def run(request):
    action = request["action"]
    if action not in {"info", "predict", "install"}:
        raise ValueError("Unknown request.")
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    model_path = Path(request["path"]) if action == "install" else MODEL_PATH
    if not model_path.is_file():
        raise ValueError("The group model is missing. Choose candidate.joblib from the Group 27 model package.")
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != evidence["model_sha256"]:
        raise ValueError("This file does not match the report model. Choose the original Group 27 candidate.joblib.")

    import joblib
    from spamcheck.models import predict_bundle, prepare_for_bundle

    bundle = joblib.load(BytesIO(model_bytes))
    if bundle["threshold"] != evidence["threshold"]:
        raise ValueError("The model threshold differs from the report.")
    if action == "predict":
        result = predict_bundle(bundle, request["text"])
        return {key: result[key] for key in (
            "label", "probability", "threshold", "explanation", "language_note"
        )}

    prepare_for_bundle(bundle, "SpamCheck")
    if action == "install" and model_path.resolve() != MODEL_PATH.resolve():
        install_model(model_bytes)
    return {"threshold": evidence["threshold"], "metrics": evidence["metrics"]}


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
