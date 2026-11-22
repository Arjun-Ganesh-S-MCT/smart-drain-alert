(function (root) {
  const D = {};

  D.LINES = {
    curious: ['Flow is lower than normal at {d}. Keep watching.'],
    worried: ['Blockage warning at {d}: flow is falling while the level rises. Inspect the drain.'],
    alarmed: ['Overflow risk at {d}. Check the drain now.'],
    panic: ['Overflow detected at {d}. Act now.'],
    sleep: ['No data. Waiting for the board.'],
    think: ['Calibrating. Keep the flow steady.'],
    dizzy: ['A sensor reading looks wrong. Check the wiring.']
  };
  D.TA = {
    curious: ['{d}: ஓட்டம் இயல்பை விட குறைவு. தொடர்ந்து கவனிக்கவும்.'],
    worried: ['{d}: அடைப்பு எச்சரிக்கை. ஓட்டம் குறைந்து நீர்மட்டம் உயர்கிறது. வடிகாலைப் பரிசோதிக்கவும்.'],
    alarmed: ['{d}: வழிதல் அபாயம். உடனே வடிகாலைச் சரிபார்க்கவும்.'],
    panic: ['{d}: வழிதல் கண்டறியப்பட்டது. உடனே நடவடிக்கை எடுக்கவும்.'],
    sleep: ['தரவு இல்லை. போர்டுக்காக காத்திருக்கிறேன்.'],
    think: ['அளவுத்திருத்தம் நடக்கிறது. ஓட்டத்தை சீராக வைக்கவும்.'],
    dizzy: ['ஒரு உணரி அளவீடு தவறாகத் தெரிகிறது. வயரிங்கைச் சரிபார்க்கவும்.']
  };

  D.line = (state, lang, drain, rng) => {
    const pool = (lang === 'ta' && D.TA[state]) || D.LINES[state];
    if (!pool) return '';
    const r = rng || Math.random;
    return pool[Math.floor(r() * pool.length)].replace('{d}', drain || (lang === 'ta' ? 'வடிகால்' : 'the drain'));
  };

  D.TIPS = [
    'Plastic and silt are the top causes of clogged drains.',
    'A drain can lose half its flow before anyone notices.',
    'Flow falling while the level rises is the classic blockage sign.',
    'The rain plate only knows wet or dry. It cannot measure how hard it rains.',
    'Turbidity is cloudiness. More particles in the water means a higher reading.',
    'Clearing drains before the monsoon prevents most street flooding.'
  ];
  D.HELP = 'Ask me: status, why, when will it overflow, or what turbidity, flow, calibration, SMS or Wi-Fi mean. I can also set the baseline, start the demo, mute, acknowledge an alarm, change the theme colour or the language.';
  D.HELP_TA = 'கேளுங்கள்: நிலை, ஏன், எப்போது வழியும். அடிப்படை அளவை அமைக்கவும், டெமோ தொடங்கவும், ஒலியை நிறுத்தவும், அலாரத்தை ஏற்கவும், தீம் அல்லது மொழியை மாற்றவும் என்னால் முடியும்.';

  const COLOURS = ['coral', 'blue', 'green', 'purple', 'red', 'yellow', 'black'];

  D.reply = (text, c, rng) => {
    const t = String(text).toLowerCase().trim();
    const ta = c.lang === 'ta';
    const live = (c.nodes || []).filter(n => n.rx);
    const done = (txt, action) => ({ text: txt, action: action || null });
    if (!t) return done(ta ? 'ஏதாவது கேளுங்கள்.' : 'Ask me something. Try: help');

    if (/\bbaseline\b/.test(t)) return done('Setting the baseline. Keep the flow normal for a few seconds.', 'baseline');
    if (/\bdemo\b/.test(t)) return done('Starting or stopping the demo.', 'demo');
    if (/\b(unmute|sound on)\b/.test(t)) return done('Sound is on.', 'unmute');
    if (/\b(mute|silence)\b/.test(t) && !/alarm/.test(t)) return done('Sound is off.', 'mute');
    if (/\b(acknowledge|ack|silence alarm|stop (the )?alarm)\b/.test(t)) return done('Alarm acknowledged.', 'ack');
    const col = COLOURS.find(x => new RegExp('\\b' + x + '\\b').test(t));
    if (col && /(theme|colou?r|make it|switch|change)/.test(t)) return done('Switching to the ' + col + ' theme.', 'accent:' + col);
    if (/\bdark\b/.test(t) && /(mode|theme|switch|change)/.test(t)) return done('Dark mode.', 'mode:dark');
    if (/\blight\b/.test(t) && /(mode|theme|switch|change)/.test(t)) return done('Light mode.', 'mode:light');
    if (/tamil|தமிழ்/.test(t)) return done('தமிழுக்கு மாறுகிறேன்.', 'lang:ta');
    if (/\benglish\b/.test(t)) return done('Switching to English.', 'lang:en');

    if (/how are you|are you ok|systems/.test(t)) return done(c.worst >= 2 ? 'Something needs attention. Ask me for the status.' : 'All systems are running. Nothing needs attention.');
    if (/\b(status|drains?|how is|how are the|condition)\b|நிலை/.test(t) && !/what is|what are/.test(t)) {
      if (!live.length) return done(ta ? 'இன்னும் அளவீடுகள் எதுவும் வரவில்லை. போர்டை இணைக்கவும் அல்லது டெமோவை முயற்சிக்கவும்.' : 'No readings yet. Connect the board or try the demo.');
      return done(live.map(n => n.name + ': ' + n.text).join('. ') + '.');
    }
    if (/\b(why|cause|reason)\b/.test(t)) {
      if (c.cause && c.cause !== 'No fault indicated' && !/குறைபாடு/.test(c.cause)) return done(c.cause + (c.evid ? '. Evidence: ' + c.evid : '') + '.');
      return done('Nothing is wrong right now.');
    }
    if (/(when|will).*(overflow|flood|full)|predict|\beta\b/.test(t)) return done(c.pred || 'No overflow is predicted right now.');
    if (/turbidity|cloudy/.test(t)) return done('Turbidity is how cloudy the water is. More silt or mud gives a higher reading, which can support a blockage estimate.');
    if (/ultrasonic|distance|level/.test(t)) return done('The ultrasonic sensor measures the distance to the water surface. As the water rises, the distance gets smaller.');
    if (/\bflow\b/.test(t)) return done('The flow sensor counts pulses. Flow falling while the water level rises is the classic blockage sign.');
    if (/calibrat/.test(t)) return done('Calibration teaches the app what normal looks like. Use the wizard under Calibration, then tune the dials.');
    if (/\b(sms|text message)\b/.test(t)) return done('SMS needs a GSM module on the board. Add your number under SMS alerts and press Send test SMS.');
    if (/wi-?fi/.test(t)) return done('Connect the board with USB, enter the Wi-Fi name and password under Connection, then press Send to board.');
    if (/\brain\b/.test(t)) return done('The rain plate only knows wet or dry. It cannot measure how hard it rains.');
    if (/\btip\b|\bfact\b|did you know/.test(t)) return done(D.TIPS[Math.floor((rng || Math.random)() * D.TIPS.length)]);
    if (/who are you|your name|about you|what are you/.test(t)) return done('I am Drip, the FlowBeacon assistant. I watch your drains and tell you what changes.');
    if (/thank|thanks|nandri|நன்றி/.test(t)) return done(ta ? 'சரி.' : 'You are welcome.');
    if (/(^|\b)(hi|hello|hey|vanakkam)\b|வணக்கம்/.test(t)) return done(ta ? 'வணக்கம். நிலை அறிய "நிலை" என்று கேளுங்கள்.' : 'Hello. Ask me for the status any time.');
    if (/help|what can you do|commands/.test(t)) return done(ta ? D.HELP_TA : D.HELP);
    return done(ta ? 'அது எனக்குப் புரியவில்லை. "help" என்று கேளுங்கள்.' : 'I did not understand that. Try: status, why, tip or help.');
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = D;
  else root.DripCore = D;
})(typeof window !== 'undefined' ? window : this);
