const { app, BrowserWindow, Menu, dialog, shell, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execFile } = require('child_process');

if (!app.requestSingleInstanceLock()) app.quit();

const ICON = path.join(__dirname, 'build', 'icon.png');
const BG = '#e0d9d3';
const SPLASH_MS = 4300;
const DRIVER_LINKS = {
  cp210x: 'https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers',
  ch340: 'https://www.wch-ic.com/downloads/CH341SER_EXE.html'
};
const flagFile = () => path.join(app.getPath('userData'), 'setup-done.json');
const wait = ms => new Promise(r => setTimeout(r, ms));
const sh = (cmd, args) => new Promise(res =>
  execFile(cmd, args, { timeout: 20000, windowsHide: true }, (err, out) => res({ err, out: String(out || '') })));

let win = null;
let setupWin = null;

function showSplash() {
  const s = new BrowserWindow({
    width: 640, height: 420, frame: false, resizable: false, movable: false, center: true,
    show: false, alwaysOnTop: true, backgroundColor: BG, icon: ICON,
    webPreferences: { sandbox: true, contextIsolation: true }
  });
  s.loadFile(path.join(__dirname, 'src', 'splash.html'));
  s.once('ready-to-show', () => s.show());
  return s;
}

function createMain() {
  win = new BrowserWindow({
    width: 1320, height: 900, minWidth: 960, minHeight: 640, show: false,
    title: 'FlowSense', backgroundColor: BG, icon: ICON,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, sandbox: true, nodeIntegration: false,
      autoplayPolicy: 'no-user-gesture-required'
    }
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
      type: 'question', title: 'Select board', message: 'Choose the ESP32-S3 port',
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
  win.on('closed', () => { win = null; });
  win.loadFile(path.join(__dirname, 'src', 'index.html'));
}

function openSetup() {
  if (setupWin) { setupWin.focus(); return; }
  setupWin = new BrowserWindow({
    parent: win || undefined, modal: !!win, width: 640, height: 640, resizable: false,
    minimizable: false, title: 'FlowSense setup', backgroundColor: BG, icon: ICON, autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: true }
  });
  setupWin.setMenu(null);
  setupWin.loadFile(path.join(__dirname, 'src', 'setup.html'));
  setupWin.on('closed', () => { setupWin = null; });
}

function linuxGroup() {
  try {
    const names = fs.readFileSync('/etc/group', 'utf8').split('\n').map(l => l.split(':')[0]);
    if (names.includes('dialout')) return 'dialout';
    if (names.includes('uucp')) return 'uucp';
  } catch (e) {}
  return 'dialout';
}

async function runChecks(send) {
  const result = { platform: process.platform, needsGroup: false, group: '', driverIssues: [] };
  const step = async (id, label, fn) => { send(id, 'run', label); await wait(450); const [state, text] = await fn(); send(id, state, text); };

  await step('sys', 'Checking this computer', async () => ['ok', `${os.type()} ${os.release()} (${process.arch})`]);
  await step('app', 'Checking app files', async () => ['ok', 'Sounds, fonts and the mascot are built in. Nothing to download.']);

  if (process.platform === 'linux') {
    const group = linuxGroup();
    result.group = group;
    await step('ports', 'Looking for serial devices', async () => {
      const devs = fs.readdirSync('/dev').filter(n => /^tty(ACM|USB)\d+$/.test(n));
      return ['ok', devs.length ? `Found: ${devs.join(', ')}` : 'No board plugged in yet. That is fine.'];
    });
    await step('perm', 'Checking serial port access', async () => {
      const id = await sh('id', ['-nG']);
      const inGroup = (process.getuid && process.getuid() === 0) || id.out.trim().split(/\s+/).includes(group);
      result.needsGroup = !inGroup;
      return inGroup ? ['ok', `Allowed (group ${group})`] : ['warn', `Your account is not in the ${group} group, so Linux blocks USB serial ports.`];
    });
  } else if (process.platform === 'win32') {
    const ps = c => sh('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', c]);
    const lines = o => o.out.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
    await step('ports', 'Looking for serial devices', async () => {
      const names = lines(await ps('Get-CimInstance Win32_SerialPort | Select-Object -ExpandProperty Name'));
      return ['ok', names.length ? `Found: ${names.join(', ')}` : 'No board plugged in yet. That is fine.'];
    });
    await step('drv', 'Checking USB serial drivers', async () => {
      const bad = lines(await ps("Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Error' -and $_.InstanceId -like 'USB*' } | Select-Object -ExpandProperty FriendlyName"));
      result.driverIssues = bad;
      return bad.length ? ['warn', `A USB device has no driver: ${bad.join(', ')}`] : ['ok', 'No missing USB serial drivers'];
    });
  }
  await step('final', 'Finishing', async () => ['ok', 'Setup check finished']);
  return result;
}

ipcMain.handle('setup:open-window', () => openSetup());
ipcMain.handle('setup:run', e => runChecks((id, state, text) => e.sender.send('setup:step', { id, state, text })));
ipcMain.handle('setup:grant', async () => {
  if (process.platform !== 'linux') return { ok: false, error: 'Only needed on Linux' };
  const group = linuxGroup();
  const r = await sh('pkexec', ['usermod', '-aG', group, os.userInfo().username]);
  return { ok: !r.err, group, error: r.err ? r.err.message : '' };
});
ipcMain.handle('setup:link', (e, key) => { if (DRIVER_LINKS[key]) shell.openExternal(DRIVER_LINKS[key]); });
ipcMain.handle('setup:done', () => {
  fs.mkdirSync(app.getPath('userData'), { recursive: true });
  fs.writeFileSync(flagFile(), JSON.stringify({ done: new Date().toISOString(), version: app.getVersion() }));
  if (setupWin) setupWin.close();
});

app.on('second-instance', () => {
  if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
});

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  const t0 = Date.now();
  const splash = showSplash();
  createMain();
  win.once('ready-to-show', () => {
    setTimeout(() => {
      if (!splash.isDestroyed()) splash.destroy();
      win.show();
      if (!fs.existsSync(flagFile())) openSetup();
    }, Math.max(0, SPLASH_MS - (Date.now() - t0)));
  });
});

app.on('window-all-closed', () => app.quit());
