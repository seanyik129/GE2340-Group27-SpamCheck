# SpamCheck

SpamCheck is GE2340 Group 27’s desktop prototype for explainable English spam detection. It runs on Windows and macOS with the same frozen word and character TF-IDF logistic regression model used in the report. It displays a spam score, the decision cutoff, and signed contributions from the text features.

## Desktop setup

Install Python 3.12 and Node.js 22.12 or later. Use 64-bit versions built for your processor. Run these commands from the repository root.

### macOS (Apple silicon or Intel)

```sh
python3.12 -m venv .venv
./.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
npm --prefix electron ci
npm --prefix electron start
```

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
npm.cmd --prefix electron ci
npm.cmd --prefix electron start
```

After setup, rerun the last command to open the app. On Windows you can also double-click **Start SpamCheck.cmd**.

### Default and custom models

SpamCheck automatically loads the bundled Group 27 report model. The first successful load opens a notice with instructions for switching models.

First launch can take longer while Python prepares the model. If loading fails, select **Retry loading**.

Select **Change model…** and open a compatible SpamCheck `.skops` file. The selected model stays active after you restart the app. Select **Use default model** to return to the Group 27 model. The 200-message validation results apply to the default model.

To export a trusted SpamCheck training bundle, use the project’s Python environment. Use `.\.venv\Scripts\python.exe` on Windows in place of `./.venv/bin/python`.

```
./.venv/bin/python electron/export_model.py path/to/candidate.joblib alternative.skops
```

Use **Try a promotion** or **Try a campus notice**, then select **Check message**. Inference runs locally.

## Source guide

| Path | Contents |
| --- | --- |
| `electron/` | Desktop interface, Electron main and preload processes, and the local JSON bridge |
| `src/spamcheck/` | Inference preprocessing and model scoring |
| `models/candidate.joblib` | Frozen Group 27 report model |
| `data/reference/iana-tlds.txt` | Pinned [IANA domain suffix snapshot](https://data.iana.org/TLD/tlds-alpha-by-domain.txt) for URL masking |
| `results/new200/metrics.json` | Aggregate evaluation counts, measures, and model fingerprint |
