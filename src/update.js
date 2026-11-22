/* Update popup. In the desktop app the main process downloads updates silently (electron-updater)
   and this shows progress. When index.html is opened in a plain browser there is nothing to install into,
   so it checks GitHub and offers the download page. Keep VERSION equal to package.json (tests enforce it). */
(function () {
  'use strict';
  const VERSION = '1.4.0';
  const REPO = 'Arjun-Ganesh-S-MCT/smart-drain-alert';
  const FB = window.flowbeacon || {};
  const T = s => (window.trans ? window.trans(s) : s);

  const css = document.createElement('style');
  css.textContent = '#fbUp{position:fixed;left:50%;top:18px;transform:translateX(-50%);z-index:50;min-width:280px;max-width:min(92vw,460px);padding:16px 20px;border-radius:20px;background:var(--bg);color:var(--tx);box-shadow:8px 8px 16px var(--sd),-8px -8px 16px var(--sl);display:none}' +
    '#fbUp b{display:block;margin-bottom:4px;color:var(--ac)}#fbUp .bar{height:10px;border-radius:99px;margin:10px 0 2px;overflow:hidden;box-shadow:inset 3px 3px 6px var(--sd),inset -3px -3px 6px var(--sl)}' +
    '#fbUp .bar i{display:block;height:100%;width:0;background:var(--ac);transition:width .3s}#fbUp .r{display:flex;gap:10px;justify-content:flex-end;margin-top:12px;flex-wrap:wrap}';
  document.head.appendChild(css);
  const box = document.createElement('div');
  box.id = 'fbUp'; box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite');
  document.body.appendChild(box);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const show = html => { box.innerHTML = html; box.style.display = 'block'; };
  const hide = () => { box.style.display = 'none'; };

  // Desktop app: progress from the main process
  if (FB.onUpdate) {
    FB.onUpdate(u => {
      if (u.state === 'available') show('<b>' + T('Updating FlowBeacon') + '</b>' + esc(T('Version') + ' ' + u.version + ' ' + T('found. Downloading…')) + '<div class="bar"><i></i></div>');
      else if (u.state === 'downloading') {
        if (!box.querySelector('.bar')) show('<b>' + T('Updating FlowBeacon') + '</b>' + T('Downloading…') + '<div class="bar"><i></i></div>');
        box.querySelector('.bar i').style.width = u.percent + '%';
      } else if (u.state === 'ready') {
        // fully automatic: restart into the new version after a short countdown ("Later" installs on next close instead)
        let n = 8;
        const go = () => { clearInterval(t); show('<b>' + T('Updating FlowBeacon') + '</b>' + T('Restarting…')); FB.installUpdate(); };
        const paint = () => {
          show('<b>' + T('Update downloaded') + '</b>' + esc(T('Version') + ' ' + u.version + ' · ' + T('restarting to install in') + ' ' + n + ' s') +
            '<div class="r"><button id="fbUpLater">' + T('Later') + '</button><button id="fbUpNow">' + T('Restart now') + '</button></div>');
          document.getElementById('fbUpLater').onclick = () => { clearInterval(t); hide(); };
          document.getElementById('fbUpNow').onclick = go;
        };
        const t = setInterval(() => { n--; if (n <= 0) go(); else paint(); }, 1000);
        paint();
      } else if (u.state === 'error') hide();
    });
    // re-check every 4 hours while the app stays open (the start-up check is in features.js)
    setInterval(() => { try { if (typeof S === 'undefined' || S.upd !== false) FB.checkUpdate && FB.checkUpdate(); } catch (e) {} }, 4 * 3600 * 1000);
    return;
  }

  // Plain browser (.html opened directly): notify only
  const cmp = (a, b) => { const x = String(a).split('.').map(Number), y = String(b).split('.').map(Number); for (let i = 0; i < 3; i++) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0); return 0; };
  async function check() {
    try {
      const r = await fetch('https://api.github.com/repos/' + REPO + '/releases/latest', { headers: { Accept: 'application/vnd.github+json' } });
      if (!r.ok) return;
      const j = await r.json(), latest = String(j.tag_name || '').replace(/^v/, '');
      if (!latest || cmp(latest, VERSION) <= 0) return;
      show('<b>' + T('New version available') + '</b>' + esc('FlowBeacon ' + latest + ' (' + T('you have') + ' ' + VERSION + '). ') + T('A web page cannot update itself: download the new version to get the latest features.') +
        '<div class="r"><button id="fbUpLater">' + T('Later') + '</button><a id="fbUpGo" target="_blank" rel="noopener"><button>' + T('Download') + '</button></a></div>');
      document.getElementById('fbUpGo').href = String(j.html_url).startsWith('https://github.com/') ? j.html_url : 'https://github.com/' + REPO + '/releases/latest';
      document.getElementById('fbUpLater').onclick = hide;
    } catch (e) { /* offline: stay quiet */ }
  }
  setTimeout(check, 2000);
  setInterval(check, 4 * 3600 * 1000);
})();
