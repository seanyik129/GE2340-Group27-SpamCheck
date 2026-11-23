# SpamCheck desktop

Follow the [Windows or macOS setup](../README.md#desktop-setup) from the repository root. The main process uses the root's `.venv` on each platform. Set `SPAMCHECK_PYTHON` to the path of a compatible Python interpreter to use a different environment.

The preload exposes message checking and the model picker. The Python bridge checks the frozen model's fingerprint and threshold before inference or installation.
