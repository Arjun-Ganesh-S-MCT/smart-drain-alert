const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('flowsense', {
  runSetup: () => ipcRenderer.invoke('setup:run'),
  onStep: cb => ipcRenderer.on('setup:step', (e, d) => cb(d)),
  grantSerial: () => ipcRenderer.invoke('setup:grant'),
  openLink: key => ipcRenderer.invoke('setup:link', key),
  finish: () => ipcRenderer.invoke('setup:done'),
  openSetup: () => ipcRenderer.invoke('setup:open-window')
});
