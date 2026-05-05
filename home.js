/* home.js — word-hover animation + harness box click handler for the home page.
 * Exposes window.__page = { init, teardown } for the SPA router. */
(function () {
  'use strict';

  var h1, picked, original = 'LLMs!';
  var enterFn, leaveFn, boxClickFn, box;

  var words = [
    'largelanguagemodels',
    'lavalamps',
    'llamas',
    'lululemons',
    'linoleums',
    'slaloms',
    'clingfilms',
    'fulfillments',
    'flimflams',
    'globalisms',
    'legalisms',
    'liberalisms',
    'pluralisms',
    'localisms',
    'loyalisms',
    'colonialisms',
    'clericalisms',
    'literalisms',
    'parallelisms',
    'intellectualisms',
    'multiculturalisms',
    'neoliberalisms',
    'unilateralisms',
    'ultranationalisms',
    'flagellums',
    'flabellums',
    'labellums',
    'allelomorphs',
    'hyaloplasms',
    'hyaloplasmata',
    'nucleoplasms',
    'nucleoplasmata',
    'polyacrylamides',
    'sulfanilamides',
    'platyhelminths',
    'platyhelminthes',
    'electroencephalograms',
    'electroencephalogrammata',
    'electroluminescents',
    'paleoclimatologies',
    'malcolms',
    'wilhelms',
    'malayalams',
    'parallelograms',
    'parallelogrammata',
    'allhallowmases'
  ];

  function formatLLMs(word) {
    var w = word.toLowerCase();
    var firstL = w.indexOf('l');
    var lastM = w.lastIndexOf('m');
    if (firstL < 0 || lastM < 0) return word;
    var closestL = -1;
    for (var i = lastM - 1; i >= 0; i--) {
      if (w.charAt(i) === 'l') { closestL = i; break; }
    }
    var chars = w.split('');
    chars[firstL] = 'L';
    if (closestL >= 0) chars[closestL] = 'L';
    chars[lastM] = 'M';
    return chars.join('') + '!';
  }

  function init() {
    h1 = document.querySelector('.hero h1');
    if (h1) {
      picked = formatLLMs(words[Math.floor(Math.random() * words.length)]);
      enterFn = function () { h1.textContent = picked; };
      leaveFn = function () { h1.textContent = original; };
      h1.addEventListener('mouseenter', enterFn);
      h1.addEventListener('mouseleave', leaveFn);
    }

    box = document.querySelector('.anatomy');
    if (box) {
      boxClickFn = function (e) {
        if (e.target.closest('.anatomy__node')) return;
        // Use SPA navigation if router is available
        var link = document.querySelector('.anatomy__harness-label');
        if (link) link.click();
      };
      box.addEventListener('click', boxClickFn);
    }
  }

  function teardown() {
    if (h1 && enterFn) {
      h1.removeEventListener('mouseenter', enterFn);
      h1.removeEventListener('mouseleave', leaveFn);
    }
    if (box && boxClickFn) {
      box.removeEventListener('click', boxClickFn);
    }
  }

  window.__page = { init: init, teardown: teardown };
  init();
})();
