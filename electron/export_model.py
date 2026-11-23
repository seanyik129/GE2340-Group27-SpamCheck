"""Export a trusted SpamCheck training bundle for the desktop model picker."""
from argparse import ArgumentParser
from pathlib import Path

import joblib
from skops.io import dumps

from bridge import load_custom_model
from spamcheck.models import predict_bundle


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="A trusted .joblib model from the SpamCheck training project")
    parser.add_argument("destination", type=Path, help="The new .skops file")
    args = parser.parse_args()
    if args.destination.suffix.lower() != ".skops":
        parser.error("The destination must end in .skops.")

    model_bytes = dumps(joblib.load(args.source))
    predict_bundle(load_custom_model(model_bytes), "SpamCheck model check")
    args.destination.write_bytes(model_bytes)
    print(f"Exported {args.destination}")


if __name__ == "__main__":
    main()
