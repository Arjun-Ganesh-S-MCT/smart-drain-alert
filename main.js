const { app, BrowserWindow, Menu, Tray, nativeImage, dialog, shell, ipcMain, net } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execFile } = require('child_process');
const pkg = require('./package.json');

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
let tray = null;
let quitting = false;
const settingsFile = () => path.join(app.getPath('userData'), 'settings.json');
const logFile = () => path.join(app.getPath('userData'), 'flowsense.log');
let settings = { closeToTray: false, startWithPc: false };
const hidden = process.argv.includes('--hidden');

function loadSettings() {
  try { settings = Object.assign(settings, JSON.parse(fs.readFileSync(settingsFile(), 'utf8'))); } catch (e) {}
}

function saveSettings() {
  fs.mkdirSync(app.getPath('userData'), { recursive: true });
  fs.writeFileSync(settingsFile(), JSON.stringify(settings));
  if (process.platform === 'win32') {
    app.setLoginItemSettings({ openAtLogin: !!settings.startWithPc, args: ['--hidden'] });
  }
}

function writeLog(text) {
  try {
    fs.mkdirSync(app.getPath('userData'), { recursive: true });
    const f = logFile();
    if (fs.existsSync(f) && fs.statSync(f).size > 1048576) fs.renameSync(f, f + '.old');
    fs.appendFileSync(f, `${new Date().toISOString()} ${String(text).slice(0, 2000)}\n`);
  } catch (e) {}
}

const trayIcon = lvl => nativeImage.createFromPath(path.join(__dirname, 'build', `tray-${lvl}.png`));

function createTray() {
  try {
    tray = new Tray(trayIcon(0));
    tray.setToolTip('FlowSense');
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: 'Show FlowSense', click: () => showMain() },
      { label: 'Quit', click: () => { quitting = true; app.quit(); } }
    ]));
    tray.on('click', () => showMain());
  } catch (e) { writeLog('tray failed: ' + e.message); }
}

function showMain() {
  if (!win) return;
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
}

const cmp = (a, b) => {
  const x = String(a).split('.').map(Number), y = String(b).split('.').map(Number);
  for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0); }
  return 0;
};

async function checkUpdate() {
  try {
    const m = String((pkg.repository && pkg.repository.url) || '').match(/github\.com\/([^/]+\/[^/.]+)/);
    if (!m) return { error: 'No repository set in package.json' };
    const res = await net.fetch(`https://api.github.com/repos/${m[1]}/releases/latest`, { headers: { 'User-Agent': 'FlowSense' } });
    if (!res.ok) return { error: 'GitHub answered ' + res.status };
    const j = await res.json();
    const latest = String(j.tag_name || '').replace(/^v/, '');
    return { current: app.getVersion(), latest, url: j.html_url, newer: cmp(latest, app.getVersion()) > 0 };
  } catch (e) { return { error: e.message }; }
}

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
  ses.setPermissionCheckHandler((wc, permission) => permission === 'serial' || permission === 'notifications');
  ses.setPermissionRequestHandler((wc, permission, cb) => cb(permission === 'notifications'));
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
  win.on('close', e => {
    if (!quitting && settings.closeToTray && tray) { e.preventDefault(); win.hide(); }
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

ipcMain.handle('app:settings:get', () => ({ closeToTray: settings.closeToTray, startWithPc: settings.startWithPc, platform: process.platform, version: app.getVersion() }));
ipcMain.handle('app:settings:set', (e, o) => {
  if (o && typeof o.closeToTray === 'boolean') settings.closeToTray = o.closeToTray;
  if (o && typeof o.startWithPc === 'boolean') settings.startWithPc = o.startWithPc;
  saveSettings();
});
ipcMain.handle('app:level', (e, lvl, text) => {
  if (!tray) return;
  tray.setImage(trayIcon(Math.max(0, Math.min(4, Number(lvl) || 0))));
  tray.setToolTip(String(text || 'FlowSense').slice(0, 120));
});
ipcMain.handle('app:focus', () => showMain());
ipcMain.handle('app:log', (e, text) => writeLog(text));
ipcMain.handle('app:open-log', () => { fs.mkdirSync(app.getPath('userData'), { recursive: true }); if (!fs.existsSync(logFile())) writeLog('log started'); shell.showItemInFolder(logFile()); });
ipcMain.handle('app:check-update', () => checkUpdate());
ipcMain.handle('app:open-url', (e, url) => { if (typeof url === 'string' && url.startsWith('https://github.com/')) shell.openExternal(url); });

app.on('second-instance', () => showMain());
app.on('before-quit', () => { quitting = true; });

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  loadSettings();
  createTray();
  const t0 = Date.now();
  const splash = showSplash();
  createMain();
  win.once('ready-to-show', () => {
    setTimeout(() => {
      if (!splash.isDestroyed()) splash.destroy();
      if (hidden && tray) return;
      win.show();
      if (!fs.existsSync(flagFile())) openSetup();
    }, Math.max(0, SPLASH_MS - (Date.now() - t0)));
  });
});

app.on('window-all-closed', () => { if (!settings.closeToTray || quitting) app.quit(); });
