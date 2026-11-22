(function () {
  const DC = window.DripCore;
  const NODES = window.__nodes;
  const d = { voice: !!S.dripVoice };
  const quiet = () => !!(S.quiet && S.quiet.on && window.soundOff && soundOff('click'));

  function worstNode() {
    let w = null;
    NODES.allNodes().forEach(x => { if (x.rx && (!w || x.lvl > w.lvl)) w = x; });
    return w;
  }
  window.dripLine = (state, fallback) => DC.line(state, S.lang, worstNode() && worstNode().name) || fallback;

  const baseSay = dripSay;
  dripSay = function (t, ms) {
    baseSay(t, ms);
    if (d.voice && !quiet() && 'speechSynthesis' in window) {
      const lang = S.lang === 'ta' ? 'ta' : 'en';
      if (speechSynthesis.getVoices().some(v => v.lang.toLowerCase().startsWith(lang))) {
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(String(tr(t)));
        u.rate = 1; u.lang = lang === 'ta' ? 'ta-IN' : 'en-IN';
        speechSynthesis.speak(u);
      }
    }
  };

  function ctx() {
    const nodes = NODES.allNodes();
    return {
      lang: S.lang,
      worst: nodes.reduce((m, x) => Math.max(m, x.lvl), 0),
      nodes: nodes.map(x => ({ name: x.name, rx: x.rx, text: ICO[x.lvl] + ' ' + tr(ST[x.lvl].n) })),
      cause: $('cause').textContent, evid: $('evid').textContent, pred: $('pred').textContent
    };
  }
  window.dripClick = () => dripSay(DC.reply('status', ctx()).text, 7000);

  const escapeHtml = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function act(a) {
    if (!a) return;
    if (a === 'baseline') $('bCal').click();
    else if (a === 'demo') $('bDemo').click();
    else if (a === 'mute') { S.mute = true; $('snd').checked = false; save(); }
    else if (a === 'unmute') { S.mute = false; $('snd').checked = true; save(); }
    else if (a === 'ack') $('bAck').click();
    else if (a.startsWith('accent:')) { const b = document.querySelector('.swatch[data-a=' + a.slice(7) + ']'); if (b) b.click(); }
    else if (a.startsWith('mode:')) { $('aMode').value = a.slice(5); $('aMode').onchange({ target: $('aMode') }); }
    else if (a.startsWith('lang:')) { $('aLang').value = a.slice(5); $('aLang').onchange({ target: $('aLang') }); }
  }
  function ask(text) {
    if (!text.trim()) return;
    const log = $('dChat');
    log.insertAdjacentHTML('beforeend', '<div class="me">' + escapeHtml(text) + '</div>');
    const r = DC.reply(text, ctx());
    log.insertAdjacentHTML('beforeend', '<div class="dr">' + escapeHtml(r.text) + '</div>');
    if (log.scrollTo) log.scrollTo(0, log.scrollHeight);
    dripSay(r.text, 7000);
    act(r.action);
  }

  const style = document.createElement('style');
  style.textContent = '.chat{height:190px;overflow:auto;padding:10px;font-size:.8rem;line-height:1.5;display:grid;gap:8px;align-content:start}.me{justify-self:end;background:var(--ac);color:var(--on);padding:6px 12px;border-radius:14px}.dr{justify-self:start;padding:6px 12px;border-radius:14px;box-shadow:3px 3px 6px var(--sd),-3px -3px 6px var(--sl)}.chip{padding:6px 12px;font-size:.75rem}';
  document.head.appendChild(style);

  document.getElementById('appr').insertAdjacentHTML('beforebegin',
    '<section class="raised card" id="meet" style="margin-bottom:24px"><h2>Ask Drip</h2><div class="chat inset" id="dChat"></div>' +
    '<div class="row fld"><input type="text" id="dIn" placeholder="Ask about the drains, or type help" style="flex:1;min-width:160px"><button id="dSend">Send</button></div>' +
    '<div class="row fld" id="dChips"></div>' +
    '<div class="row" style="justify-content:space-between;margin-top:14px"><span>Speak alerts aloud</span><label class="sw"><input type="checkbox" id="dVoice" aria-label="Speak alerts aloud"><i></i></label></div></section>');
  $('dChat').insertAdjacentHTML('beforeend', '<div class="dr">I am Drip. Ask me for the status, the cause of an alert, or type help.</div>');
  $('dChips').innerHTML = ['Status', 'Why', 'Tip', 'Help'].map(c => '<button class="chip" data-q="' + c.toLowerCase() + '">' + c + '</button>').join('');
  $('dChips').onclick = e => { const b = e.target.closest('.chip'); if (b) ask(b.dataset.q); };
  $('dSend').onclick = () => { ask($('dIn').value); $('dIn').value = ''; };
  $('dIn').onkeydown = e => { if (e.key === 'Enter') $('dSend').click(); };
  $('dVoice').checked = d.voice;
  $('dVoice').onchange = e => { d.voice = e.target.checked; S.dripVoice = d.voice; save(); if (d.voice) dripSay('Alerts will be spoken aloud.'); };
})();
