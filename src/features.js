(function () {
  const FB = window.flowbeacon || {};
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const logErr = m => { try { if (FB.log) FB.log(String(m)); } catch (e) {} };
  window.addEventListener('error', e => logErr('error: ' + e.message + ' @' + (e.filename || '') + ':' + e.lineno));
  window.addEventListener('unhandledrejection', e => logErr('rejection: ' + ((e.reason && e.reason.stack) || e.reason)));

  S.mode = S.mode || (S.theme === 'dark' ? 'dark' : 'light');
  S.accent = S.accent || 'coral';
  S.lang = S.lang || 'en';
  S.zoom = S.zoom || 1;
  S.snd = Object.assign({ ui: true, possible: true, warning: true, risk: true, overflow: true, rain: true, predict: true }, S.snd);
  S.quiet = Object.assign({ on: false, from: '22:00', to: '06:00', smsMin: 3 }, S.quiet);
  S.profiles = S.profiles || [];
  if (!S.nodes || !Object.keys(S.nodes).length) S.nodes = { 'drain-1': { name: 'Drain 1', base: S.base || null } };
  if (S.notify === undefined) S.notify = true;
  if (S.upd === undefined) S.upd = true;

  const T = (bg, sd, sl, tx, mu, ac, on) => ({ bg, sd, sl, tx, mu, ac, on });
  const THEMES = {
    coral: { n: 'Coral', c: '#fc8068', light: T('#e0d9d3', '#bdb3ac', '#f4f0ea', '#6b625b', '#948a82', '#fc8068', '#ffffff'), dark: T('#2f2a27', '#1f1b19', '#3f3935', '#e6ded8', '#a1958c', '#ff8f78', '#2a1f1c') },
    blue: { n: 'Blue', c: '#4f86c6', light: T('#d9dfe7', '#b3bccb', '#f2f5f9', '#4d5a6b', '#8793a3', '#4f86c6', '#ffffff'), dark: T('#262b33', '#181c21', '#343b46', '#dde3ec', '#8f9bad', '#6aa3f0', '#13202f') },
    green: { n: 'Green', c: '#3f9a63', light: T('#d9e2da', '#b2c0b4', '#f1f6f2', '#4b5f50', '#84998a', '#3f9a63', '#ffffff'), dark: T('#232b25', '#161c18', '#313b34', '#dbe6dd', '#8ea294', '#62c283', '#102014') },
    purple: { n: 'Purple', c: '#8a6bc9', light: T('#e0dbe7', '#bab3c8', '#f5f2f9', '#5b5270', '#928aa6', '#8a6bc9', '#ffffff'), dark: T('#2a2631', '#1b1820', '#39343f', '#e4dff0', '#9d94b2', '#a78bfa', '#1c1230') },
    red: { n: 'Red', c: '#d9444f', light: T('#e6dada', '#c4b0b0', '#f7f0f0', '#6b4f4f', '#9b8484', '#d9444f', '#ffffff'), dark: T('#2e2626', '#1e1818', '#3d3333', '#ecdddd', '#a99090', '#f06a73', '#2e1012') },
    yellow: { n: 'Yellow', c: '#e8b422', light: T('#e5e0d0', '#c4bda5', '#f7f4ea', '#655f48', '#968f74', '#e8b422', '#3b2f05'), dark: T('#2d2a22', '#1e1c16', '#3b372d', '#ece6d2', '#a79f84', '#f5c542', '#2b2205') },
    black: { n: 'Black', c: '#2b2b2b', light: T('#dcdcdc', '#b8b8b8', '#f3f3f3', '#3a3a3a', '#7d7d7d', '#2b2b2b', '#ffffff'), dark: T('#1c1c1c', '#0e0e0e', '#2a2a2a', '#e6e6e6', '#8a8a8a', '#f2f2f2', '#111111') }
  };
  const TINT = { coral: '', blue: 'hue-rotate(205deg)', green: 'hue-rotate(125deg)', purple: 'hue-rotate(255deg)', red: 'hue-rotate(-15deg)', yellow: 'hue-rotate(40deg) saturate(1.2)', black: 'grayscale(1) brightness(.5)' };

  function applyTheme() {
    const dark = S.mode === 'auto' ? matchMedia('(prefers-color-scheme: dark)').matches : S.mode === 'dark';
    const th = THEMES[S.accent] || THEMES.coral, p = th[dark ? 'dark' : 'light'];
    const st = document.documentElement.style;
    for (const k in p) st.setProperty('--' + k, p[k]);
    const cs = getComputedStyle(document.documentElement);
    AC = cs.getPropertyValue('--ac').trim() || AC;
    MU = cs.getPropertyValue('--mu').trim() || MU;
    TX = cs.getPropertyValue('--tx').trim() || TX;
    Object.keys(EL).forEach(k => { if (/^(body|arm|umbrella|sweat)/.test(k)) EL[k].style.filter = TINT[S.accent] || ''; });
    document.querySelectorAll('.dial').forEach(el => dialDraw(el));
    draw();
  }
  window.applyTheme = applyTheme;
  if (matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (S.mode === 'auto') applyTheme(); });

  function applyCalm() {
    document.documentElement.classList.toggle('calm', !!S.calm);
    document.documentElement.style.zoom = S.zoom;
  }

  const TA = {
    'Sound': 'ஒலி', 'Drip': 'டிரிப்', 'Connect ESP32-S3': 'ESP32-S3 இணை', 'Demo mode': 'டெமோ முறை', 'Set baseline': 'அடிப்படை அளவை அமை', 'Calibration': 'அளவுத்திருத்தம்',
    'Acknowledge': 'ஏற்றுக்கொள்', 'Not connected': 'இணைக்கப்படவில்லை', 'Connected': 'இணைக்கப்பட்டது', 'Waiting for data': 'தரவுக்காக காத்திருக்கிறது',
    'Connect the board or start demo mode.': 'போர்டை இணைக்கவும் அல்லது டெமோ முறையைத் தொடங்கவும்.', 'Demo scenario:': 'டெமோ சூழல்:', 'Normal': 'இயல்பு', 'Partial valve': 'பகுதி வால்வு',
    'Rain': 'மழை', 'Blockage + rain': 'அடைப்பு + மழை', 'Overflow': 'வழிதல்', 'Water flow': 'நீர் ஓட்டம்', 'Distance to water surface': 'நீர் மேற்பரப்புக்கான தூரம்', 'Turbidity': 'கலங்கல்',
    'Rain sensor plate': 'மழை உணரி தகடு', 'Baseline not set': 'அடிப்படை அளவு அமைக்கப்படவில்லை', 'Wet or dry only': 'ஈரம் அல்லது உலர் மட்டும்', 'Drain model': 'வடிகால் மாதிரி', 'Trend': 'போக்கு',
    'Last 90': 'கடைசி 90', 'Last 300': 'கடைசி 300', 'Last 900': 'கடைசி 900', 'Flow': 'ஓட்டம்', 'water level': 'நீர்மட்டம்', 'Incident reports': 'நிகழ்வு அறிக்கைகள்', 'All': 'அனைத்தும்',
    'Warning+': 'எச்சரிக்கை+', 'Risk+': 'அபாயம்+', 'PDF report': 'PDF அறிக்கை', 'Clear': 'அழி', 'Test recording': 'சோதனைப் பதிவு', 'Label for this session': 'இந்த அமர்வின் பெயர்',
    'Start recording': 'பதிவைத் தொடங்கு', 'Stop recording': 'பதிவை நிறுத்து', 'Save CSV': 'CSV சேமி', 'Calibration wizard': 'அளவுத்திருத்த வழிகாட்டி', 'Press Calibration to start.': 'தொடங்க அளவுத்திருத்தத்தை அழுத்தவும்.',
    'Record step': 'படியைப் பதிவு செய்', 'Apply thresholds': 'எல்லைகளைப் பயன்படுத்து', 'Connection': 'இணைப்பு', 'Wi-Fi': 'வைஃபை', 'Send to board over USB': 'USB வழியாக போர்டுக்கு அனுப்பு',
    'Wi-Fi name': 'வைஃபை பெயர்', 'Wi-Fi password': 'வைஃபை கடவுச்சொல்', 'Show': 'காட்டு', 'Hide': 'மறை', 'Board address (IP)': 'போர்டு முகவரி (IP)', 'Connect': 'இணை', 'Disconnect': 'துண்டி',
    'SMS alerts': 'SMS எச்சரிக்கைகள்', 'Send SMS alerts': 'SMS எச்சரிக்கை அனுப்பு', 'Mobile numbers (separate with commas)': 'மொபைல் எண்கள் (காற்புள்ளியால் பிரிக்கவும்)', 'Send when': 'எப்போது அனுப்ப வேண்டும்',
    'Blockage warning or worse': 'அடைப்பு எச்சரிக்கை அல்லது மோசம்', 'Overflow risk or worse': 'வழிதல் அபாயம் அல்லது மோசம்', 'Overflow detected only': 'வழிதல் கண்டறியப்பட்டால் மட்டும்',
    'Wait between SMS': 'SMS இடைவெளி', '1 minute': '1 நிமிடம்', '5 minutes': '5 நிமிடங்கள்', '10 minutes': '10 நிமிடங்கள்', '30 minutes': '30 நிமிடங்கள்', 'Send test SMS': 'சோதனை SMS அனுப்பு',
    'Open in phone app': 'போன் செயலியில் திற', 'Calibration dials': 'அளவுத்திருத்த டயல்கள்', 'Reset thresholds': 'எல்லைகளை மீட்டமை', 'Firmware console': 'ஃபர்ம்வேர் கன்சோல்', 'Send': 'அனுப்பு',
    'Run first-time setup again': 'முதல்முறை அமைப்பை மீண்டும் இயக்கு', 'Flow drop: possible (%)': 'ஓட்டக் குறைவு: சாத்தியம் (%)', 'Flow drop: blockage (%)': 'ஓட்டக் குறைவு: அடைப்பு (%)',
    'Level rise warning (cm)': 'நீர்மட்ட உயர்வு எச்சரிக்கை (செ.மீ)', 'Overflow risk distance (cm)': 'வழிதல் அபாய தூரம் (செ.மீ)', 'Overflow distance (cm)': 'வழிதல் தூரம் (செ.மீ)', 'Turbidity change (%)': 'கலங்கல் மாற்றம் (%)',
    'Possible blockage': 'அடைப்பு சாத்தியம்', 'Blockage warning': 'அடைப்பு எச்சரிக்கை', 'Overflow risk': 'வழிதல் அபாயம்', 'Overflow detected': 'வழிதல் கண்டறியப்பட்டது',
    'None': 'இல்லை', 'Low': 'குறைவு', 'Medium': 'நடுத்தரம்', 'High': 'அதிகம்', 'Critical': 'மிக அபாயம்', 'Severity': 'தீவிரம்', 'severity': 'தீவிரம்', 'Confidence': 'நம்பகத்தன்மை', 'confidence': 'நம்பகத்தன்மை',
    '(estimate)': '(மதிப்பீடு)', 'Sensor check': 'உணரி சோதனை', 'Sensors look healthy': 'உணரிகள் சீராக உள்ளன', 'Readings match baseline': 'அளவீடுகள் அடிப்படைக்கு ஏற்ப உள்ளன',
    'Set a baseline while flow is normal': 'ஓட்டம் இயல்பாக இருக்கும்போது அடிப்படை அளவை அமைக்கவும்', 'No fault indicated': 'குறைபாடு எதுவும் இல்லை',
    'Blockage and rainfall likely both contributing': 'அடைப்பும் மழையும் சேர்ந்து காரணமாக இருக்கலாம்', 'Rainfall likely contributing to rising level': 'மழையால் நீர்மட்டம் உயர்கிறது',
    'Water level high; cause unclear': 'நீர்மட்டம் அதிகம்; காரணம் தெளிவில்லை', 'Unusual pattern against baseline': 'அடிப்படைக்கு மாறான அசாதாரண முறை', 'Drains': 'வடிகால்கள்', 'Ask Drip': 'டிரிப்பிடம் கேளுங்கள்', 'Speak alerts aloud': 'எச்சரிக்கைகளை ஒலியாகச் சொல்', 'Interface sounds': 'இடைமுக ஒலிகள்', 'History': 'வரலாறு',
    'Appearance and behaviour': 'தோற்றமும் செயல்பாடும்', 'Language': 'மொழி', 'Text size': 'எழுத்து அளவு', 'Reduce motion': 'அசைவைக் குறை', 'Rename': 'பெயர் மாற்று', 'Learn from recordings': 'பதிவுகளிலிருந்து கற்றுக்கொள்',
    'Replay a recording': 'பதிவை மீண்டும் இயக்கு', 'Calibration profiles': 'அளவுத்திருத்த சுயவிவரங்கள்', 'Notifications': 'அறிவிப்புகள்', 'Quiet hours': 'அமைதி நேரம்', 'Switching…': 'மாற்றுகிறது…',
    'Hi, I am Drip!': 'வணக்கம், நான் டிரிப்!', 'Board connected.': 'போர்டு இணைக்கப்பட்டது.', 'Baseline saved!': 'அடிப்படை அளவு சேமிக்கப்பட்டது!', 'Back to normal!': 'மீண்டும் இயல்பு நிலை!',
    'Rain detected.': 'மழை கண்டறியப்பட்டது.', 'Hmm, flow looks lower than usual.': 'ம்ம், ஓட்டம் வழக்கத்தை விட குறைவு.',
    'Blockage warning! Flow is dropping while the level rises.': 'அடைப்பு எச்சரிக்கை! நீர்மட்டம் உயரும்போது ஓட்டம் குறைகிறது.', 'Overflow risk! Please check the drain.': 'வழிதல் அபாயம்! வடிகாலைச் சரிபார்க்கவும்.',
    'OVERFLOW! Water has reached the limit!': 'வழிதல்! நீர் எல்லையை எட்டியது!', 'Zzz... waiting for the board.': 'Zzz... போர்டுக்காக காத்திருக்கிறேன்.', 'Calibrating. Keep the flow steady.': 'அளவுத்திருத்தம் நடக்கிறது. ஓட்டத்தை சீராக வைக்கவும்.',
    'A sensor looks faulty. Check the wiring.': 'ஒரு உணரி பழுதாகத் தெரிகிறது. வயரிங்கைச் சரிபார்க்கவும்.'
  };
  window.trans = s => {
    if (S.lang !== 'ta' || typeof s !== 'string') return s;
    if (TA[s]) return TA[s];
    if (s.startsWith('Likely blockage: flow falling')) return 'அடைப்பு இருக்கலாம்: ஓட்டம் குறைகிறது' + (s.includes('while level rises') ? ' மற்றும் நீர்மட்டம் உயர்கிறது' : '');
    const m = s.match(/^Overflow predicted in about (\d+) min\.$/);
    return m ? 'சுமார் ' + m[1] + ' நிமிடத்தில் வழிதல் ஏற்படலாம்.' : s;
  };
  window.transEv = s => {
    if (S.lang !== 'ta') return s;
    return s.replace('Flow ', 'ஓட்டம் ').replace(' vs baseline', ' (அடிப்படையுடன்)').replace('Level +', 'நீர்மட்டம் +').replace(/ cm/g, ' செ.மீ').replace('Turbidity ', 'கலங்கல் ').replace('Anomaly ', 'அசாதாரணம் ').replace('Rain plate wet', 'மழை தகடு ஈரம்');
  };
  function applyLang() {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const todo = [];
    while (w.nextNode()) todo.push(w.currentNode);
    todo.forEach(n => {
      const p = n.parentNode && n.parentNode.nodeName;
      if (/SCRIPT|STYLE|PRE|TEXTAREA/.test(p) || (n.parentNode.closest && n.parentNode.closest('#drip,#log,#hTab'))) return;
      if (n.__o === undefined) {
        const raw = n.nodeValue, t = raw.trim();
        if (!TA[t]) return;
        n.__o = t;
        n.__w = [raw.slice(0, raw.indexOf(t)), raw.slice(raw.indexOf(t) + t.length)];
      }
      n.nodeValue = n.__w[0] + (S.lang === 'ta' ? TA[n.__o] : n.__o) + n.__w[1];
    });
  }
  window.applyLang = applyLang;
  const _bs = buildSet;
  buildSet = function () { _bs(); applyLang(); };

  const NR = {};
  let active = null;
  const ST_ = ST;
  function nrec(id) {
    if (!S.nodes[id]) S.nodes[id] = { name: 'Drain ' + (Object.keys(S.nodes).length + 1), base: null };
    if (!NR[id]) NR[id] = { hist: [], lvl: 0, prevRain: 0, predWarn: false, acked: false, smsLast: 0, smsLastLvl: 0, fault: false, last: null, rx: 0 };
    return NR[id];
  }
  function grab() { return { hist, lvl: lastLvl, prevRain, predWarn, acked, smsLast, smsLastLvl, fault: dripFault, base: S.base }; }
  function put(o, base) { hist = o.hist; lastLvl = o.lvl; prevRain = o.prevRain; predWarn = o.predWarn; acked = o.acked; smsLast = o.smsLast; smsLastLvl = o.smsLastLvl; dripFault = o.fault; S.base = base; }
  function loadN(id) { put(nrec(id), S.nodes[id].base); }
  function storeN(id) {
    const g = grab();
    Object.assign(NR[id], { hist: g.hist, lvl: g.lvl, prevRain: g.prevRain, predWarn: g.predWarn, acked: g.acked, smsLast: g.smsLast, smsLastLvl: g.smsLastLvl, fault: g.fault });
    if (S.nodes[id].base !== g.base) { S.nodes[id].base = g.base; save(); }
  }
  function allNodes() {
    return Object.keys(S.nodes).map(id => {
      const a = id === active, n = NR[id] || {};
      return { id, name: S.nodes[id].name, lvl: a ? lastLvl : (n.lvl || 0), acked: a ? acked : !!n.acked, rx: n.rx || 0, last: n.last };
    });
  }
  window.fbNodes = allNodes;
  function banner() {
    const w = allNodes().filter(x => x.lvl >= 3 && !x.acked).sort((a, b) => b.lvl - a.lvl)[0], b = $('ban');
    if (w) { b.style.display = 'flex'; $('banT').textContent = tr(ST_[w.lvl].n) + ' · ' + w.name; } else b.style.display = 'none';
  }
  $('bAck').onclick = () => { acked = true; Object.values(NR).forEach(n => { n.acked = true; }); banner(); };
  setInterval(() => allNodes().forEach(x => { if (x.lvl >= 3 && !x.acked) play(x.lvl === 4 ? 'overflow' : 'risk', true); }), 3000);

  let lastSent = -1;
  function bridge() {
    if (!FB.setLevel) return;
    let m = 0, who = '';
    allNodes().forEach(x => { if (x.lvl > m) { m = x.lvl; who = x.name; } });
    if (m !== lastSent) { lastSent = m; FB.setLevel(m, 'FlowBeacon: ' + ST_[m].n + (who ? ' (' + who + ')' : '')); }
  }

  function tiles() {
    const list = $('nodeList');
    if (!list) return;
    const now = Date.now();
    list.innerHTML = allNodes().map(x => {
      const stale = !x.rx || now - x.rx > 10000;
      const st = ST_[x.lvl];
      return '<button class="tile ' + (x.id === active ? 'on' : 'raised') + '" data-id="' + esc(x.id) + '"><b><i class="dot2" style="background:' + (stale ? 'var(--mu)' : st.c) + '"></i>' + esc(x.name) + '</b><span>' + (stale ? '–' : esc(ICO[x.lvl] + ' ' + tr(st.n))) + '</span></button>';
    }).join('');
    const sel = $('hNode');
    if (sel && sel.options.length !== Object.keys(S.nodes).length) {
      sel.innerHTML = Object.keys(S.nodes).map(id => '<option value="' + esc(id) + '">' + esc(S.nodes[id].name) + '</option>').join('');
    }
    if ($('nname') && document.activeElement !== $('nname') && active) $('nname').value = S.nodes[active] ? S.nodes[active].name : '';
  }
  function selectNode(id) {
    if (id === active || !S.nodes[id]) return;
    if (active) storeN(active);
    active = id;
    loadN(id);
    $('cond').textContent = tr('Switching…');
    tiles();
    banner();
  }

  const onBase = onData;
  onData = function (d) {
    const id = String(d.node || 'drain-1'), n = nrec(id);
    n.last = d;
    n.rx = Date.now();
    if (active === null && !/^demo-/.test(id)) { active = id; loadN(id); }
    window.curNodeName = S.nodes[id].name;
    if (id === active) { onBase(d); storeN(id); }
    else {
      const keep = grab(), cb = calBuf, wb = wz.buf, ro = rec.on;
      calBuf = null; wz.buf = null; rec.on = false; QUIET = true;
      put(n, S.nodes[id].base);
      try { onBase(d); } catch (e) { logErr(e.stack || e); }
      finally { storeN(id); QUIET = false; calBuf = cb; wz.buf = wb; rec.on = ro; put(keep, keep.base); }
    }
    histAdd(id, d, (NR[id] || {}).lvl || 0);
    if (id === active) mlShow(d);
    tiles();
    banner();
    bridge();
  };
  document.addEventListener('click', e => { const t = e.target.closest && e.target.closest('.tile'); if (t) selectNode(t.dataset.id); });
  setInterval(tiles, 3000);

  let idb = null;
  const B = {};
  let lastRows = [];
  if (window.indexedDB) {
    const rq = indexedDB.open('flowbeacon', 1);
    rq.onupgradeneeded = () => { rq.result.createObjectStore('min', { keyPath: ['node', 't'] }); };
    rq.onsuccess = () => { idb = rq.result; prune(); renderHist(); };
    rq.onerror = () => {};
  }
  function flush(b) {
    if (!idb || !b || !b.n) return;
    try { idb.transaction('min', 'readwrite').objectStore('min').put({ node: b.node, t: b.t, n: b.n, f: b.f / b.n, l: b.l / b.n, tb: b.tb / b.n, r: b.r / b.n, lvl: b.lvl }); } catch (e) {}
  }
  function histAdd(id, d, lvl) {
    const m = Math.floor(Date.now() / 60000) * 60000;
    let b = B[id];
    if (!b || b.t !== m) { flush(b); b = B[id] = { node: id, t: m, n: 0, f: 0, l: 0, tb: 0, r: 0, lvl: 0 }; }
    b.n++; b.f += +d.flow || 0; b.l += +d.dist || 0; b.tb += +d.turb || 0; b.r += d.rain ? 1 : 0; b.lvl = Math.max(b.lvl, lvl);
  }
  window.addEventListener('beforeunload', () => Object.values(B).forEach(flush));
  setInterval(() => Object.values(B).forEach(b => { if (b.t < Date.now() - 60000) flush(b); }), 60000);
  function rangeQ(node, a, b) {
    return new Promise(res => {
      if (!idb) return res([]);
      const out = [];
      const rq = idb.transaction('min').objectStore('min').openCursor(IDBKeyRange.bound([node, a], [node, b]));
      rq.onsuccess = () => { const c = rq.result; if (c) { out.push(c.value); c.continue(); } else res(out); };
      rq.onerror = () => res(out);
    });
  }
  function prune() {
    const cut = Date.now() - 90 * 864e5;
    Object.keys(S.nodes).forEach(id => rangeQ(id, 0, cut).then(rows => {
      if (!rows.length) return;
      const st = idb.transaction('min', 'readwrite').objectStore('min');
      rows.forEach(r => st.delete([r.node, r.t]));
    }));
  }
  async function renderHist() {
    if (!$('hcv') || !idb) return;
    const id = $('hNode').value || active || 'drain-1', days = +$('hRange').value, now = Date.now();
    const rows = await rangeQ(id, now - days * 864e5, now);
    lastRows = rows;
    const hourly = days === 1, grp = new Map();
    rows.forEach(r => {
      const k = hourly ? Math.floor(r.t / 36e5) * 36e5 : new Date(r.t).setHours(0, 0, 0, 0);
      let g = grp.get(k);
      if (!g) { g = { t: k, n: 0, f: 0, l: 0, lmin: 1e9, lmax: -1e9, lvl: 0 }; grp.set(k, g); }
      g.n += r.n; g.f += r.f * r.n; g.l += r.l * r.n; g.lmin = Math.min(g.lmin, r.l); g.lmax = Math.max(g.lmax, r.l); g.lvl = Math.max(g.lvl, r.lvl);
    });
    const list = [...grp.values()].sort((a, b) => a.t - b.t).map(g => Object.assign({}, g, { f: g.f / g.n, l: g.l / g.n }));
    const cv = $('hcv'), x = cv.getContext('2d'), w = cv.width, h = cv.height;
    x.clearRect(0, 0, w, h);
    const line = (k, col, inv) => {
      if (list.length < 2) return;
      const a = list.map(p => p[k]);
      let mn = Math.min(...a), mx = Math.max(...a);
      if (mx - mn < 0.5) mx = mn + 0.5;
      x.beginPath(); x.lineWidth = 3; x.lineJoin = 'round'; x.strokeStyle = col;
      a.forEach((y, i) => { const px = i / (a.length - 1) * (w - 20) + 10, q = (y - mn) / (mx - mn), py = (inv ? q : 1 - q) * (h - 44) + 12; i ? x.lineTo(px, py) : x.moveTo(px, py); });
      x.stroke();
    };
    line('f', AC, false); line('l', TX, true);
    list.forEach((g, i) => { x.fillStyle = ST_[g.lvl].c; const px = list.length > 1 ? i / (list.length - 1) * (w - 20) + 10 : w / 2; x.fillRect(px - 3, h - 18, 6, 10); });
    const fmt = t => hourly ? new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : new Date(t).toLocaleDateString();
    $('hTab').innerHTML = '<tr><th>' + (hourly ? 'Hour' : 'Day') + '</th><th>Minutes</th><th>Avg flow</th><th>Level min/max (cm)</th><th>Worst</th></tr>' +
      list.slice().reverse().slice(0, 14).map(g => '<tr><td>' + fmt(g.t) + '</td><td>' + g.n + '</td><td>' + g.f.toFixed(2) + '</td><td>' + g.lmin.toFixed(1) + ' / ' + g.lmax.toFixed(1) + '</td><td style="color:' + ST_[g.lvl].c + '">' + esc(ICO[g.lvl] + ' ' + tr(ST_[g.lvl].n)) + '</td></tr>').join('');
  }

  function mlShow(d) {
    if (!S.useModel || !S.model || !S.base) { if ($('ml')) $('ml').textContent = ''; return; }
    const p = Core.predictNB(S.model, Core.features(d, S.base));
    $('ml').textContent = 'Learned model: ' + p.label + ' (' + Math.round(p.p * 100) + '%)';
  }
  async function readCsv(file) { return Core.parseCSV(await file.text()).map(r => Object.assign(r, { label: r.label || file.name.replace(/\.csv$/i, '') })); }
  let replaying = false;
  const stopDemoBase = stopDemo;
  stopDemo = function () { stopDemoBase(); replaying = false; const g = document.getElementById('rGo'); if (g) g.textContent = 'Play'; };
  function stopReplay() { stopDemo(); }
  function startReplay(rows, speed) {
    stopDemo();
    if (!S.base && rows.length >= 10) mkBase(rows.slice(0, 10));
    let i = 0;
    $('conn').innerHTML = '<span class="dot" style="background:var(--p1)"></span>Replay';
    demo = setInterval(() => {
      if (i >= rows.length) { stopDemo(); $('rMsg').textContent = 'Replay finished.'; return; }
      const x = rows[i++];
      onData({ flow: x.flow, dist: x.dist, turb: x.turb, rain: x.rain });
    }, Math.max(40, 1000 / speed));
    $('rMsg').textContent = 'Playing ' + rows.length + ' readings…';
    replaying = true;
    $('rGo').textContent = 'Stop';
  }

  function report() {
    let img = '';
    try { img = $('cv').toDataURL('image/png'); } catch (e) {}
    const c = [0, 0, 0, 0, 0];
    S.inc.forEach(i => { c[i.lvl]++; });
    $('rep').innerHTML = '<img src="img/techminds.png" style="height:60px"><h1 style="color:#000;background:none">FlowBeacon: incident report</h1><p>Generated ' + new Date().toLocaleString() + '. Prototype estimates, not confirmed measurements.</p>' +
      '<h3>Summary</h3><table><tr><th>Incidents</th><th>Possible blockage</th><th>Blockage warning</th><th>Overflow risk</th><th>Overflow</th></tr><tr><td>' + S.inc.length + '</td><td>' + c[1] + '</td><td>' + c[2] + '</td><td>' + c[3] + '</td><td>' + c[4] + '</td></tr></table>' +
      (img ? '<h3>Recent trend</h3><img src="' + img + '" style="width:100%;max-height:220px">' : '') +
      '<h3>Incidents</h3><table><tr><th>Time</th><th>Drain</th><th>Condition</th><th>Likely cause</th><th>Sensor evidence</th><th>Severity</th><th>Confidence</th></tr>' +
      S.inc.map(i => '<tr><td>' + i.time.toLocaleString() + '</td><td>' + esc(i.node || '') + '</td><td>' + esc(i.cond) + '</td><td>' + esc(i.cause) + '</td><td>' + esc(i.ev) + '</td><td>' + esc(i.sev) + '</td><td>' + i.conf + '%</td></tr>').join('') + '</table>';
    print();
  }

  const swi = (id, label) => '<div class="row" style="justify-content:space-between;margin-top:10px"><span>' + label + '</span><label class="sw"><input type="checkbox" id="' + id + '" aria-label="' + label + '"><i></i></label></div>';
  const sel = (id, label, opts) => '<label class="fld">' + label + '</label><select id="' + id + '">' + opts.map(o => '<option value="' + o[0] + '">' + o[1] + '</option>').join('') + '</select>';

  const grid = document.querySelector('.grid');
  grid.insertAdjacentHTML('beforebegin', '<section class="raised card" id="nodes" style="margin-bottom:24px"><h2>Drains</h2><div class="row" id="nodeList"></div><div class="row fld"><input type="text" id="nname" style="flex:1;min-width:160px" aria-label="Drain name"><button id="bNr">Rename</button></div></section>');
  const anchor = $('set').closest('section');
  anchor.insertAdjacentHTML('beforebegin',
    '<section class="raised card" id="histCard" style="margin-bottom:24px"><div class="row" style="justify-content:space-between;margin-bottom:12px"><h2 style="margin:0">History</h2><div class="row"><select id="hNode" style="width:auto"></select><select id="hRange" style="width:auto"><option value="1">24 hours</option><option value="7">7 days</option><option value="30">30 days</option></select><button id="hGo">Refresh</button><button id="hCsv">Export CSV</button></div></div><div class="inset" style="padding:8px"><canvas id="hcv" width="900" height="190"></canvas></div><div style="overflow:auto;margin-top:12px"><table class="h" id="hTab"></table></div></section>' +
    '<div class="wide"><section class="raised card"><h2>Learn from recordings</h2><p class="sub">Load the labelled CSV files saved by Test recording (normal, partial valve, rain and so on). Set the baseline first.</p><input type="file" id="mFiles" accept=".csv" multiple style="display:none"><div class="row"><button id="mPick">Choose CSV files</button><button id="mTrain" disabled>Train</button><button id="mHdr" disabled>Export model.h</button><button id="mJson" disabled>Export JSON</button></div>' + swi('mUse', 'Use learned model') + '<p class="sub" id="mMsg"></p></section>' +
    '<section class="raised card"><h2>Replay a recording</h2><input type="file" id="rFile" accept=".csv" style="display:none"><div class="row"><button id="rPick">Choose CSV</button><select id="rSpeed" style="width:auto"><option value="1">1x</option><option value="2">2x</option><option value="5">5x</option><option value="10">10x</option></select><button id="rGo" disabled>Play</button></div><p class="sub" id="rMsg"></p><h2 style="margin-top:18px">Calibration profiles</h2><div class="row"><select id="pSel" style="width:auto;min-width:160px"></select><button id="pApply">Apply</button><button id="pDel">Delete</button></div><div class="row fld"><input type="text" id="pName" placeholder="Profile name" style="flex:1"><button id="pSave">Save current</button></div></section></div>' +
    '<section class="raised card" id="appr" style="margin-bottom:24px"><h2>Appearance and behaviour</h2><div class="wide" style="margin:0"><div><label>Theme colour</label><div class="row" id="swatches"></div>' +
    sel('aMode', 'Mode', [['light', 'Light'], ['dark', 'Dark'], ['auto', 'Follow system']]) + sel('aLang', 'Language', [['en', 'English'], ['ta', 'தமிழ்']]) + sel('aZoom', 'Text size', [['1', 'Normal'], ['1.15', 'Large'], ['1.3', 'Extra large']]) + swi('aCalm', 'Reduce motion') +
    '</div><div>' + swi('bNot', 'Desktop notifications') + swi('bTray', 'Keep running in the tray when closed') + '<div id="rowStart">' + swi('bStart', 'Start with Windows') + '</div>' + swi('bUpd', 'Check for updates on start') +
    '<div class="row fld"><button id="bUpNow">Check now</button><button id="bLog">Open log folder</button></div><p class="sub" id="aMsg"></p></div><div><label>Sounds</label>' +
    swi('sUi', 'Interface sounds') + swi('sPos', 'Possible blockage') + swi('sWar', 'Blockage warning') + swi('sRisk', 'Overflow risk') + swi('sOver', 'Overflow') + swi('sRain', 'Rain') + swi('sPred', 'Prediction') + swi('qOn', 'Quiet hours') +
    '<div class="row fld"><input type="time" id="qFrom" style="width:auto"><span>to</span><input type="time" id="qTo" style="width:auto"></div>' + sel('qSms', 'SMS minimum during quiet hours', [['2', 'Blockage warning'], ['3', 'Overflow risk'], ['4', 'Overflow only']]) + '</div></div></section>');

  const sw = (id, obj, key, extra) => { const e = $(id); e.checked = !!obj[key]; e.onchange = ev => { obj[key] = ev.target.checked; save(); if (extra) extra(); }; };
  sw('aCalm', S, 'calm', applyCalm);
  sw('bNot', S, 'notify'); sw('bUpd', S, 'upd');
  sw('sUi', S.snd, 'ui'); sw('sPos', S.snd, 'possible'); sw('sWar', S.snd, 'warning'); sw('sRisk', S.snd, 'risk'); sw('sOver', S.snd, 'overflow'); sw('sRain', S.snd, 'rain'); sw('sPred', S.snd, 'predict'); sw('qOn', S.quiet, 'on');
  sw('mUse', S, 'useModel');
  $('qFrom').value = S.quiet.from; $('qTo').value = S.quiet.to; $('qSms').value = S.quiet.smsMin;
  $('qFrom').onchange = e => { S.quiet.from = e.target.value; save(); };
  $('qTo').onchange = e => { S.quiet.to = e.target.value; save(); };
  $('qSms').onchange = e => { S.quiet.smsMin = +e.target.value; save(); };
  $('aMode').value = S.mode; $('aMode').onchange = e => { S.mode = e.target.value; save(); applyTheme(); };
  $('aLang').value = S.lang; $('aLang').onchange = e => { S.lang = e.target.value; save(); applyLang(); renderHist(); tiles(); };
  $('aZoom').value = String(S.zoom); $('aZoom').onchange = e => { S.zoom = +e.target.value; save(); applyCalm(); };
  $('swatches').innerHTML = Object.keys(THEMES).map(k => '<button class="swatch raised' + (k === S.accent ? ' on' : '') + '" data-a="' + k + '" title="' + THEMES[k].n + '" aria-label="' + THEMES[k].n + '"><i style="background:' + THEMES[k].c + '"></i></button>').join('');
  $('swatches').onclick = e => {
    const b = e.target.closest('.swatch');
    if (!b) return;
    S.accent = b.dataset.a; save();
    $('swatches').querySelectorAll('.swatch').forEach(x => x.classList.toggle('on', x === b));
    applyTheme();
  };

  const sendSet = o => { if (FB.setSettings) FB.setSettings(o); };
  if (FB.getSettings) FB.getSettings().then(s => {
    $('bTray').checked = !!s.closeToTray; $('bStart').checked = !!s.startWithPc;
    $('rowStart').style.display = s.platform === 'win32' ? '' : 'none';
    $('aMsg').textContent = 'Version ' + s.version;
  });
  else { $('bTray').closest('.row').hidden = true; $('rowStart').hidden = true; }
  $('bTray').onchange = e => sendSet({ closeToTray: e.target.checked });
  $('bStart').onchange = e => sendSet({ startWithPc: e.target.checked });
  $('bLog').onclick = () => { if (FB.openLog) FB.openLog(); };
  function showUpd(r) { $('updT').textContent = 'FlowBeacon ' + r.latest + ' is available (you have ' + r.current + ').'; $('upd').style.display = 'flex'; $('updB').onclick = () => FB.openUrl(r.url); }
  $('bUpNow').onclick = async () => {
    if (!FB.checkUpdate) return;
    $('aMsg').textContent = 'Checking…';
    const r = await FB.checkUpdate();
    if (r.error) $('aMsg').textContent = 'Could not check: ' + r.error;
    else if (r.newer) { $('aMsg').textContent = 'Version ' + r.latest + ' is available.'; showUpd(r); }
    else $('aMsg').textContent = 'You have the latest version (' + r.current + ').';
  };
  if (FB.checkUpdate && S.upd) setTimeout(() => FB.checkUpdate().then(r => { if (r && r.newer) showUpd(r); }).catch(() => {}), 6000);

  $('bNr').onclick = () => { const v = $('nname').value.trim(); if (v && active) { S.nodes[active].name = v; save(); tiles(); $('hNode').innerHTML = ''; tiles(); } };
  $('hGo').onclick = renderHist; $('hNode').onchange = renderHist; $('hRange').onchange = renderHist;
  $('hCsv').onclick = () => dl('flowbeacon-history.csv', ['node,time,minutes,avg_flow,avg_dist,avg_turb,rain_fraction,worst_level'].concat(lastRows.map(r => [r.node, new Date(r.t).toISOString(), r.n, r.f.toFixed(3), r.l.toFixed(2), r.tb.toFixed(0), r.r.toFixed(2), r.lvl].join(','))).join('\n'), 'text/csv');
  $('bRep').onclick = report;

  function profs() { $('pSel').innerHTML = S.profiles.map((p, i) => '<option value="' + i + '">' + esc(p.name) + '</option>').join(''); }
  profs();
  $('pSave').onclick = () => { const n = $('pName').value.trim(); if (!n) return; S.profiles.push({ name: n, cfg: Object.assign({}, S.cfg), base: S.base }); save(); profs(); $('pName').value = ''; };
  $('pApply').onclick = () => { const p = S.profiles[+$('pSel').value]; if (!p) return; Object.assign(S.cfg, p.cfg); S.base = p.base || S.base; save(); buildSet(); };
  $('pDel').onclick = () => { S.profiles.splice(+$('pSel').value, 1); save(); profs(); };

  let replayRows = [], trainRows = [];
  $('rPick').onclick = () => $('rFile').click();
  $('rFile').onchange = async e => { const f = e.target.files[0]; if (!f) return; replayRows = await readCsv(f); $('rGo').disabled = !replayRows.length; $('rMsg').textContent = replayRows.length ? f.name + ': ' + replayRows.length + ' readings' : 'No readings found in that file.'; };
  $('rGo').onclick = () => { if (replaying) { stopReplay(); return; } startReplay(replayRows, +$('rSpeed').value); };
  $('mPick').onclick = () => $('mFiles').click();
  $('mFiles').onchange = async e => { trainRows = []; for (const f of e.target.files) trainRows = trainRows.concat(await readCsv(f)); $('mTrain').disabled = !trainRows.length; $('mMsg').textContent = trainRows.length + ' readings loaded.'; };
  $('mTrain').onclick = () => {
    if (!S.base) { $('mMsg').textContent = 'Set the baseline first.'; return; }
    const rows = trainRows.map(r => ({ label: r.label, x: Core.features(r, S.base) }));
    const m = Core.trainNB(rows);
    m.base = S.base; S.model = m; save();
    $('mMsg').textContent = 'Trained on ' + rows.length + ' readings, labels: ' + m.labels.join(', ') + '. Accuracy on these files: ' + Math.round(Core.accuracy(m, rows) * 100) + '%.';
    $('mHdr').disabled = false; $('mJson').disabled = false;
  };
  if (S.model) { $('mHdr').disabled = false; $('mJson').disabled = false; $('mMsg').textContent = 'Saved model: ' + S.model.labels.join(', '); }
  $('mHdr').onclick = () => dl('model.h', Core.header(S.model, S.model.base), 'text/plain');
  $('mJson').onclick = () => dl('flowbeacon-model.json', JSON.stringify(S.model), 'application/json');

  function inQuiet() {
    const q = S.quiet;
    if (!q.on) return false;
    const m = x => { const p = String(x).split(':'); return (+p[0]) * 60 + (+p[1] || 0); };
    const n = new Date(), c = n.getHours() * 60 + n.getMinutes(), a = m(q.from), b = m(q.to);
    return a <= b ? (c >= a && c < b) : (c >= a || c < b);
  }
  window.soundOff = n => {
    const ui = ['click', 'connect', 'disconnect', 'baseline', 'normal'];
    if (ui.includes(n) ? S.snd.ui === false : S.snd[n] === false) return true;
    return inQuiet() && n !== 'overflow' && n !== 'risk';
  };
  window.quietSmsMin = () => (inQuiet() ? S.quiet.smsMin : 0);
  window.notifyLevel = (r, s) => {
    if (S.notify === false || r.lvl < 2 || (inQuiet() && r.lvl < 3)) return;
    try {
      const n = new Notification('FlowBeacon: ' + tr(s.n), { body: (window.curNodeName ? window.curNodeName + ' · ' : '') + tr(r.cause) });
      n.onclick = () => { if (FB.focus) FB.focus(); };
    } catch (e) { logErr(e); }
  };

  const demoExtra = [['demo-2', 'Drain 2 (demo)', 4.1, 12.4, 870], ['demo-3', 'Drain 3 (demo)', 2.2, 10.6, 1100]];
  setInterval(() => {
    const on = $('bDemo').classList.contains('on');
    if (on) demoExtra.forEach(x => {
      if (!S.nodes[x[0]]) S.nodes[x[0]] = { name: x[1], base: { flow: 4.2, dist: 12.5, turb: 850, sf: 0.2, sd: 0.2, st: 30 } };
      const j = () => Math.random() - 0.5;
      onData({ node: x[0], flow: x[2] + j() * 0.2, dist: x[3] + j() * 0.2, turb: x[4] + j() * 30, rain: 0 });
    });
    else demoExtra.forEach(x => {
      if (!S.nodes[x[0]]) return;
      if (active === x[0]) selectNode('drain-1');
      delete S.nodes[x[0]]; delete NR[x[0]]; $('hNode').innerHTML = ''; tiles();
    });
  }, 1000);

  const ph = { x: 0, y: 0, vx: 0, vy: 0, drag: false, abs: false, sq: 1, sv: 0, pts: [], ox: 0, oy: 0, moved: false };
  const box = () => ({ w: dr.offsetWidth, h: dr.offsetHeight });
  const bot = () => { const t = $('tabs'), r = t && t.getBoundingClientRect(); return r && r.height && r.top > innerHeight / 2 ? r.top : innerHeight; };
  const syncBar = () => { const t = $('tabs'), r = t && t.getBoundingClientRect(); document.documentElement.style.setProperty('--tabh', (r && r.height && r.top > innerHeight / 2 ? Math.ceil(innerHeight - r.top) : 0) + 'px'); };
  syncBar(); addEventListener('load', syncBar); addEventListener('resize', syncBar); addEventListener('orientationchange', () => setTimeout(syncBar, 300)); document.addEventListener('fbtabs-ready', syncBar);
  const place = () => { dr.style.left = ph.x + 'px'; dr.style.top = ph.y + 'px'; };
  function toAbs() {
    if (ph.abs) return;
    const r = dr.getBoundingClientRect();
    dr.style.transition = 'none'; dr.style.left = r.left + 'px'; dr.style.top = r.top + 'px'; dr.style.right = 'auto'; dr.style.bottom = 'auto';
    ph.x = r.left; ph.y = r.top; ph.abs = true;
  }
  dr.onpointerdown = e => {
    if (e.button !== 0) return;
    toAbs(); dr.setPointerCapture(e.pointerId);
    ph.drag = true; ph.moved = false; ph.ox = e.clientX - ph.x; ph.oy = e.clientY - ph.y; ph.vx = ph.vy = 0;
    ph.pts = [{ x: ph.x, y: ph.y, t: performance.now() }]; dr.style.cursor = 'grabbing';
  };
  dr.onpointermove = e => {
    if (!ph.drag) return;
    const b = box(), nx = clamp(e.clientX - ph.ox, 0, innerWidth - b.w), ny = clamp(e.clientY - ph.oy, 0, bot() - b.h);
    if (Math.hypot(nx - ph.x, ny - ph.y) > 2) ph.moved = true;
    ph.x = nx; ph.y = ny; place();
    ph.pts.push({ x: nx, y: ny, t: performance.now() });
    if (ph.pts.length > 6) ph.pts.shift();
  };
  dr.onpointerup = () => {
    if (!ph.drag) return;
    ph.drag = false; dr.style.cursor = 'grab';
    if (!ph.moved) { if (window.dripClick) dripClick(); ph.sq = 0.9; kick(); return; }
    const a = ph.pts[0], b = ph.pts[ph.pts.length - 1], dt = Math.max(0.016, (b.t - a.t) / 1000);
    if (S.calm) { ph.vx = ph.vy = 0; return; }
    ph.vx = clamp((b.x - a.x) / dt, -2500, 2500); ph.vy = clamp((b.y - a.y) / dt, -2500, 2500);
    kick();
  };
  dr.oncontextmenu = e => {
    e.preventDefault(); toAbs();
    const b = box();
    dr.style.transition = 'left .6s cubic-bezier(.3,1.5,.5,1),top .6s cubic-bezier(.3,1.5,.5,1)';
    ph.x = innerWidth - b.w - 22; ph.y = bot() - b.h - 16; ph.vx = ph.vy = 0; place();
    setTimeout(() => { dr.style.transition = 'none'; }, 700);
  };
  addEventListener('resize', () => { if (!ph.abs) return; const b = box(); ph.x = clamp(ph.x, 0, innerWidth - b.w); ph.y = clamp(ph.y, 0, bot() - b.h); place(); });

  const FL = [];
  window.fling = (el, k, v) => {
    const [mn, mx, st] = DL[k];
    if (S.calm || Math.abs(v) < st * 3) return;
    const lim = (mx - mn) * 3;
    FL.push({ el, k, x: S.cfg[k], v: clamp(v, -lim, lim) });
    knobSpin();
    kick();
  };
  window.flingStop = el => { for (let i = FL.length - 1; i >= 0; i--) if (FL[i].el === el) FL.splice(i, 1); };
  const W = { y: 167, amp: 0, ph: 0 };
  function paintWater() {
    const wt = $('water');
    if (!wt) return;
    let d = 'M23 168 L23 ' + W.y.toFixed(1);
    for (let i = 0; i <= 12; i++) d += ' L' + (23 + i * 114 / 12).toFixed(1) + ' ' + (W.y + W.amp * Math.sin(W.ph + i * 0.9)).toFixed(2);
    wt.setAttribute('d', d + ' L137 168 Z');
    const sf = $('surf'), bm = $('beam');
    if (sf) { let l = ''; for (let i = 0; i <= 12; i++) l += (i ? ' L' : 'M') + (23 + i * 114 / 12).toFixed(1) + ' ' + (W.y + W.amp * Math.sin(W.ph + i * 0.9)).toFixed(2); sf.setAttribute('d', l); }
    if (bm) { const sp = 6 + Math.max(0, (W.y - 48)) * 0.16; bm.setAttribute('points', '70,48 90,48 ' + (90 + sp).toFixed(1) + ',' + W.y.toFixed(1) + ' ' + (70 - sp).toFixed(1) + ',' + W.y.toFixed(1)); }
  }
  window.setWater = p => {
    const y = 167 - p * 134;
    if (!S.calm && Math.abs(y - W.y) > 0.4) W.amp = Math.min(7, W.amp + Math.abs(y - W.y) * 1.2);
    W.y = y; paintWater(); kick();
  };
  const RP = [], dropsG = document.getElementById('drops');
  if (dropsG) {
    dropsG.innerHTML = '';
    for (let i = 0; i < 9; i++) {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('r', 3.2); dropsG.appendChild(c);
      RP.push({ c, x: 28 + Math.random() * 104, y: Math.random() * 30, v: Math.random() * 80 });
    }
  }
  let running = false, lastT = 0;
  function kick() { if (!running) { running = true; lastT = performance.now(); requestAnimationFrame(loop); } }
  function loop(t) {
    const dt = Math.min(0.033, (t - lastT) / 1000 || 0.016);
    lastT = t;
    let act = false;
    if (ph.abs && !ph.drag && !S.calm) {
      const b = box(), fl = bot() - b.h, wr = innerWidth - b.w;
      ph.vy += 1900 * dt; ph.x += ph.vx * dt; ph.y += ph.vy * dt;
      if (ph.y >= fl) {
        ph.y = fl;
        if (ph.vy > 140) { ph.sq = 1 - Math.min(0.32, ph.vy / 3000); ph.sv = 0; ph.vy = -ph.vy * 0.52; ph.vx *= 0.88; } else ph.vy = 0;
        ph.vx *= Math.pow(0.02, dt);
      }
      if (ph.y < 0) { ph.y = 0; ph.vy = -ph.vy * 0.5; }
      if (ph.x < 0) { ph.x = 0; ph.vx = -ph.vx * 0.6; }
      if (ph.x > wr) { ph.x = wr; ph.vx = -ph.vx * 0.6; }
      if (Math.abs(ph.vx) > 6 || Math.abs(ph.vy) > 6 || ph.y < fl - 1) act = true; else { ph.vx = ph.vy = 0; }
      place();
    }
    ph.sv += ((1 - ph.sq) * 400 - ph.sv * 18) * dt; ph.sq += ph.sv * dt;
    if (Math.abs(ph.sq - 1) > 0.003 || Math.abs(ph.sv) > 0.02) act = true; else { ph.sq = 1; ph.sv = 0; }
    const air = ph.abs && ph.y < bot() - dr.offsetHeight - 1;
    $('dsq').style.transform = 'rotate(' + (air ? clamp(ph.vx * 0.012, -25, 25) : 0) + 'deg) scale(' + (1 / Math.sqrt(ph.sq)).toFixed(3) + ',' + ph.sq.toFixed(3) + ')';
    for (let i = FL.length - 1; i >= 0; i--) {
      const f = FL[i], [mn, mx, st] = DL[f.k];
      f.v *= Math.pow(0.03, dt); f.x += f.v * dt;
      if (f.x < mn) { f.x = mn; f.v = -f.v * 0.4; } else if (f.x > mx) { f.x = mx; f.v = -f.v * 0.4; }
      dialSet(f.el, f.x);
      if (Math.abs(f.v) < st * 2) FL.splice(i, 1); else act = true;
    }
    if (W.amp > 0.05) { W.amp *= Math.pow(0.25, dt); W.ph += dt * 9; paintWater(); act = true; } else W.amp = 0;
    if (prevRain && !S.calm) {
      RP.forEach(p => {
        p.v += 520 * dt; p.y += p.v * dt;
        if (p.y >= W.y) { p.y = -4; p.v = Math.random() * 60; p.x = 28 + Math.random() * 104; W.amp = Math.min(5, W.amp + 0.35); }
        p.c.setAttribute('cx', p.x.toFixed(1)); p.c.setAttribute('cy', p.y.toFixed(1));
      });
      act = true;
    }
    if (act) requestAnimationFrame(loop); else running = false;
  }
  setInterval(() => { if (prevRain) kick(); }, 1000);

  window.__nodes = { NR, selectNode, allNodes, TINT, THEMES, get active() { return active; } };
  applyTheme();
  applyCalm();
  applyLang();
  tiles();
  paintWater();
  renderLog();
})();
