# SpamCheck desktop

Follow the [Windows or macOS setup](../README.md#desktop-setup) from the repository root. The main process uses the root's `.venv` on each platform. Set `SPAMCHECK_PYTHON` to the path of a compatible Python interpreter to use a different environment.

The preload exposes message checking, model selection, and restoring the default. The Python bridge verifies the bundled model's fingerprint and threshold. For replacement models, it reads compatible `.skops` bundles using the project's transformer types.
