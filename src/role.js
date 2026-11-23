/* Access modes: Consumer (view), Maintenance team (operate), Developer (everything).
   Chosen on first start, switchable from the header. Developer mode asks for a password (default 1234, changeable under Console).
   This is a convenience lock on this computer, not strong security. */
(function () {
  'use strict';
  const KEY = 'fbrole', PWKEY = 'fbdevpw', SALT = 'fb-dev:';
  const DEFAULT_HASH = 'e45cf19bbe2cbbb462353255f8393fbb91b3f88aa258eadac6d7257ad13ec746';   // SHA-256 of "fb-dev:1234"
  const ALL = ['overview', 'model', 'incidents', 'connect', 'history', 'calib', 'drip', 'settings', 'console', 'map'];
  const ROLES = {
    consumer: { n: 'Consumer', d: 'See drain status, live readings, the drain model and history. No controls.', ic: 'devices', tabs: ['overview', 'model', 'history', 'drip', 'settings'] },
    team: { n: 'Maintenance team', d: 'Full operational control: incidents, city map and dispatch, board connection and calibration.', ic: 'team', tabs: ALL.filter(t => t !== 'console') },
    dev: { n: 'Developer', d: 'Full control of everything, including the firmware console. Can switch to any mode. Password required.', ic: 'lock', tabs: ALL }
  };
  const T = s => (window.trans ? window.trans(s) : s);
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const store = {
    get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  let role = 'consumer', fails = 0, lockUntil = 0;

  async function hash(p) {
    if (window.crypto && crypto.subtle) return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(SALT + p)))].map(b => b.toString(16).padStart(2, '0')).join('');
    return 'plain:' + p;
  }
  const expected = () => store.get(PWKEY) || ((window.crypto && crypto.subtle) ? DEFAULT_HASH : 'plain:1234');

  /* ---- applying a mode ---- */
  const can = tab => ROLES[role].tabs.includes(tab);
  function apply() {
    document.body.dataset.role = role;
    const lock = role === 'consumer';
    ['bConn', 'bDemo', 'bCal', 'bWiz'].forEach(id => { const b = $(id); if (b) { b.hidden = lock; b.disabled = lock; } });
    const seg = document.querySelector('.seg [data-s]'), nn = $('nname');
    [seg && seg.closest('.seg') && seg.closest('.seg').parentElement, nn && nn.parentElement].forEach(e => { if (e) e.hidden = lock; });
    const chip = $('roleChip');
    if (chip) chip.textContent = T(ROLES[role].n) + ' ▾';
    document.dispatchEvent(new Event('fbrole'));
  }
  function set(r, remember) {
    role = r;
    if (remember !== false) store.set(KEY, r);
    apply();
  }

  /* ---- chooser dialog ---- */
  const css = document.createElement('style');
  css.textContent = '.role-ov{position:fixed;inset:0;z-index:60;display:none;place-items:center;padding:20px;background:color-mix(in srgb,var(--bg) 78%,#000 22%);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}' +
    '.role-ov.on{display:grid}.role-box{width:min(760px,100%);padding:28px 30px;max-height:94vh;overflow:auto}.role-box h1{margin:0 0 4px;font-size:1.3rem}' +
    '.role-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:20px 0}' +
    '.role-card{display:flex;flex-direction:column;align-items:flex-start;gap:8px;text-align:left;padding:18px;border-radius:18px;height:100%}.role-card::before{content:"";width:44px;height:44px;background:var(--ic) center/contain no-repeat}' +
    '.role-card b{font-size:1rem;color:var(--ac)}.role-card span{font-size:.78rem;font-weight:400;line-height:1.5;color:var(--mu);white-space:normal}.role-card.cur{outline:2px solid var(--ac);outline-offset:2px}' +
    '.rolechip{padding:7px 14px;font-size:.76rem;margin-right:10px}';
  document.head.appendChild(css);
  const ov = document.createElement('div');
  ov.id = 'roleOv'; ov.className = 'role-ov'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('aria-labelledby', 'roleT');
  ov.innerHTML = '<div class="role-box raised"><h1 id="roleT">Welcome to FlowBeacon</h1><p class="sub">Choose how you will use the app. You can switch later from the top bar.</p><div class="role-grid">' +
    Object.keys(ROLES).map(k => '<button class="role-card" data-r="' + k + '" style="--ic:var(--i-' + ROLES[k].ic + ')"><b>' + esc(T(ROLES[k].n)) + '</b><span>' + esc(T(ROLES[k].d)) + '</span></button>').join('') +
    '</div><div id="rolePw" hidden><label for="rolePwIn">Developer password</label><div class="row"><input type="password" id="rolePwIn" autocomplete="off" style="max-width:240px"><button id="rolePwGo">Unlock</button><span id="rolePwMsg" class="sub"></span></div></div>' +
    '<div class="row fld" style="justify-content:flex-end"><button id="roleCancel" hidden>Cancel</button></div></div>';
  document.body.appendChild(ov);

  function open(opts) {
    opts = opts || {};
    ov.classList.add('on');
    $('roleCancel').hidden = !opts.cancel;
    $('rolePw').hidden = !opts.askDev;
    $('rolePwMsg').textContent = '';
    ov.querySelectorAll('.role-card').forEach(c => c.classList.toggle('cur', !!opts.cancel && c.dataset.r === role));
    if (opts.askDev) setTimeout(() => $('rolePwIn').focus(), 50);
  }
  const close = () => { ov.classList.remove('on'); $('rolePwIn').value = ''; };
  async function tryDev() {
    const msg = $('rolePwMsg');
    if (Date.now() < lockUntil) { msg.textContent = T('Too many attempts. Wait a few seconds.'); return; }
    if (await hash($('rolePwIn').value) === expected()) { fails = 0; set('dev'); close(); }
    else { fails++; msg.textContent = T('Wrong password.'); $('rolePwIn').select(); if (fails >= 5) { lockUntil = Date.now() + 30000; fails = 0; } }
  }
  ov.addEventListener('click', e => {
    const c = e.target.closest('.role-card');
    if (c) {
      if (c.dataset.r === 'dev') { if (role === 'dev') close(); else { $('rolePw').hidden = false; $('rolePwIn').focus(); } }
      else { set(c.dataset.r); close(); }
    }
    if (e.target.id === 'rolePwGo') tryDev();
    if (e.target.id === 'roleCancel') close();
  });
  ov.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.id === 'rolePwIn') tryDev();
    if (e.key === 'Escape' && !$('roleCancel').hidden) close();
  });

  /* ---- header chip ---- */
  const chip = document.createElement('button');
  chip.id = 'roleChip'; chip.className = 'rolechip'; chip.setAttribute('aria-haspopup', 'dialog');
  const conn = $('conn');
  if (conn) conn.before(chip); else document.querySelector('header').appendChild(chip);
  chip.onclick = () => open({ cancel: true });

  /* ---- developer-only card: change the developer password ---- */
  document.addEventListener('fbtabs-ready', () => {
    const pg = document.querySelector('.pg[data-pg=console]');
    if (!pg || $('devAccess')) return;
    const s = document.createElement('section');
    s.id = 'devAccess'; s.className = 'raised card';
    s.innerHTML = '<h2>Developer access</h2><label for="devNew">New developer password</label><div class="row"><input type="password" id="devNew" autocomplete="off" placeholder="At least 4 characters" style="max-width:260px"><button id="devSave">Save</button><button id="devReset">Reset to 1234</button><span id="devMsg" class="sub"></span></div>';
    pg.prepend(s);
    $('devSave').onclick = async () => { const v = $('devNew').value; if (v.length < 4) { $('devMsg').textContent = T('At least 4 characters.'); return; } store.set(PWKEY, await hash(v)); $('devNew').value = ''; $('devMsg').textContent = T('Password changed.'); };
    $('devReset').onclick = () => { try { localStorage.removeItem(PWKEY); } catch (e) {} $('devMsg').textContent = T('Password reset to 1234.'); };
  });

  window.fbRole = { get: () => role, can, set, open };

  /* ---- first start / next start ---- */
  const saved = store.get(KEY);
  if (!saved) { set('consumer', false); open({}); }                       // first login: must choose
  else if (saved === 'dev') { set('consumer', false); open({ askDev: true }); }   // developer mode asks again on every start
  else set(ROLES[saved] ? saved : 'consumer');
})();
