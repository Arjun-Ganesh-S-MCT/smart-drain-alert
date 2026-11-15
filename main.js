const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const path = require('path');

if (!app.requestSingleInstanceLock()) app.quit();

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 1320,
    height: 900,
    minWidth: 960,
    minHeight: 640,
    title: 'Smart Drainage Alert',
    backgroundColor: '#e0d9d3',
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false }
  });

  const ses = win.webContents.session;
  ses.setPermissionCheckHandler((wc, permission) => permission === 'serial');
  ses.setDevicePermissionHandler(details => details.deviceType === 'serial');
  ses.on('select-serial-port', (event, ports, wc, callback) => {
    event.preventDefault();
    if (!ports.length) return callback('');
    if (ports.length === 1) return callback(ports[0].portId);
    const list = ports.slice(0, 8);
    const index = dialog.showMessageBoxSync(win, {
      type: 'question',
      title: 'Select board',
      message: 'Choose the ESP32-S3 port',
      buttons: [...list.map(p => `${p.displayName || 'Serial device'} (${p.portName})`), 'Cancel'],
      cancelId: list.length
    });
    callback(index < list.length ? list[index].portId : '');
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith('file:')) return;
    event.preventDefault();
    if (/^(sms|https?):/.test(url)) shell.openExternal(url);
  });

  win.loadFile(path.join(__dirname, 'src', 'index.html'));
}

app.on('second-instance', () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();
});

app.on('window-all-closed', () => app.quit());
