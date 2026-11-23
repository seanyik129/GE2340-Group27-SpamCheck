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

### Load the report model once

Extract the group-only model package provided by a team member. Open SpamCheck, select **Load group model…**, and choose the extracted **candidate.joblib**. SpamCheck verifies the file against the report’s model fingerprint and saves a local copy at `data/student/expanded250/candidate.joblib`. Subsequent launches use that copy. The group shares this file separately because its fitted vocabulary includes donated messages.

Use **Try a promotion** or **Try a campus notice**, then select **Check message**. **Validation results** shows the frozen model’s 200-message evaluation. Inference runs locally.

## Source guide

| Path | Contents |
| --- | --- |
| `electron/` | Desktop interface, Electron main and preload processes, and the local JSON bridge |
| `src/spamcheck/` | Inference preprocessing and model scoring |
| `data/reference/iana-tlds.txt` | Pinned [IANA domain suffix snapshot](https://data.iana.org/TLD/tlds-alpha-by-domain.txt) for URL masking |
| `results/new200/metrics.json` | Aggregate evaluation counts, measures, and model fingerprint |
