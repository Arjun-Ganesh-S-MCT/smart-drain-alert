(function (root) {
  const Core = {};

  Core.DEF = { dropWarn: 25, dropBlock: 50, rise: 1, risk: 4, over: 2, turb: 30 };

  Core.conf = c => ({ dw: c.dropWarn / 100, db: c.dropBlock / 100, rise: c.rise, risk: c.risk, over: c.over, tb: c.turb / 100 });

  Core.health = (d, hist, base) => {
    const r = hist.slice(-20), i = [];
    const bad = d.dist <= 0 || d.dist > 600;
    if (bad) i.push('Ultrasonic reading out of range, check wiring');
    if (d.turb <= 0 || d.turb >= 4095) i.push('Turbidity reading at its limit');
    if (r.length >= 20) {
      if (r.every(q => q.l === d.dist)) i.push('Ultrasonic value is not changing');
      if (d.flow > 0 && r.every(q => q.f === d.flow)) i.push('Flow value is frozen');
    }
    if (base && d.flow === 0) i.push('Flow is 0: blockage or sensor fault');
    return { i, bad };
  };

  Core.predictEta = (hist, over) => {
    const p = hist.slice(-20);
    if (p.length < 10) return null;
    const n = p.length, t0 = p[0].t;
    let sx = 0, sy = 0, sxy = 0, sxx = 0;
    p.forEach(q => { const x = (q.t - t0) / 1000; sx += x; sy += q.l; sxy += x * q.l; sxx += x * x; });
    const den = n * sxx - sx * sx;
    if (!den) return null;
    const m = (n * sxy - sx * sy) / den, cur = p[n - 1].l;
    if (m > -0.005 || cur <= over) return null;
    return (cur - over) / -m;
  };

  Core.evaluate = (d, h, b, cfg) => {
    const c = Core.conf(cfg);
    let lvl = 0, ev = [], pts = 0, fd = 0, rise = 0, td = 0, z = 0, cause = 'No fault indicated';
    if (b) {
      fd = b.flow > 0 ? 1 - d.flow / b.flow : 0;
      rise = b.dist - d.dist;
      td = b.turb > 0 ? (d.turb - b.turb) / b.turb : 0;
      z = Math.max(Math.abs(d.flow - b.flow) / b.sf, h.bad ? 0 : Math.abs(d.dist - b.dist) / b.sd);
      if (fd > 0.05) ev.push('Flow ' + (-fd * 100).toFixed(0) + '% vs baseline');
      if (rise > 0.2) ev.push('Level +' + rise.toFixed(1) + ' cm');
      if (Math.abs(td) > 0.1) ev.push('Turbidity ' + (td > 0 ? '+' : '') + (td * 100).toFixed(0) + '%');
      if (z > 3) ev.push('Anomaly ' + z.toFixed(1) + ' σ');
    }
    if (d.rain) ev.push('Rain plate wet');
    const blk = fd >= c.dw, rising = rise >= c.rise, dirty = td >= c.tb;
    if (b) {
      if (blk && (rising || dirty)) lvl = 1;
      if (fd >= c.db && rising) lvl = 2;
      if (z > 4 && fd > 0.1 && !lvl) lvl = 1;
    }
    if (!h.bad) {
      if (d.dist <= c.risk) lvl = Math.max(lvl, 3);
      if (d.dist <= c.over) lvl = 4;
    }
    if (blk && d.rain) cause = 'Blockage and rainfall likely both contributing';
    else if (blk) cause = 'Likely blockage: flow falling' + (rising ? ' while level rises' : '');
    else if (d.rain && rising) cause = 'Rainfall likely contributing to rising level';
    else if (lvl >= 3) cause = 'Water level high; cause unclear';
    else if (lvl) cause = 'Unusual pattern against baseline';
    if (blk) pts += fd >= c.db ? 40 : 25;
    if (rising) pts += 25;
    if (dirty) pts += 15;
    if (d.rain && rising) pts += 10;
    if (lvl >= 3) pts += 15;
    if (z > 3) pts += 10;
    return { lvl, ev, cause, conf: lvl ? Math.min(95, pts) : 0, fd, rise };
  };

  Core.normNum = v => {
    let d = String(v).replace(/[\s\-()]/g, '');
    if (/^\d{10}$/.test(d)) d = '+91' + d;
    else if (/^0\d{10}$/.test(d)) d = '+91' + d.slice(1);
    else if (/^91\d{10}$/.test(d)) d = '+' + d;
    return /^\+\d{10,15}$/.test(d) ? d : null;
  };

  Core.features = (d, b) => [
    b.flow > 0 ? 1 - d.flow / b.flow : 0,
    b.dist - d.dist,
    b.turb > 0 ? (d.turb - b.turb) / b.turb : 0,
    d.rain ? 1 : 0
  ];

  Core.trainNB = rows => {
    const labels = [...new Set(rows.map(r => r.label))];
    const floors = [0.05, 0.3, 0.05, 0.15];
    const mean = [], std = [], prior = [];
    labels.forEach(l => {
      const xs = rows.filter(r => r.label === l).map(r => r.x);
      prior.push(xs.length / rows.length);
      const m = [], s = [];
      for (let j = 0; j < 4; j++) {
        const mu = xs.reduce((a, x) => a + x[j], 0) / xs.length;
        const v = xs.reduce((a, x) => a + (x[j] - mu) ** 2, 0) / xs.length;
        m.push(mu);
        s.push(Math.max(Math.sqrt(v), floors[j]));
      }
      mean.push(m);
      std.push(s);
    });
    return { labels, prior, mean, std, n: rows.length };
  };

  Core.predictNB = (m, x) => {
    const lp = m.labels.map((l, i) => {
      let s = Math.log(m.prior[i]);
      for (let j = 0; j < x.length; j++) {
        const sd = m.std[i][j], z = (x[j] - m.mean[i][j]) / sd;
        s += -0.5 * z * z - Math.log(sd);
      }
      return s;
    });
    const mx = Math.max(...lp), ex = lp.map(v => Math.exp(v - mx)), sum = ex.reduce((a, b) => a + b, 0);
    const probs = ex.map(v => v / sum), k = probs.indexOf(Math.max(...probs));
    return { label: m.labels[k], p: probs[k], probs };
  };

  Core.accuracy = (m, rows) => rows.length ? rows.filter(r => Core.predictNB(m, r.x).label === r.label).length / rows.length : 0;

  Core.header = (m, b) => {
    const f = a => a.map(v => Number(v.toFixed(5))).join(',');
    return [
      '#define HAS_MODEL 1',
      'const int ML_N=' + m.labels.length + ';',
      'const char* ML_LABELS[]={' + m.labels.map(l => '"' + l.replace(/[^a-zA-Z0-9 _-]/g, '') + '"').join(',') + '};',
      'const float ML_PRIOR[]={' + f(m.prior) + '};',
      'const float ML_MEAN[][4]={' + m.mean.map(r => '{' + f(r) + '}').join(',') + '};',
      'const float ML_STD[][4]={' + m.std.map(r => '{' + f(r) + '}').join(',') + '};',
      'const float BASE_FLOW=' + b.flow.toFixed(3) + ',BASE_DIST=' + b.dist.toFixed(3) + ',BASE_TURB=' + b.turb.toFixed(1) + ';',
      ''
    ].join('\n');
  };

  Core.parseCSV = text => {
    const L = text.split(/\r?\n/).filter(Boolean);
    if (L.length < 2) return [];
    const h = L[0].split(',').map(x => x.trim().toLowerCase().replace(/"/g, ''));
    const ix = n => h.indexOf(n);
    if (ix('flow') < 0 || ix('dist') < 0 || ix('turb') < 0) return [];
    return L.slice(1).map(l => {
      const c = l.split(',').map(x => x.replace(/"/g, ''));
      return { label: ix('label') >= 0 ? c[ix('label')] : '', flow: +c[ix('flow')], dist: +c[ix('dist')], turb: +c[ix('turb')], rain: +c[ix('rain')] ? 1 : 0 };
    }).filter(r => isFinite(r.flow) && isFinite(r.dist) && isFinite(r.turb));
  };

  Core.baseFrom = rows => {
    const m = k => rows.reduce((s, x) => s + x[k], 0) / rows.length;
    const sd = (k, fl) => { const mu = m(k); return Math.max(Math.sqrt(rows.reduce((s, x) => s + (x[k] - mu) ** 2, 0) / rows.length), fl); };
    return { flow: m('flow'), dist: m('dist'), turb: m('turb'), sf: sd('flow', Math.max(0.05, 0.05 * m('flow'))), sd: sd('dist', 0.2), st: sd('turb', 10) };
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = Core;
  else root.Core = Core;
})(typeof window !== 'undefined' ? window : this);
