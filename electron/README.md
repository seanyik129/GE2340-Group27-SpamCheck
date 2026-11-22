# SpamCheck desktop

Open the **SpamCheck** Windows shortcut or double-click **Start SpamCheck.cmd**
in the project folder. The demo uses the local Python environment and the
expanded250 model verified against the report's model hash and threshold.

For a fresh Windows checkout with Node 22.12+ and the project Python
environment, run these commands from the electron directory:

```powershell
npm ci
npm exec -- install-electron
```

Run **Start SpamCheck.cmd** from the project root. The model must be present at
`data/student/expanded250/candidate.joblib`. That file contains a fitted
vocabulary and stays in the group's private project. The app uses local Python
inference and accepts message text through standard input.

For the recording, select **Try a promotion** and **Check message**, then
repeat with **Try a campus notice**. **Validation results** shows the held-out
confusion counts and metrics.
