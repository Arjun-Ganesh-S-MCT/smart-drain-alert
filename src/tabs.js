/* Tabbed layout: one section group per tab, so the window never needs page-level scrolling.
   Moves the existing sections (same elements, same IDs and listeners) into tab pages. */
(function () {
  'use strict';
  const TABS = [
    ['overview', 'Overview', 'devices'], ['model', 'Drain model', 'zone'], ['incidents', 'Incidents', 'blockage'],
    ['connect', 'Connection', 'connect'], ['history', 'History', 'resolved'], ['calib', 'Calibration', 'calibration'],
    ['drip', 'Ask Drip', 'team'], ['settings', 'Settings', 'status'], ['console', 'Console', 'update'], ['map', 'City map', 'map']
  ];
  const RULES = [[/drain model/, 'model'], [/incident reports/, 'incidents'], [/^connection/, 'connect'], [/^history/, 'history'],
    [/learn from recordings|calibration dials/, 'calib'], [/ask drip/, 'drip'], [/appearance/, 'settings'], [/firmware console/, 'console']];
  const T = s => (window.trans ? window.trans(s) : s);
  const nav = document.querySelector('nav.toolbar');
  if (!nav) return;

  const pages = document.createElement('main');
  pages.id = 'pages';
  const groups = {};
  TABS.forEach(([k]) => { const g = document.createElement('div'); g.className = 'pg'; g.dataset.pg = k; g.hidden = true; groups[k] = g; pages.appendChild(g); });

  const items = [...document.body.children].filter(e => e !== nav && e.tagName !== 'HEADER' && e.tagName !== 'SCRIPT' && e.id !== 'ban' && e.id !== 'drip' && e.id !== 'rep' && e.id !== 'fbUp' && !e.matches('link,style'));
  items.forEach(e => {
    let key = 'overview';
    if (e.id === 'mapView') key = 'map';
    else {
      const h = [...e.querySelectorAll('h2')].map(x => x.textContent.trim().toLowerCase());
      for (const [re, k] of RULES) if (h.some(t => re.test(t))) { key = k; break; }
    }
    groups[key].appendChild(e);
  });

  const bar = document.createElement('nav');
  bar.id = 'tabs'; bar.setAttribute('role', 'tablist'); bar.setAttribute('aria-label', 'Sections');
  bar.innerHTML = TABS.map(([k, n, i]) => '<button class="tab" role="tab" data-t="' + k + '" id="tab-' + k + '" style="--ic:var(--i-' + i + ')">' + T(n) + '</button>').join('');
  nav.after(bar);
  const ban = document.getElementById('ban');
  (ban || bar).after(pages);
  if (ban) bar.after(ban);

  let cur = '';
  const allowed = k => !window.fbRole || window.fbRole.can(k);
  function show(k, focus) {
    if (!groups[k] || !allowed(k)) k = 'overview';
    const wasMap = cur === 'map';
    cur = k;
    Object.keys(groups).forEach(g => { groups[g].hidden = g !== k; });
    bar.querySelectorAll('.tab').forEach(b => { const on = b.dataset.t === k; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1; });
    if (window.fbMap && window.fbMap.show) { if (k === 'map') window.fbMap.show(true); else if (wasMap) window.fbMap.show(false); }
    pages.scrollTop = 0;
    try { localStorage.setItem('fbtab', k); } catch (e) {}
    if (focus) document.getElementById('tab-' + k).focus();
    // charts measure their size when drawn, so redraw now that the page is visible
    requestAnimationFrame(() => { try { if (typeof draw === 'function') draw(); } catch (e) {} window.dispatchEvent(new Event('resize')); });
  }
  bar.onclick = e => { const b = e.target.closest('.tab'); if (b) show(b.dataset.t); };
  bar.onkeydown = e => {
    const ks = TABS.map(t => t[0]).filter(allowed), i = ks.indexOf(cur);
    if (e.key === 'ArrowRight') { e.preventDefault(); show(ks[(i + 1) % ks.length], true); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); show(ks[(i + ks.length - 1) % ks.length], true); }
  };
  const old = document.getElementById('bMapNav');            // the toolbar map button now just opens the tab
  if (old) old.onclick = () => show(cur === 'map' ? 'overview' : 'map');
  function applyRole() {
    bar.querySelectorAll('.tab').forEach(b => { b.hidden = !allowed(b.dataset.t); });
    if (!allowed(cur)) show('overview');
  }
  document.addEventListener('fbrole', applyRole);
  window.fbTabs = { show };

  let start = 'overview';
  try { start = localStorage.getItem('fbtab') || start; } catch (e) {}
  show(start);
  applyRole();
  document.dispatchEvent(new Event('fbtabs-ready'));
})();
