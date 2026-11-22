/* City drainage map for corporation officials: Leaflet + OpenStreetMap.
   Reads live node data from the existing multi-drain engine (window.fbNodes, set in features.js). */
(function () {
  'use strict';
  const KEY = 'fbmap';
  const STALE_MS = 30000;
  const CENTER = [13.0827, 80.2707];
  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const T = s => (window.trans ? window.trans(s) : s);
  const STAT = {
    normal: { n: 'Normal', g: '✓' }, possible: { n: 'Possible blockage', g: '?' }, blockage: { n: 'Blockage detected', g: '!' },
    overflow: { n: 'Overflow warning', g: '≈' }, offline: { n: 'Offline', g: '–' }
  };
  const LVLN = ['Normal', 'Possible blockage', 'Blockage warning', 'Overflow risk', 'Overflow detected'];
  const INC_ST = { open: 'Open', assigned: 'Assigned', progress: 'In progress', resolved: 'Resolved' };
  const DEMO = {
    'demo-2': { lat: 13.0850, lng: 80.2101, ward: 'Ward 34', zone: 'Zone 5', name: 'Anna Nagar 2nd Ave (demo)' },
    'demo-3': { lat: 13.0418, lng: 80.2341, ward: 'Ward 57', zone: 'Zone 8', name: 'T. Nagar Usman Rd (demo)' }
  };

  let M = { devices: {}, teams: ['Team A', 'Team B', 'Team C'], incidents: [], hide: {}, officer: '', pin: null, salt: '', center: CENTER };
  try { Object.assign(M, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) {}
  const isDemo = id => /^demo-/.test(id);
  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(Object.assign({}, M, {
        devices: Object.fromEntries(Object.entries(M.devices).filter(([id]) => !isDemo(id))),
        incidents: M.incidents.filter(i => !isDemo(i.dev))
      })));
    } catch (e) {}
  }

  let map = null, mapErr = '', layer = null, markers = {}, sel = null, pick = false, unlocked = false, shown = false, fitted = false, tileWarned = false;
  const normalCount = {};
  const sig = {};

  /* ---------- devices ---------- */
  function autoPlace(id) {
    if (DEMO[id]) return Object.assign({ placed: true }, DEMO[id]);
    let h = 0; for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    const a = (h % 360) * Math.PI / 180, r = 0.004 + ((h >>> 9) % 100) / 100 * 0.02;
    return { lat: +(M.center[0] + Math.sin(a) * r).toFixed(5), lng: +(M.center[1] + Math.cos(a) * r).toFixed(5), ward: '', zone: '', name: '', placed: false };
  }
  function ensure(id) {
    if (M.hide[id]) return null;
    if (!M.devices[id]) M.devices[id] = autoPlace(id);
    return M.devices[id];
  }
  function live() { try { return (window.fbNodes ? window.fbNodes() : []); } catch (e) { return []; } }
  function states() {
    const nodes = {}; live().forEach(n => { nodes[n.id] = n; });
    Object.keys(nodes).forEach(ensure);
    const now = Date.now();
    return Object.keys(M.devices).filter(id => !M.hide[id]).map(id => {
      const dv = M.devices[id], n = nodes[id], rx = n ? n.rx : 0, online = !!rx && now - rx < STALE_MS;
      const lvl = n && online ? n.lvl : 0;
      const status = !online ? 'offline' : lvl === 0 ? 'normal' : lvl === 1 ? 'possible' : lvl === 2 ? 'blockage' : 'overflow';
      let base = null; try { base = S.nodes[id] && S.nodes[id].base; } catch (e) {}
      return { id, dv, lvl, status, online, rx, last: n ? n.last : null, base, name: (n && n.name) || id };
    });
  }
  const label = st => st.dv.name ? st.dv.name : (st.name !== st.id ? st.name : st.id);
  const pass = st => {
    const w = $('dmWard').value, z = $('dmZone').value, s = $('dmStat').value;
    return (!w || (st.dv.ward || 'Unassigned') === w) && (!z || (st.dv.zone || 'Unassigned') === z) && (!s || st.status === s);
  };

  /* ---------- incidents ---------- */
  const openInc = id => M.incidents.find(i => i.dev === id && i.status !== 'resolved');
  const addLog = (i, m) => { i.log.push({ t: Date.now(), m }); };
  function newInc(st, lvl) {
    const i = { id: 'I' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5), dev: st.id, level: lvl, max: lvl, start: Date.now(), status: 'open', team: '', log: [] };
    addLog(i, 'Detected: ' + LVLN[lvl]);
    M.incidents.unshift(i);
    if (M.incidents.length > 500) M.incidents.length = 500;
    return i;
  }
  function track(st) {
    if (!st.online) return;
    const inc = openInc(st.id);
    if (st.lvl >= 2) {
      normalCount[st.id] = 0;
      if (!inc) { newInc(st, st.lvl); save(); }
      else if (st.lvl !== inc.level) { inc.level = st.lvl; if (st.lvl > inc.max) { inc.max = st.lvl; addLog(inc, 'Escalated: ' + LVLN[st.lvl]); } save(); }
    } else if (st.lvl === 0 && inc) {
      normalCount[st.id] = (normalCount[st.id] || 0) + 1;
      if (normalCount[st.id] >= 3) { inc.status = 'resolved'; inc.end = Date.now(); inc.by = 'Sensor (back to normal)'; addLog(inc, 'Sensor reads normal: closed automatically'); save(); }
    } else normalCount[st.id] = 0;
  }

  /* ---------- rendering ---------- */
  function fillSelect(el, items, all) {
    const s = items.join('|'), cur = el.value;
    if (el.dataset.sig === s) return;
    el.dataset.sig = s;
    el.innerHTML = '<option value="">' + esc(T(all)) + '</option>' + items.map(v => '<option value="' + esc(v) + '">' + esc(v) + '</option>').join('');
    el.value = items.includes(cur) ? cur : '';
  }
  function popup(st) {
    const l = st.last || {}, rise = st.base && l.dist != null ? st.base.dist - l.dist : null;
    const lv = st.online ? LVLN[st.lvl] : 'Offline';
    return '<div class="dm-pop"><b>' + esc(label(st)) + '</b><table>' +
      '<tr><td>Device ID</td><td>' + esc(st.id) + '</td></tr>' +
      '<tr><td>Location</td><td>' + esc(st.dv.name || (st.dv.placed ? '' : 'Not set')) + ' ' + esc((st.dv.ward || '') + (st.dv.zone ? ' · ' + st.dv.zone : '')) + '</td></tr>' +
      '<tr><td>Water level</td><td>' + (l.dist != null ? (+l.dist).toFixed(1) + ' cm to surface' + (rise != null ? ' (' + (rise >= 0 ? '+' : '') + rise.toFixed(1) + ' cm vs normal)' : '') : '–') + '</td></tr>' +
      '<tr><td>Flow rate</td><td>' + (l.flow != null ? (+l.flow).toFixed(2) + ' L/min' : '–') + '</td></tr>' +
      '<tr><td>Turbidity</td><td>' + (l.turb != null ? Math.round(l.turb) + ' units' : '–') + '</td></tr>' +
      '<tr><td>Status</td><td><b style="color:' + ({ normal: '#1a9460', possible: '#a88400', blockage: '#e5383b', overflow: '#2f7de1', offline: '#777' }[st.status]) + '">' + esc(lv) + '</b></td></tr></table></div>';
  }
  function updMarkers(list) {
    if (!map) return;
    const keep = new Set();
    list.filter(pass).forEach(st => {
      keep.add(st.id);
      const pos = [st.dv.lat, st.dv.lng];
      let mk = markers[st.id];
      if (!mk) {
        mk = markers[st.id] = L.marker(pos, { keyboard: true, title: label(st) }).bindPopup('');
        mk.on('click', () => select(st.id));
      }
      if (!layer.hasLayer(mk)) layer.addLayer(mk);
      mk.setLatLng(pos);
      const s2 = st.status + (sel === st.id ? 's' : '');
      if (sig[st.id] !== s2) {
        sig[st.id] = s2;
        mk.setIcon(L.divIcon({ className: '', iconSize: [38, 48], iconAnchor: [19, 46], popupAnchor: [0, -44],
          html: '<span class="dm-pin dm-s-' + st.status + (st.status === 'overflow' && st.lvl === 4 || st.status === 'blockage' ? ' dm-crit' : '') + (sel === st.id ? ' dm-sel' : '') + '"></span>' }));
      }
      mk.getPopup().setContent(popup(st));
    });
    Object.keys(markers).forEach(id => { if (!keep.has(id) && layer.hasLayer(markers[id])) layer.removeLayer(markers[id]); });
    Object.keys(markers).forEach(id => { if (!M.devices[id] || M.hide[id]) { layer.removeLayer(markers[id]); delete markers[id]; delete sig[id]; } });
    if (!fitted && shown) {
      const pts = list.filter(s => s.dv.placed).map(s => [s.dv.lat, s.dv.lng]);
      if (pts.length) { map.fitBounds(pts, { maxZoom: 15, padding: [40, 40] }); fitted = true; }
    }
  }
  function render() {
    if (!shown) return;
    const all = states(), list = all.filter(pass);
    fillSelect($('dmWard'), [...new Set(all.map(s => s.dv.ward || 'Unassigned'))].sort(), 'All wards');
    fillSelect($('dmZone'), [...new Set(all.map(s => s.dv.zone || 'Unassigned'))].sort(), 'All zones');
    const so = $('dmStat');
    if (!so.dataset.sig) { so.dataset.sig = 1; so.innerHTML = '<option value="">' + esc(T('All statuses')) + '</option>' + Object.keys(STAT).map(k => '<option value="' + k + '">' + esc(T(STAT[k].n)) + '</option>').join(''); }
    const ids = new Set(list.map(s => s.id)), incs = M.incidents.filter(i => ids.has(i.dev));
    $('dmTotal').textContent = list.length;
    $('dmNormal').textContent = list.filter(s => s.status === 'normal').length;
    $('dmActive').textContent = incs.filter(i => i.status !== 'resolved').length;
    $('dmResolved').textContent = incs.filter(i => i.status === 'resolved').length;
    $('dmScope').textContent = ($('dmWard').value || T('All wards')) + ' · ' + ($('dmZone').value || T('All zones'));
    updMarkers(all);
    table(all, incs);
    side(all);
    teamsUi();
  }
  function table(all, incs) {
    const by = {}; all.forEach(s => { by[s.id] = s; });
    const f = d => new Date(d).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
    $('dmTable').innerHTML = '<tr><th>Detected</th><th>Device</th><th>Ward</th><th>Level</th><th>Team</th><th>Status</th></tr>' +
      (incs.slice(0, 100).map(i => { const s = by[i.dev]; return '<tr class="dm-row' + (i.dev === sel ? ' on' : '') + '" data-id="' + esc(i.dev) + '"><td>' + f(i.start) + '</td><td>' + esc(s ? label(s) : i.dev) + '</td><td>' + esc(s ? s.dv.ward || 'Unassigned' : '') + '</td><td>' + esc(LVLN[i.max]) + '</td><td>' + esc(i.team || '–') + '</td><td>' + esc(INC_ST[i.status]) + '</td></tr>'; }).join('') ||
        '<tr><td colspan="6" class="sub">No incidents yet.</td></tr>');
  }
  function teamsUi() {
    const cur = $('dmTeam').value, s = M.teams.join('|');
    if ($('dmTeam').dataset.sig !== s) {
      $('dmTeam').dataset.sig = s;
      $('dmTeam').innerHTML = '<option value="">' + esc(T('Choose team')) + '</option>' + M.teams.map(t => '<option>' + esc(t) + '</option>').join('');
      $('dmTeam').value = M.teams.includes(cur) ? cur : '';
      $('dmTeams').innerHTML = M.teams.map((t, i) => '<span class="dm-team inset">' + esc(t) + '<button data-t="' + i + '" aria-label="Remove ' + esc(t) + '">×</button></span>').join('');
    }
  }
  function side(all) {
    const st = all.find(s => s.id === sel);
    if (!st) { $('dmInfo').textContent = T('Click a marker on the map or a row below.'); $('dmDispatch').hidden = true; return; }
    const l = st.last || {}, rise = st.base && l.dist != null ? st.base.dist - l.dist : null;
    $('dmInfo').innerHTML = '<span class="dm-badge dm-s-' + st.status + '">' + esc(T(st.online ? LVLN[st.lvl] : 'Offline')) + '</span>' +
      '<div class="dm-kv"><span>Device ID</span><span>' + esc(st.id) + '</span>' +
      '<span>Location</span><span>' + esc(st.dv.name || (st.dv.placed ? '–' : 'Not set: use Edit device location')) + '</span>' +
      '<span>Ward / zone</span><span>' + esc((st.dv.ward || 'Unassigned') + ' / ' + (st.dv.zone || 'Unassigned')) + '</span>' +
      '<span>Water level</span><span>' + (l.dist != null ? (+l.dist).toFixed(1) + ' cm to surface' + (rise != null ? ' (' + (rise >= 0 ? '+' : '') + rise.toFixed(1) + ' cm)' : '') : '–') + '</span>' +
      '<span>Flow rate</span><span>' + (l.flow != null ? (+l.flow).toFixed(2) + ' L/min' : '–') + '</span>' +
      '<span>Turbidity</span><span>' + (l.turb != null ? Math.round(l.turb) + ' units' : '–') + '</span>' +
      '<span>Last data</span><span>' + (st.rx ? new Date(st.rx).toLocaleTimeString() : 'never') + '</span></div>';
    const inc = openInc(st.id), canNew = !inc && st.online && st.lvl >= 1;
    $('dmDispatch').hidden = !(inc || canNew);
    if (inc) {
      $('dmInc').innerHTML = '<b>' + esc(INC_ST[inc.status]) + '</b>' + (inc.team ? ' · ' + esc(inc.team) : '') + '<br>' + inc.log.slice(-4).map(e => esc(new Date(e.t).toLocaleTimeString() + ' ' + e.m)).join('<br>');
      if (inc.team && !$('dmTeam').dataset.touched) $('dmTeam').value = inc.team;
    } else $('dmInc').textContent = T('Possible blockage: no work order yet. Assigning a team opens one.');
    $('dmStart').disabled = !inc || inc.status !== 'assigned';
    $('dmDone').disabled = !inc;
  }
  function select(id, focus) {
    sel = id;
    $('dmTeam').dataset.touched = '';
    const dv = M.devices[id];
    if (dv) { $('dmeName').value = dv.name || ''; $('dmeWard').value = dv.ward || ''; $('dmeZone').value = dv.zone || ''; $('dmeLat').value = dv.lat; $('dmeLng').value = dv.lng; }
    Object.keys(sig).forEach(k => delete sig[k]);
    if (focus && map && dv) map.setView([dv.lat, dv.lng], Math.max(map.getZoom(), 15));
    render();
  }

  /* ---------- actions ---------- */
  const officer = () => M.officer || 'Official';
  $('dmOfficer').value = M.officer;
  $('dmOfficer').onchange = e => { M.officer = e.target.value.trim(); save(); };
  $('dmTeam').onchange = () => { $('dmTeam').dataset.touched = 1; };
  $('dmAssign').onclick = () => {
    const team = $('dmTeam').value, st = states().find(s => s.id === sel);
    if (!st || !team) { $('dmMapMsg').textContent = T('Choose a maintenance team first.'); return; }
    let inc = openInc(sel);
    if (!inc) { if (st.lvl < 1) return; inc = newInc(st, st.lvl); }
    inc.team = team; inc.status = 'assigned'; inc.assigned = Date.now();
    addLog(inc, 'Assigned to ' + team + ' by ' + officer());
    $('dmMapMsg').textContent = ''; save(); render();
  };
  $('dmStart').onclick = () => { const i = openInc(sel); if (!i) return; i.status = 'progress'; addLog(i, 'Work started by ' + (i.team || 'team')); save(); render(); };
  $('dmDone').onclick = () => {
    const i = openInc(sel); if (!i) return;
    if (!confirm('Mark this incident as resolved?')) return;
    i.status = 'resolved'; i.end = Date.now(); i.by = officer(); addLog(i, 'Marked resolved by ' + officer()); save(); render();
  };
  $('dmAddTeam').onclick = () => { const v = $('dmNewTeam').value.trim(); if (v && !M.teams.includes(v)) { M.teams.push(v); $('dmNewTeam').value = ''; save(); render(); } };
  $('dmTeams').onclick = e => { const b = e.target.closest('button'); if (b) { M.teams.splice(+b.dataset.t, 1); $('dmTeam').dataset.sig = ''; save(); render(); } };
  $('dmAdd').onclick = () => {
    const id = $('dmNewId').value.trim().slice(0, 40);
    if (!id) return;
    delete M.hide[id];
    if (!M.devices[id]) M.devices[id] = autoPlace(id);
    $('dmNewId').value = ''; save(); select(id, true); $('dmEditBox').open = true;
  };
  $('dmeSave').onclick = () => {
    const dv = M.devices[sel], lat = parseFloat($('dmeLat').value), lng = parseFloat($('dmeLng').value);
    if (!dv) return;
    if (!(lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180)) { $('dmMapMsg').textContent = T('Enter a valid latitude and longitude.'); return; }
    Object.assign(dv, { name: $('dmeName').value.trim(), ward: $('dmeWard').value.trim(), zone: $('dmeZone').value.trim(), lat, lng, placed: true });
    $('dmMapMsg').textContent = ''; save(); select(sel, true);
  };
  $('dmeDel').onclick = () => {
    if (!sel || !confirm('Remove this device from the city map? Past incidents are kept.')) return;
    M.hide[sel] = 1; sel = null; save(); render();
  };
  $('dmePick').onclick = () => {
    if (!sel) { $('dmMapMsg').textContent = T('Select a device first.'); return; }
    pick = !pick; $('dmePick').classList.toggle('on', pick);
    $('dmMapMsg').textContent = pick ? T('Click the map to set the device location.') : '';
  };
  $('dmCityGo').onclick = () => {
    const p = $('dmCity').value.split(',').map(x => parseFloat(x));
    if (p.length === 2 && p.every(isFinite) && map) { M.center = p; save(); map.setView(p, 13); }
  };
  document.addEventListener('click', e => {
    const r = e.target.closest && e.target.closest('#dmTable tr.dm-row');
    if (r) select(r.dataset.id, true);
  });
  ['dmWard', 'dmZone', 'dmStat'].forEach(id => { $(id).onchange = () => { fitted = false; render(); }; });

  /* ---------- officials PIN (convenience lock, kept on this computer) ---------- */
  async function hash(p) {
    const data = new TextEncoder().encode(M.salt + p);
    if (window.crypto && crypto.subtle) return [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(b => b.toString(16).padStart(2, '0')).join('');
    let h = 5381; for (const b of data) h = ((h << 5) + h + b) >>> 0; return String(h);
  }
  $('dmPinSet').onclick = async () => {
    const v = $('dmPinNew').value;
    if (v.length < 4) { $('dmMapMsg').textContent = T('PIN must be at least 4 characters.'); return; }
    M.salt = Math.random().toString(36).slice(2); M.pin = await hash(v); $('dmPinNew').value = ''; unlocked = true; save();
    $('dmMapMsg').textContent = T('PIN set. It will be asked each time the app starts.');
  };
  $('dmPinOff').onclick = () => { M.pin = null; save(); $('dmMapMsg').textContent = T('PIN removed.'); };
  async function tryUnlock() {
    if (await hash($('dmPinIn').value) === M.pin) { unlocked = true; $('dmPinIn').value = ''; $('dmPinMsg').textContent = ''; gate(); }
    else $('dmPinMsg').textContent = T('Wrong PIN.');
  }
  $('dmPinGo').onclick = tryUnlock;
  $('dmPinIn').onkeydown = e => { if (e.key === 'Enter') tryUnlock(); };
  function gate() {
    const locked = !!M.pin && !unlocked;
    $('dmLock').hidden = !locked; $('dmBody').hidden = locked;
    if (!locked) { start(); }
  }

  /* ---------- map ---------- */
  const CDN = 'https://unpkg.com/leaflet@1.9.4/dist/';
  function inject(base) {
    return new Promise((res, rej) => {
      const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = base + 'leaflet.css'; document.head.appendChild(l);
      const s = document.createElement('script'); s.src = base + 'leaflet.js'; s.onload = res; s.onerror = () => { s.remove(); l.remove(); rej(new Error('missing')); };
      document.head.appendChild(s);
    });
  }
  // Local copy (from npm install) first, internet copy as a fallback
  const loadLeaflet = () => window.L ? Promise.resolve() : inject('vendor/leaflet/').catch(() => inject(CDN));
  async function start() {
    render();
    if (map || mapErr) { if (map) setTimeout(() => map.invalidateSize(), 50); return; }
    try { await loadLeaflet(); } catch (e) { mapErr = 'Map library could not load. Connect to the internet or run "npm install" once. Stats, filters and dispatch still work.'; $('dmMapMsg').textContent = mapErr; return; }
    map = L.map('dmMap').setView(M.center, 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' })
      .on('tileerror', () => { if (!tileWarned) { tileWarned = true; $('dmMapMsg').textContent = T('Map tiles could not load. Check the internet connection; device data still updates.'); } })
      .on('tileload', () => { if (tileWarned) { tileWarned = false; $('dmMapMsg').textContent = ''; } })
      .addTo(map);
    layer = L.layerGroup().addTo(map);
    map.on('click', e => {
      if (!pick) return;
      $('dmeLat').value = e.latlng.lat.toFixed(5); $('dmeLng').value = e.latlng.lng.toFixed(5);
      pick = false; $('dmePick').classList.remove('on'); $('dmMapMsg').textContent = T('Location picked. Press Save.'); $('dmEditBox').open = true;
    });
    render();
  }
  function toggle(on) {
    shown = on;
    document.body.classList.toggle('dm-on', on);
    $('mapView').hidden = !on;
    $('bMapNav').textContent = T(on ? 'Back to monitor' : 'City drainage map');
    $('bMapNav').setAttribute('aria-pressed', on);
    if (on) gate(); else window.scrollTo(0, 0);
  }
  $('bMapNav').onclick = () => toggle(!shown);

  /* ---------- live data ---------- */
  const prev = window.onData;
  if (typeof prev === 'function') {
    onData = function (d) {
      prev(d);
      try {
        const id = String((d && d.node) || 'drain-1'), st = states().find(s => s.id === id);
        if (st) track(st);
        if (shown && !$('mapView').hidden && !$('dmBody').hidden) render();
      } catch (e) { try { window.flowbeacon && window.flowbeacon.log('map: ' + (e.stack || e)); } catch (x) {} }
    };
  }
  setInterval(() => { if (shown && !$('dmBody').hidden) render(); }, 3000);
  window.fbMap = { states, openInc, get data() { return M; } };
})();
