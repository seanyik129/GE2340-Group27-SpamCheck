const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const root = path.resolve(__dirname, '..');
const page = path.join(__dirname, 'index.html');
const python = process.env.SPAMCHECK_PYTHON || [
  path.join(root, '.venv', 'Scripts', 'python.exe'),
  path.resolve(root, '../../work/ge2340-venv/Scripts/python.exe')
].find(file => fs.existsSync(file)) || 'python';

function request(action, text) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, ['-I', path.join(__dirname, 'bridge.py')], {
      cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'ignore']
    });
    const timeout = setTimeout(() => {
      child.kill();
      reject(new Error('The model took too long to respond.'));
    }, 20000);
    let output = '';
    child.stdout.setEncoding('utf8');
    child.stdout.on('data', chunk => { output += chunk; });
    child.stdin.on('error', () => {});
    child.on('error', () => {
      clearTimeout(timeout);
      reject(new Error('The project Python environment could not start.'));
    });
    child.on('close', code => {
      clearTimeout(timeout);
      try {
        if (code !== 0) throw new Error();
        const response = JSON.parse(output);
        if (response.error) return reject(new Error(response.error));
        resolve(response.result);
      } catch {
        reject(new Error('The local model returned an invalid response.'));
      }
    });
    child.stdin.end(JSON.stringify({ action, text }));
  });
}

function verifySender(event) {
  if (event.senderFrame?.url !== pathToFileURL(page).href)
    throw new Error('Unknown app window.');
}

app.whenReady().then(async () => {
  ipcMain.handle('model:info', event => {
    verifySender(event);
    return request('info');
  });
  ipcMain.handle('model:predict', (event, text) => {
    verifySender(event);
    if (typeof text !== 'string' || !text.trim() || text.length > 10000)
      throw new Error('Enter an English message of up to 10,000 characters.');
    return request('predict', text);
  });
  const window = new BrowserWindow({
    width: 1240, height: 870, minWidth: 720, minHeight: 600, backgroundColor: '#edf0f8',
    autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), sandbox: true,
      contextIsolation: true, nodeIntegration: false }
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', event => event.preventDefault());
  await window.loadFile(page);
  if (process.argv.includes('--smoke')) {
    try {
      await require('./smoke.cjs')(window, process.env.SPAMCHECK_SMOKE_DIR);
      app.exit(0);
    } catch (error) {
      console.error(error);
      app.exit(1);
    }
  }
}).catch(error => { console.error(error); app.exit(1); });

app.on('window-all-closed', () => app.quit());
