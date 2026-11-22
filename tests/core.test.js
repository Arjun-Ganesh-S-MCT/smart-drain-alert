const test = require('node:test');
const assert = require('node:assert');
const Core = require('../src/core.js');

const base = { flow: 4, dist: 12, turb: 800, sf: 0.2, sd: 0.2, st: 20 };
const cfg = Core.DEF;
const ok = { bad: false, i: [] };
const reading = (o = {}) => Object.assign({ flow: 4, dist: 12, turb: 800, rain: 0 }, o);

test('normal readings give level 0', () => {
  const r = Core.evaluate(reading(), ok, base, cfg);
  assert.strictEqual(r.lvl, 0);
  assert.strictEqual(r.conf, 0);
});

test('falling flow with rising level is a blockage warning', () => {
  const r = Core.evaluate(reading({ flow: 1.6, dist: 10.5 }), ok, base, cfg);
  assert.strictEqual(r.lvl, 2);
  assert.match(r.cause, /Likely blockage/);
});

test('blockage plus rain names both causes', () => {
  const r = Core.evaluate(reading({ flow: 1.6, dist: 10.5, rain: 1 }), ok, base, cfg);
  assert.match(r.cause, /rainfall/);
});

test('rain alone with a rising level blames rainfall', () => {
  const r = Core.evaluate(reading({ dist: 10.5, rain: 1 }), ok, base, cfg);
  assert.match(r.cause, /Rainfall/);
});

test('water at the risk distance is level 3, at the overflow distance level 4', () => {
  assert.strictEqual(Core.evaluate(reading({ dist: 3.5 }), ok, base, cfg).lvl, 3);
  assert.strictEqual(Core.evaluate(reading({ dist: 1.5 }), ok, base, cfg).lvl, 4);
});

test('an out of range ultrasonic reading cannot raise an overflow', () => {
  const d = reading({ dist: 0 });
  const h = Core.health(d, [], base);
  assert.strictEqual(h.bad, true);
  assert.ok(Core.evaluate(d, h, base, cfg).lvl < 3);
});

test('frozen and stuck values are reported', () => {
  const hist = Array.from({ length: 20 }, (_, i) => ({ t: i * 1000, f: 4, l: 12 }));
  const h = Core.health(reading(), hist, base);
  assert.ok(h.i.some(x => /not changing/.test(x)));
  assert.ok(h.i.some(x => /frozen/.test(x)));
});

test('rising level gives an overflow estimate', () => {
  const hist = Array.from({ length: 20 }, (_, i) => ({ t: i * 1000, f: 3, l: 12 - i * 0.2 }));
  const eta = Core.predictEta(hist, 2);
  assert.ok(eta > 30 && eta < 60);
});

test('a steady or falling level gives no estimate', () => {
  const hist = Array.from({ length: 20 }, (_, i) => ({ t: i * 1000, f: 3, l: 12 + i * 0.1 }));
  assert.strictEqual(Core.predictEta(hist, 2), null);
});

test('mobile numbers are normalised', () => {
  assert.strictEqual(Core.normNum('98765 43210'), '+919876543210');
  assert.strictEqual(Core.normNum('+91 98765-43210'), '+919876543210');
  assert.strictEqual(Core.normNum('09876543210'), '+919876543210');
  assert.strictEqual(Core.normNum('12345'), null);
});

test('the learned model separates normal from blocked', () => {
  const rows = [];
  for (let i = 0; i < 30; i++) {
    rows.push({ label: 'normal', x: Core.features(reading({ flow: 4 + (i % 3) * 0.05, dist: 12 }), base) });
    rows.push({ label: 'blocked', x: Core.features(reading({ flow: 1.8 + (i % 3) * 0.05, dist: 10.6 }), base) });
  }
  const m = Core.trainNB(rows);
  assert.strictEqual(Core.predictNB(m, Core.features(reading(), base)).label, 'normal');
  assert.strictEqual(Core.predictNB(m, Core.features(reading({ flow: 1.7, dist: 10.5 }), base)).label, 'blocked');
  assert.ok(Core.accuracy(m, rows) > 0.95);
  assert.match(Core.header(m, base), /ML_LABELS\[\]=\{"normal","blocked"\}/);
});

test('recorded CSV files are parsed', () => {
  const rows = Core.parseCSV('time,label,flow,dist,turb,rain,condition\n2026-01-01T00:00:00Z,normal,4.1,12.2,850,0,Normal\n');
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].label, 'normal');
  assert.strictEqual(rows[0].dist, 12.2);
});

test('a faulty ultrasonic reading is not treated as a rising water level', () => {
  const d = reading({ flow: 1.6, dist: 0 });
  const h = Core.health(d, [], base);
  const r = Core.evaluate(d, h, base, cfg);
  assert.strictEqual(r.rise, 0);
  assert.ok(r.lvl < 2);
  assert.ok(!r.ev.some(x => /^Level \+/.test(x)));
});

test('update.js VERSION matches package.json', () => {
  const v = /const VERSION = '([^']+)'/.exec(require('fs').readFileSync(require('path').join(__dirname, '../src/update.js'), 'utf8'))[1];
  assert.strictEqual(v, require('../package.json').version);
});
