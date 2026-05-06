/* catalog.js — shared utilities for catalog pages.
 * Loaded before each page's app script. */

window.CatalogUtils = {
  /** HTML-escape a string (DOM-based, safe) */
  esc: function (s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
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
  },

  /** Show .catalog-nav and .catalog-stats only when #catalog is near the viewport.
   *  Uses IntersectionObserver with a rootMargin to reveal slightly before scroll reaches it. */
  initCatalogReveal: function () {
    var catalog = document.getElementById('catalog');
    if (!catalog) return;
    var nav = document.querySelector('.catalog-nav');
    var stats = document.querySelector('.catalog-stats');
    if (!nav && !stats) return;

    function show() {
      if (nav) nav.classList.add('visible');
      if (stats) stats.classList.add('visible');
    }
    function hide() {
      if (nav) nav.classList.remove('visible');
      if (stats) stats.classList.remove('visible');
    }

    if (!('IntersectionObserver' in window)) { show(); return; }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) show(); else hide();
      });
    }, { rootMargin: '200px 0px 0px 0px' });
    observer.observe(catalog);
  },

  /** Highlight search query matches in text. Returns escaped HTML. */
  highlightText: function (text, query) {
    var escaped = CatalogUtils.esc(text);
    if (!query) return escaped;
    var qEsc = CatalogUtils.esc(query);
    var lower = escaped.toLowerCase();
    var qLower = qEsc.toLowerCase();
    var result = '';
    var lastIdx = 0;
    var idx = lower.indexOf(qLower);
    while (idx !== -1) {
      result += escaped.slice(lastIdx, idx);
      result += '<mark class="search-hl">' + escaped.slice(idx, idx + qEsc.length) + '</mark>';
      lastIdx = idx + qEsc.length;
      idx = lower.indexOf(qLower, lastIdx);
    }
    result += escaped.slice(lastIdx);
    return result;
  },

  /** Focus trap for modal drawers. Returns control object { enable, disable }. */
  createFocusTrap: function () {
    var handler = null;
    var preFocus = null;

    return {
      enable: function (container) {
        if (handler) {
          container.removeEventListener('keydown', handler);
        } else {
          preFocus = document.activeElement;
        }
        handler = function (e) {
          if (e.key !== 'Tab') return;
          var focusable = container.querySelectorAll(
            'button:not([disabled]), [href], input:not([tabindex="-1"]), select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          if (!focusable.length) return;
          var first = focusable[0];
          var last = focusable[focusable.length - 1];
          if (e.shiftKey) {
            if (document.activeElement === first) { e.preventDefault(); last.focus(); }
          } else {
            if (document.activeElement === last) { e.preventDefault(); first.focus(); }
          }
        };
        container.addEventListener('keydown', handler);
      },
      disable: function (container) {
        if (handler) {
          container.removeEventListener('keydown', handler);
          handler = null;
        }
        if (preFocus) {
          preFocus.focus();
          preFocus = null;
        }
      }
    };
  },

  /** Event listener tracker for clean SPA teardown. Returns { on, teardown }. */
  createListenerTracker: function () {
    var listeners = [];
    return {
      on: function (el, event, fn, opts) {
        if (!el) return;
        el.addEventListener(event, fn, opts);
        listeners.push({ el: el, event: event, fn: fn, opts: opts });
      },
      teardown: function () {
        listeners.forEach(function (l) {
          l.el.removeEventListener(l.event, l.fn, l.opts);
        });
        listeners = [];
      }
    };
  },

  /**
   * Generic grouped catalog renderer.
   * Config: { data, groupKey, containerId, navId, statsId, renderCard, entityName }
   * Returns { init, teardown } lifecycle methods.
   */
  createGroupedCatalog: function (config) {
    var U = CatalogUtils;
    var grouped = U.groupBy(config.data, config.groupKey);
    var groups = grouped.groups;
    var order = grouped.order;
    var activeFilter = null;
    var entityName = config.entityName || 'item';

    function renderNav() {
      var navEl = document.getElementById(config.navId);
      navEl.innerHTML = order.map(function (v) {
        var cls = activeFilter === v ? ' class="active"' : '';
        return '<button data-filter="' + U.esc(v) + '"' + cls + '>' + U.esc(v) + '</button>';
      }).join('');

      navEl.querySelectorAll('button').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var val = btn.getAttribute('data-filter');
          activeFilter = activeFilter === val ? null : val;
          renderNav();
          renderCatalog();
        });
      });
    }

    function renderCatalog() {
      var visibleGroups = activeFilter ? [activeFilter] : order;
      var html = visibleGroups.map(function (group) {
        var items = groups[group];
        var cards = items.map(config.renderCard).join('');
        var countLabel = items.length === 1 ? entityName : (config.entityPlural || entityName + 's');
        return (
          '<section class="catalog-section" id="' + U.slug(group) + '">' +
            '<div class="catalog-section-head">' +
              '<span class="catalog-section-name">' + U.esc(group) + '</span>' +
              '<span class="catalog-section-count">' + items.length + ' ' + countLabel + '</span>' +
            '</div>' +
            '<div class="catalog-grid">' + cards + '</div>' +
          '</section>'
        );
      }).join('');
      document.getElementById(config.containerId).innerHTML = html;
    }

    return {
      init: function () {
        activeFilter = null;
        var statsEl = document.getElementById(config.statsId);
        if (statsEl) {
          var totalLabel = config.entityPlural || entityName + 's';
          var groupLabel = config.groupLabel || config.groupKey + 's';
          statsEl.innerHTML =
            '<span><span class="stat-value">' + config.data.length + '</span><span class="stat-label">' + totalLabel + '</span></span>' +
            '<span><span class="stat-value">' + order.length + '</span><span class="stat-label">' + groupLabel + '</span></span>';
        }
        renderNav();
        renderCatalog();
        U.initBackToTop();
        U.initCatalogReveal();
      },
      teardown: function () {}
    };
  }
};
