# SpamCheck

SpamCheck is GE2340 Group 27’s Windows desktop prototype for explainable English spam detection. The Electron interface sends message text to a local Python bridge, which runs the validated word and character TF-IDF logistic regression model. The interface displays a spam score, the decision cutoff, and signed contributions from the text features.

## Desktop setup

Use Windows, Python 3.12, and Node.js 22.12 or later. From the repository root:

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location electron
npm ci
npm exec -- install-electron
Set-Location ..
```

For a run with the evaluated classifier, use the group’s authorized copy of the frozen model at `data/student/expanded250/candidate.joblib`. The model contains a vocabulary fitted on donated messages and is kept in the group’s private project. The bridge checks the model hash and decision threshold against the aggregate evaluation record when it loads the model.

Open **Start SpamCheck.cmd**. Use **Try a promotion** or **Try a campus notice**, then select **Check message**. **Validation results** shows the stored measures for the frozen model’s 200-message evaluation.

## Source guide

| Path | Contents |
| --- | --- |
| `electron/` | Desktop interface, Electron main and preload processes, and the local JSON bridge |
| `src/spamcheck/` | Inference preprocessing and model scoring |
| `data/reference/iana-tlds.txt` | Pinned [IANA domain suffix snapshot](https://data.iana.org/TLD/tlds-alpha-by-domain.txt) for URL masking |
| `results/new200/metrics.json` | Aggregate evaluation counts, measures, and model fingerprint |
