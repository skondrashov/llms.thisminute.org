/* context/app.js — statelessness token demo.
 * Exposes window.__page for SPA router. */
(function () {
'use strict';

var T = [
  {t:'user',r:1},{t:'What'},{t:'is'},{t:'the'},{t:'capital'},{t:'of'},{t:'France'},{t:'?'},
  {t:'assistant',r:2},{t:'The'},{t:'capital'},{t:'of'},{t:'France'},{t:'is'},{t:'Paris'},{t:'.'},
  {t:'user',r:1},{t:'And'},{t:'Germany'},{t:'?'},
  {t:'assistant',r:2},{t:'The'},{t:'capital'},{t:'of'},{t:'Germany'},{t:'is'},{t:'Berlin'},{t:'.'}
];
var START = 9;
var EV = [
  {n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},
  {n:5},
  {n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1},{n:1, g:1}
];
var vis, ei, busy, playing;

function render(newCount, isGen) {
  var h = '';
  for (var i = 0; i < vis; i++) {
    if (T[i].r && i > 0) h += '<div class="brk"></div>';
    var c = 'tk';
    if (T[i].r === 1) c += ' ru';
    else if (T[i].r === 2) c += ' ra';
    if (newCount && i >= vis - newCount) c += isGen ? ' lt' : ' bt';
    h += '<span class="' + c + '">' + T[i].t + '</span>';
  }
  document.getElementById('tokens').innerHTML = h;
}

function status() {
  var el = document.getElementById('status');
  if (ei === 0) el.textContent = vis + ' tokens in context';
  else if (ei >= EV.length) el.textContent = 'complete — ' + T.length + ' tokens';
  else if (EV[ei - 1].g) el.innerHTML = 'reads ' + (vis - 1) + ' tokens → <strong>' + T[vis - 1].t + '</strong>';
  else el.textContent = vis + ' tokens in context';
  document.getElementById('sbtn').disabled = ei >= EV.length;
}

function sleep(ms) { return new Promise(function(r) { setTimeout(r, ms); }); }

async function doStep() {
  if (ei >= EV.length || busy) return;
  busy = true;
  var ev = EV[ei];
  if (ev.g) {
    var area = document.getElementById('area');
    var tks = document.querySelectorAll('#tokens .tk');
    area.classList.add('reading');
    tks.forEach(function(t) { t.classList.add('fl'); });
    await sleep(280);
    tks.forEach(function(t) { t.classList.remove('fl'); });
    area.classList.remove('reading');
    await sleep(80);
  }
  vis += ev.n; ei++;
  render(ev.n, !!ev.g);
  status();
  busy = false;
}

function doReset() {
  playing = false;
  document.getElementById('pbtn').textContent = 'Play';
  vis = START; ei = 0;
  render(0, false); status();
}

function doPlay() {
  if (playing) {
    playing = false;
    document.getElementById('pbtn').textContent = 'Play';
    return;
  }
  playing = true;
  document.getElementById('pbtn').textContent = 'Pause';
  (async function go() {
    if (!playing || ei >= EV.length) {
      playing = false;
      document.getElementById('pbtn').textContent = 'Play';
      return;
    }
    await doStep();
    var delay = EV[ei - 1].g ? 600 : 1000;
    await sleep(delay);
    go();
  })();
}

// Expose for button onclick attributes in HTML
window.doStep = doStep;
window.doReset = doReset;
window.doPlay = doPlay;

function init() {
  vis = START; ei = 0; busy = false; playing = false;
  render(0, false);
  status();
}

window.__page = { init: init, teardown: function() { playing = false; } };
init();

})();
