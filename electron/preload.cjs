const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('spamcheck', {
  info: () => ipcRenderer.invoke('model:info'),
  predict: text => ipcRenderer.invoke('model:predict', text),
  installModel: () => ipcRenderer.invoke('model:install')
});
