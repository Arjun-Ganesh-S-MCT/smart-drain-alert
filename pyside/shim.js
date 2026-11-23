/* Injected before the page loads. Gives the unchanged FlowBeacon UI the same window.flowbeacon bridge,
   navigator.serial and Notification it had under Electron, backed by Python (PySide6). */
(function () {
  'use strict';
  let B = null;
  const ready = new Promise(res => new QWebChannel(qt.webChannelTransport, ch => { B = ch.objects.bridge; wire(); res(B); }));
  const call = (name, ...a) => ready.then(b => new Promise(r => b[name](...a, r)));
  const j = s => { try { return JSON.parse(s); } catch (e) { return {}; } };
  const stepCbs = [], notes = [];
  const updCbs = [];
  let setupRes = null, port = null;

  function wire() {
    B.setupStep.connect(s => stepCbs.forEach(f => f(j(s))));
    B.setupResult.connect(s => { if (setupRes) { setupRes(j(s)); setupRes = null; } });
    B.updateState.connect(s => updCbs.forEach(f => f(j(s))));
    B.notifyClicked.connect(() => notes.forEach(n => n.onclick && n.onclick()));
    B.serialData.connect(b64 => { if (port && port._ctrl) { const s = atob(b64), u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); try { port._ctrl.enqueue(u); } catch (e) {} } });
    B.serialClosed.connect(() => { if (port && port._ctrl) { try { port._ctrl.close(); } catch (e) {} port._ctrl = null; } });
  }

  window.flowbeacon = {
    platform: '__PLATFORM__',
    runSetup: () => new Promise(res => { setupRes = res; call('runSetup'); }),
    onStep: cb => stepCbs.push(cb),
    grantSerial: () => call('grantSerial').then(j),
    openLink: key => call('openLink', key),
    finish: () => call('finish'),
    openSetup: () => call('openSetup'),
    getSettings: () => call('getSettings').then(j),
    setSettings: o => call('setSettings', JSON.stringify(o || {})),
    setLevel: (l, t) => call('setLevel', +l || 0, String(t || '')),
    focus: () => call('focus'),
    log: t => call('log', String(t)),
    openLog: () => call('openLog'),
    openUrl: u => call('openUrl', String(u)),
    checkUpdate: () => call('checkUpdate').then(j),
    onUpdate: cb => updCbs.push(cb),
    installUpdate: () => call('installUpdate')
  };

  // Web Serial look-alike backed by QSerialPort
  class Port {
    constructor(name) { this.name = name; this.readable = null; this.writable = null; this._ctrl = null; }
    async open(o) {
      const err = await call('serialOpen', this.name, (o && o.baudRate) || 115200);
      if (err) throw new Error(err);
      port = this;
      this.readable = new ReadableStream({ start: c => { this._ctrl = c; } });
      this.writable = new WritableStream({ write: chunk => { let s = ''; for (const b of chunk) s += String.fromCharCode(b); return call('serialWrite', btoa(s)); } });
    }
    async close() { await call('serialClose'); try { if (this._ctrl) this._ctrl.close(); } catch (e) {} this._ctrl = null; this.readable = this.writable = null; }
  }
  Object.defineProperty(navigator, 'serial', {
    configurable: true,
    value: {
      requestPort: async () => { const n = await call('pickPort'); if (!n) throw new Error('No port selected'); return new Port(n); },
      getPorts: async () => { const n = await call('lastPort'); return n ? [new Port(n)] : []; }
    }
  });

  // Desktop notifications through the tray
  window.Notification = class {
    constructor(title, o) { this.onclick = null; notes.push(this); if (notes.length > 20) notes.shift(); call('notify', String(title), String((o && o.body) || '')); }
    close() {}
    static get permission() { return 'granted'; }
    static requestPermission() { return Promise.resolve('granted'); }
  };

  // window.print() has no dialog in Qt WebEngine: save the report as PDF instead
  window.print = () => { call('printReport'); };
})();
