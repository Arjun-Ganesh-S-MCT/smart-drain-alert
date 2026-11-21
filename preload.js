const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('flowsense', {
  platform: process.platform,
  runSetup: () => ipcRenderer.invoke('setup:run'),
  onStep: cb => ipcRenderer.on('setup:step', (e, d) => cb(d)),
  grantSerial: () => ipcRenderer.invoke('setup:grant'),
  openLink: key => ipcRenderer.invoke('setup:link', key),
  finish: () => ipcRenderer.invoke('setup:done'),
  openSetup: () => ipcRenderer.invoke('setup:open-window'),
  getSettings: () => ipcRenderer.invoke('app:settings:get'),
  setSettings: o => ipcRenderer.invoke('app:settings:set', o),
  setLevel: (lvl, text) => ipcRenderer.invoke('app:level', lvl, text),
  focus: () => ipcRenderer.invoke('app:focus'),
  log: text => ipcRenderer.invoke('app:log', text),
  openLog: () => ipcRenderer.invoke('app:open-log'),
  checkUpdate: () => ipcRenderer.invoke('app:check-update'),
  openUrl: url => ipcRenderer.invoke('app:open-url', url)
});
