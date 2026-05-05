/* catalog.js — shared utilities for catalog pages.
 * Loaded before each page's inline <script>. */

window.CatalogUtils = {
  /** HTML-escape a string */
  esc: function (s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  },

  /** Slugify a string for use as an HTML id */
  slug: function (s) {
    return s.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  },

  /** Render a tag pill. Accepts a plain string or { label, cls } object. */
  tagHtml: function (t) {
    var e = CatalogUtils.esc;
    if (typeof t === 'string') return '<span class="catalog-tag">' + e(t) + '</span>';
    return '<span class="catalog-tag ' + (t.cls || '') + '">' + e(t.label) + '</span>';
  },

  /** Group an array of items by a key, preserving first-appearance order. */
  groupBy: function (items, key) {
    var groups = {};
    var order = [];
    for (var i = 0; i < items.length; i++) {
      var val = items[i][key];
      if (!(val in groups)) {
        groups[val] = [];
        order.push(val);
      }
      groups[val].push(items[i]);
    }
    return { groups: groups, order: order };
  },

  /** Wire up a .back-to-top button (show after scrolling 400px, click to scroll top). */
  initBackToTop: function () {
    var btn = document.getElementById('back-to-top');
    if (!btn) return;
    var threshold = 400;
    window.addEventListener('scroll', function () {
      btn.classList.toggle('visible', window.scrollY > threshold);
    }, { passive: true });
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
};
