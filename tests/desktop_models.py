"""Verify desktop model switching in an empty test checkout."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import joblib

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_MODEL = ROOT / "data/desktop/active-model.skops"
sys.path.insert(0, str(ROOT / "src"))


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
    if CUSTOM_MODEL.exists():
        raise ValueError("Use an empty test checkout to preserve your selected model.")

    default = bridge("info")["result"]
    assert default["is_default"]
    assert default["metrics"]["n"] == 200
    message = "Congratulations! Claim your free cash prize and reply WIN now."
    original = bridge("predict", text=message)["result"]
    assert original["label"] == "spam"

    try:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "variant.joblib"
            candidate = directory / "Custom model café.skops"
            invalid = directory / "invalid.skops"
            invalid.write_bytes(b"Not a model bundle")
            assert "compatible" in bridge("install", path=str(invalid))["error"]
            assert bridge("info")["result"] == default

            bundle = joblib.load(ROOT / "models/candidate.joblib")
            bundle["threshold"] = 1.0
            joblib.dump(bundle, source)
            subprocess.run(
                [sys.executable, str(ROOT / "electron/export_model.py"), str(source), str(candidate)],
                check=True,
            )
            installed = bridge("install", path=str(candidate))["result"]
            assert installed == {"threshold": 1.0, "metrics": None, "is_default": False}
            assert bridge("info")["result"] == installed
            assert CUSTOM_MODEL.read_bytes() == candidate.read_bytes()
            assert bridge("predict", text=message)["result"] == {
                **original, "threshold": 1.0, "label": "legitimate"
            }

            assert "compatible" in bridge("install", path=str(invalid))["error"]
            assert bridge("info")["result"] == installed
    finally:
        assert bridge("restore")["result"] == default

    assert not CUSTOM_MODEL.exists()
    assert bridge("predict", text=message)["result"] == original
    print("Verified bundled model, custom export and install, invalid-file handling and default restore.")


if __name__ == "__main__":
    main()
