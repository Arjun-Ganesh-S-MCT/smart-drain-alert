(function () {
  'use strict';
  if (window.flowbeacon || !/Android/i.test(navigator.userAgent || '')) return;
  var slow = !(window.matchMedia && matchMedia('(prefers-reduced-motion:reduce)').matches);
  var k = slow ? 1 : 0.35;
  var css = document.createElement('style');
  css.textContent =
    '#fbIntro{position:fixed;top:0;right:0;bottom:0;left:0;z-index:200;background:#e0d9d3;color:#6b625b;overflow:hidden;-webkit-user-select:none;user-select:none;transition:opacity .9s ease}' +
    '#fbIntro.out{opacity:0}' +
    '#fbIntro .sc{position:absolute;top:0;right:0;bottom:70px;left:0;display:flex;flex-direction:column;align-items:center;justify-content:center;opacity:0}' +
    '#fbIntro .sc>*{margin:9px 0}' +
    '#fbA{animation:fbin 1.3s ' + 0.3 * k + 's ease-out forwards,fbout .9s ' + 4.4 * k + 's ease-in forwards}' +
    '#fbB{animation:fbin 1.2s ' + 5.4 * k + 's ease-out forwards}' +
    '#fbA img{height:130px;max-width:70vw;animation:fbpop 1.6s ' + 0.3 * k + 's ease-out both}' +
    '#fbA p{font-size:.8rem;letter-spacing:.55em;text-indent:.55em;opacity:0;animation:fbin 1.1s ' + 2.1 * k + 's ease-out forwards}' +
    '#fbB img{height:128px;animation:fbhop 1.5s ' + 5.4 * k + 's ease-out both}' +
    '#fbB h1{font-size:1.55rem;letter-spacing:.05em;text-indent:.05em;white-space:nowrap;margin-bottom:0}#fbB h1 span{color:#fc8068}' +
    '#fbB p{font-size:.68rem;letter-spacing:.06em;color:#948a82;opacity:0;animation:fbin 1.1s ' + 6.6 * k + 's ease-out forwards}' +
    '#fbIntro .bar{position:absolute;left:44px;right:44px;bottom:calc(34px + env(safe-area-inset-bottom,0px));height:12px;border-radius:99px;box-shadow:inset 3px 3px 6px #bdb3ac,inset -3px -3px 6px #f4f0ea}' +
    '#fbIntro .bar i{display:block;height:100%;width:0;border-radius:99px;background:#fc8068;animation:fbfill ' + 8.2 * k + 's .2s ease-in-out forwards}' +
    '@keyframes fbin{from{opacity:0}to{opacity:1}}@keyframes fbout{to{opacity:0}}' +
    '@keyframes fbpop{from{transform:scale(.88)}to{transform:scale(1)}}' +
    '@keyframes fbhop{0%{transform:translateY(46px) scale(.9)}65%{transform:translateY(-12px)}100%{transform:none}}' +
    '@keyframes fbfill{to{width:100%}}';
  document.head.appendChild(css);
  var el = document.createElement('div');
  el.id = 'fbIntro';
  el.innerHTML = '<div class="sc" id="fbA"><img src="img/techminds.png" alt="TechMinds"><p>PRESENTS</p></div>' +
    '<div class="sc" id="fbB"><img src="img/drip-full.png" alt="Drip"><h1>Flow<span>Beacon</span></h1><p>drain blockage prediction</p></div>' +
    '<div class="bar"><i></i></div>';
  document.body.insertBefore(el, document.body.firstChild);
  var done = false;
  function end() {
    if (done) return; done = true;
    el.classList.add('out');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); if (css.parentNode) css.parentNode.removeChild(css); }, 1000);
  }
  el.addEventListener('click', end);
  setTimeout(end, (8.8 * k + 0.2) * 1000);
})();
