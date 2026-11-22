const test = require('node:test');
const assert = require('node:assert');
const D = require('../src/drip-core.js');

const ctx = (o = {}) => Object.assign({ lang: 'en', worst: 0, nodes: [], cause: '', evid: '', pred: '' }, o);

test('alert lines name the affected drain', () => {
  assert.match(D.line('panic', 'en', 'Drain 2', () => 0), /Overflow detected at Drain 2/);
  assert.match(D.line('alarmed', 'en', null, () => 0), /at the drain/);
  assert.strictEqual(D.line('unknown', 'en', 'x'), '');
});

test('Tamil lines are used when the language is Tamil', () => {
  assert.match(D.line('worried', 'ta', 'Drain 1', () => 0), /Drain 1/);
  assert.match(D.line('worried', 'ta', 'Drain 1', () => 0), /[஀-௿]/);
});

test('Drip reports drain status from live data', () => {
  const r = D.reply('how is the drain status', ctx({ nodes: [{ name: 'Drain 1', rx: 1, text: '✓ Normal' }, { name: 'Drain 2', rx: 1, text: '■ Overflow risk' }] }));
  assert.match(r.text, /Drain 1: ✓ Normal/);
  assert.match(r.text, /Drain 2: ■ Overflow risk/);
  assert.match(D.reply('status', ctx()).text, /No readings yet/);
});

test('Drip explains the cause only when there is one', () => {
  assert.match(D.reply('why', ctx({ cause: 'Likely blockage: flow falling', evid: 'Flow -43%' })).text, /Likely blockage/);
  assert.match(D.reply('why', ctx({ cause: 'No fault indicated' })).text, /Nothing is wrong/);
});

test('chat commands return app actions', () => {
  assert.strictEqual(D.reply('set the baseline', ctx()).action, 'baseline');
  assert.strictEqual(D.reply('start demo', ctx()).action, 'demo');
  assert.strictEqual(D.reply('mute', ctx()).action, 'mute');
  assert.strictEqual(D.reply('unmute', ctx()).action, 'unmute');
  assert.strictEqual(D.reply('change the theme to purple', ctx()).action, 'accent:purple');
  assert.strictEqual(D.reply('dark mode please', ctx()).action, 'mode:dark');
  assert.strictEqual(D.reply('switch to tamil', ctx()).action, 'lang:ta');
  assert.strictEqual(D.reply('acknowledge the alarm', ctx()).action, 'ack');
});

test('the overflow estimate is passed through', () => {
  assert.match(D.reply('when will it overflow', ctx({ pred: 'Prediction: overflow in about 4 min' })).text, /4 min/);
  assert.match(D.reply('predict', ctx()).text, /No overflow is predicted/);
});

test('unknown questions get a plain fallback', () => {
  assert.match(D.reply('qwertyuiop', ctx()).text, /Try: status/);
});

test('words that only contain "eta" do not trigger the overflow estimate', () => {
  assert.doesNotMatch(D.reply('tell me the details', ctx()).text, /overflow/i);
  assert.match(D.reply('what is the eta', ctx({ pred: 'Prediction: overflow in about 4 min' })).text, /4 min/);
});
