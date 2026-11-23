/* More life for Drip: idle behaviours, new moods, tap combos, hover wave, water-drop trail and splash. */
(function () {
  'use strict';
  if (typeof EX === 'undefined' || !document.getElementById('drip')) return;
  const el = document.getElementById('drip'), body = document.getElementById('dbody');
  const calm = () => !!S.calm || document.documentElement.classList.contains('calm');
  const rnd = (a, b) => a + Math.random() * (b - a);
  const say = t => { if (!S.dripVoice) return t; return ''; };   // idle chatter is not read aloud

  Object.assign(EX, {
    yawn: { e: 'c', m: 'mouth_open', l: 'arm_up2', r: 'arm_up', a: 'stretch' },
    dance: { e: 'c', m: 'mouth_open', l: 'arm_up2', r: 'arm_up', a: 'dance' },
    sing: { e: 'c', m: 'mouth_open', l: 'arm_left', r: 'arm_right', a: 'sway' },
    giggle: { e: 'c', m: 'mouth_smile', l: 'arm_left', r: 'arm_right', a: 'wiggle' },
    gasp: { e: 'o', b: 'brows_up', m: 'mouth_scream', l: 'arm_up2', r: 'arm_up', a: 'hop' },
    grumpy: { e: 'o', b: 'brows_angry', m: 'mouth_worried', l: 'arm_left', r: 'arm_right', a: 'shiver' }
  });

  /* ---- particles ---- */
  const COLORS = ['#4fa8e0', '#7cc4f0', '#a8dcf8'];
  function drop(x, y, dx, dy, size, ms, bg) {
    if (calm()) return;
    const p = document.createElement('div');
    p.className = 'dpart';
    p.style.cssText = 'left:' + x + 'px;top:' + y + 'px;width:' + size + 'px;height:' + size * 1.25 + 'px' + (bg ? ';background:' + bg : '');
    document.body.appendChild(p);
    const a = p.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(.3)', opacity: 0 }], { duration: ms, easing: 'cubic-bezier(.2,.7,.4,1)' });
    a.onfinish = () => p.remove();
  }
  function burst(n, confetti) {
    const r = body.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height * .55;
    for (let i = 0; i < n; i++) {
      const ang = (i / n) * Math.PI * 2 + rnd(-.2, .2), d = rnd(50, 110);
      drop(cx, cy, Math.cos(ang) * d, Math.sin(ang) * d + 30, rnd(5, 10), rnd(550, 900), confetti ? ['#fc8068', '#e6b800', '#22b573', '#4f86c6', '#8a6bc9'][i % 5] : COLORS[i % 3]);
    }
  }

  /* ---- idle behaviours ---- */
  const hr = new Date().getHours(), greet = hr < 12 ? 'Good morning!' : hr < 17 ? 'Good afternoon!' : 'Good evening!';
  const IDLE = [
    ['wave', 2300, 'Hello there!'], ['dance', 2800, 'Drain, drain, flow away!'], ['sing', 3200, 'La la la…'],
    ['yawn', 2400, 'Quiet shift. Good.'], ['giggle', 1500, ''], ['spin', 0, 'Wheee!'], ['glance', 0, '']
  ];
  function glance() {
    [[-1, .15, 0], [1, .1, 800], [0, 0, 1700]].forEach(([x, y, t]) => setTimeout(() => { if (cur === 'idle') look(x, y); }, t));
  }
  function idleTick() {
    setTimeout(idleTick, rnd(7000, 15000));
    if (!el.offsetParent || calm() || cur !== 'idle' || Date.now() < fu || document.hidden) return;
    let pick = IDLE[Math.floor(Math.random() * IDLE.length)];
    if (prevRain) pick = ['dance', 2800, 'Singing in the rain!'];
    const [n, ms, t] = pick;
    if (n === 'glance') return glance();
    if (n === 'spin') { body.classList.add('spin'); if (t) dripSay(say(t) || t, 1500); return; }
    dripFlash(n, ms, S.dripVoice ? '' : t);
  }
  setTimeout(idleTick, 9000);
  setTimeout(() => { if (cur === 'idle' && !calm()) dripFlash('wave', 2600, greet + ' I am watching your drains.'); }, 5500);

  /* ---- hover wave (rate limited) ---- */
  let lastHover = 0;
  el.addEventListener('pointerenter', e => {
    if (e.buttons || cur !== 'idle' || Date.now() - lastHover < 9000 || Date.now() < fu) return;
    lastHover = Date.now();
    dripFlash('wave', 1500);
  });

  /* ---- tap combos and drag effects ---- */
  let taps = [], sx = 0, sy = 0, moved = false, lastTrail = 0, cheered = 0;
  el.addEventListener('pointerdown', e => { sx = e.clientX; sy = e.clientY; moved = false; });
  el.addEventListener('pointermove', e => {
    if (!e.buttons) return;
    if (Math.hypot(e.clientX - sx, e.clientY - sy) > 6) moved = true;
    if (!moved) return;
    const now = performance.now();
    if (now - cheered > 700) { cheered = now; dripFlash('cheer', 800); }
    if (now - lastTrail > 45) { lastTrail = now; drop(e.clientX + rnd(-10, 10), e.clientY + rnd(0, 20), rnd(-14, 14), rnd(30, 70), rnd(5, 9), rnd(450, 750)); }
  });
  el.addEventListener('pointerup', e => {
    if (moved) { burst(12); return; }
    const now = Date.now();
    taps = taps.filter(t => now - t < 2200); taps.push(now);
    const n = taps.length;
    if (n === 3) dripFlash('giggle', 1800, 'Hehe, that tickles!');
    else if (n === 5) dripFlash('gasp', 1600, 'Okay okay, I am awake!');
    else if (n >= 7) { taps = []; body.classList.add('spin'); dripFlash('dizzy', 2600, 'Whoa… I am dizzy!'); }
  });
  el.addEventListener('dblclick', () => { body.classList.add('spin'); burst(10); dripSay('Ta-da!', 1500); });

  /* ---- reactions to what happens in the app ---- */
  let prev = cur;
  setInterval(() => {
    if (cur !== prev) {
      if (['curious', 'worried', 'alarmed', 'panic'].includes(prev) && cur === 'idle') burst(18, true);
      if (prev === 'sleep' && cur !== 'sleep') dripSay('I am awake!', 1800);
      prev = cur;
    }
  }, 500);
})();
