const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { createModelWorker } = require('./model-worker.cjs');

const root = path.resolve(__dirname, '..');
const page = path.join(__dirname, 'index.html');
const venv = path.join(root, '.venv');
const python = process.env.SPAMCHECK_PYTHON || (process.platform === 'win32'
  ? path.join(venv, 'Scripts', 'python.exe')
  : path.join(venv, 'bin', 'python'));

const modelWorker = createModelWorker(python, path.join(__dirname, 'bridge.py'), root);
const { request } = modelWorker;

function exitApp(code) {
  modelWorker.close();
  app.exit(code);
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
    return request('predict', { text });
  });
  ipcMain.handle('model:install', async event => {
    verifySender(event);
    const parent = BrowserWindow.fromWebContents(event.sender);
    const { canceled, filePaths } = await dialog.showOpenDialog(parent, {
      title: 'Select a SpamCheck model',
      properties: ['openFile'],
      filters: [{ name: 'SpamCheck model', extensions: ['skops'] }]
    });
    return canceled ? null : request('install', { path: filePaths[0] });
  });
  ipcMain.handle('model:restore', event => {
    verifySender(event);
    return request('restore');
  });
  const smoke = process.argv.includes('--smoke');
  const webPreferences = {
    preload: path.join(__dirname, 'preload.cjs'), sandbox: true,
    contextIsolation: true, nodeIntegration: false
  };
  if (smoke) webPreferences.partition = 'spamcheck-smoke';
  const window = new BrowserWindow({
    width: 1240, height: 870, minWidth: 720, minHeight: 600, backgroundColor: '#edf0f8',
    autoHideMenuBar: true,
    webPreferences
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', event => event.preventDefault());
  await window.loadFile(page);
  if (smoke) {
    try {
      await require('./smoke.cjs')(window, process.env.SPAMCHECK_SMOKE_DIR);
      exitApp(0);
    } catch (error) {
      console.error(error);
      exitApp(1);
    }
  }
}).catch(error => { console.error(error); exitApp(1); });

app.on('window-all-closed', () => app.quit());
app.on('will-quit', modelWorker.close);
