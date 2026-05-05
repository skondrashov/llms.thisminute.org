/* router.js — client-side SPA router for llms.thisminute.org
 *
 * Progressive enhancement: pages work standalone; this layer intercepts
 * same-origin navigation and swaps content without a full reload.
 *
 * Shell (persistent): <body>, .forge-theme-toggle (nav), shared CSS/JS.
 * Page content: everything inside <div id="page">.
 *
 * Pages declare their scripts via two attributes on #page:
 *   data-deps="data.js,taxonomy.js"   — loaded once, cached (data scripts)
 *   data-app="app.js"                 — lifecycle script, re-executed each visit
 */
(function () {
  'use strict';
  if (!window.history || !window.history.pushState) return;

  // --- Loading bar ---
  var bar = document.createElement('div');
  bar.className = 'spa-loading-bar';
  document.body.appendChild(bar);

  function showLoading() { bar.classList.add('active'); bar.classList.remove('done'); }
  function hideLoading() {
    bar.classList.remove('active');
    bar.classList.add('done');
    setTimeout(function () { bar.classList.remove('done'); }, 300);
  }

  // --- Page cache (HTML strings) ---
  var htmlCache = {};

  // --- Tracks which dep scripts have been loaded (by resolved URL) ---
  var loadedDeps = {};

  // --- State ---
  var navigating = false;

  // --- Helpers ---

  function updateNav(pathname) {
    var links = document.querySelectorAll('.site-nav a');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href');
      var match = href === '/' ? pathname === '/' : pathname.indexOf(href) === 0;
      if (match) {
        links[i].setAttribute('aria-current', 'page');
      } else {
        links[i].removeAttribute('aria-current');
      }
    }
  }

  function updateFavicon(doc) {
    var newIcon = doc.querySelector('link[rel="icon"]');
    if (newIcon) {
      var existing = document.querySelector('link[rel="icon"]');
      if (existing) {
        existing.href = newIcon.href;
      } else {
        document.head.appendChild(newIcon.cloneNode(true));
      }
    }
  }

  function extractPageStyle(doc) {
    var styles = doc.querySelectorAll('head > style');
    var combined = '';
    for (var i = 0; i < styles.length; i++) {
      combined += styles[i].textContent + '\n';
    }
    return combined;
  }

  function resolveUrl(src, baseUrl) {
    if (src.indexOf('http') === 0 || src.indexOf('//') === 0) return src;
    if (src.charAt(0) === '/') return src;
    var base = baseUrl.replace(/[^/]*$/, '');
    return base + src;
  }

  function parseAttr(el, attr) {
    var val = el.getAttribute(attr);
    if (!val) return [];
    return val.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  }

  // --- Script loading ---

  function injectScript(src, callback) {
    var script = document.createElement('script');
    script.src = src;
    script.setAttribute('data-page-script', 'true');
    script.onload = callback;
    script.onerror = function () {
      console.warn('[router] Failed to load:', src);
      callback();
    };
    document.body.appendChild(script);
  }

  function loadDeps(deps, callback) {
    // Load dependency scripts sequentially; skip if already loaded
    var i = 0;
    function next() {
      if (i >= deps.length) { callback(); return; }
      var src = deps[i];
      i++;
      if (loadedDeps[src]) { next(); return; }
      injectScript(src, function () {
        loadedDeps[src] = true;
        next();
      });
    }
    next();
  }

  function loadApp(src, callback) {
    if (!src) { callback(); return; }
    // Always inject fresh (re-execute the app script)
    injectScript(src, callback);
  }

  // --- Lifecycle ---

  function teardownCurrentPage() {
    if (window.__page && window.__page.teardown) {
      try { window.__page.teardown(); } catch (e) { console.warn('[router] teardown error:', e); }
    }
    window.__page = null;
  }

  function initNewPage() {
    if (window.__page && window.__page.init) {
      try { window.__page.init(); } catch (e) { console.error('[router] init error:', e); }
    }
  }

  // --- Style management ---
  var pageStyleEl = document.createElement('style');
  pageStyleEl.id = 'spa-page-style';
  document.head.appendChild(pageStyleEl);

  // Capture initial page's inline styles
  (function () {
    var existing = document.querySelectorAll('head > style:not(#spa-page-style)');
    var combined = '';
    for (var i = 0; i < existing.length; i++) {
      combined += existing[i].textContent + '\n';
      existing[i].parentNode.removeChild(existing[i]);
    }
    pageStyleEl.textContent = combined;
  })();

  // --- Body class management ---
  function updateBodyClass(doc) {
    var newBody = doc.querySelector('body');
    var classes = document.body.className.split(/\s+/).filter(Boolean);
    // Remove old section-* classes
    classes = classes.filter(function (c) { return c.indexOf('section-') !== 0; });
    // Add new section-* classes from fetched page
    if (newBody) {
      var nc = newBody.className.split(/\s+/);
      for (var i = 0; i < nc.length; i++) {
        if (nc[i].indexOf('section-') === 0) classes.push(nc[i]);
      }
    }
    // Preserve light-mode
    if (document.body.classList.contains('light-mode') && classes.indexOf('light-mode') === -1) {
      classes.push('light-mode');
    }
    document.body.className = classes.join(' ');
  }

  // --- Core navigation ---

  function navigate(url, pushState) {
    if (navigating) return;
    navigating = true;
    showLoading();

    var fetchPromise;
    if (htmlCache[url]) {
      fetchPromise = Promise.resolve(htmlCache[url]);
    } else {
      fetchPromise = fetch(url).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      }).then(function (html) {
        htmlCache[url] = html;
        return html;
      });
    }

    fetchPromise.then(function (html) {
      var parser = new DOMParser();
      var doc = parser.parseFromString(html, 'text/html');

      var newPage = doc.getElementById('page');
      if (!newPage) {
        // Page doesn't support SPA — full navigation
        window.location.href = url;
        return;
      }

      // 1. Teardown current page
      teardownCurrentPage();

      // 2. Remove old app scripts from DOM (deps stay)
      var oldAppScripts = document.querySelectorAll('script[data-page-script]');
      for (var i = 0; i < oldAppScripts.length; i++) {
        // Only remove non-dep scripts (deps are kept forever)
        if (!oldAppScripts[i].hasAttribute('data-dep')) {
          oldAppScripts[i].parentNode.removeChild(oldAppScripts[i]);
        }
      }

      // 3. Update body class
      updateBodyClass(doc);

      // 4. Swap page styles
      pageStyleEl.textContent = extractPageStyle(doc);

      // 5. Swap page content
      var container = document.getElementById('page');
      container.innerHTML = newPage.innerHTML;
      // Copy attributes
      var attrs = ['data-deps', 'data-app'];
      attrs.forEach(function (a) {
        var v = newPage.getAttribute(a);
        if (v) container.setAttribute(a, v); else container.removeAttribute(a);
      });

      // 6. Update document title
      var newTitle = doc.querySelector('title');
      if (newTitle) document.title = newTitle.textContent;

      // 7. Update favicon
      updateFavicon(doc);

      // 8. Update nav active state
      updateNav(url);

      // 9. History
      if (pushState) {
        history.pushState({ path: url }, '', url);
      }

      // 10. Load deps then app
      var deps = parseAttr(newPage, 'data-deps').map(function (s) { return resolveUrl(s, url); });
      var appSrc = newPage.getAttribute('data-app');
      var appUrl = appSrc ? resolveUrl(appSrc, url) : null;

      loadDeps(deps, function () {
        loadApp(appUrl, function () {
          initNewPage();
          hideLoading();
          navigating = false;

          // Scroll
          if (window.location.hash) {
            var target = document.getElementById(window.location.hash.slice(1));
            if (target) { target.scrollIntoView(); return; }
          }
          window.scrollTo(0, 0);
        });
      });

    }).catch(function (err) {
      console.error('[router] Navigation failed:', err);
      hideLoading();
      navigating = false;
      window.location.href = url;
    });
  }

  // --- Event handlers ---

  function handleClick(e) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (e.defaultPrevented) return;

    var link = e.target.closest('a[href]');
    if (!link) return;

    var href = link.getAttribute('href');
    if (!href || href.charAt(0) === '#') return;
    if (link.target === '_blank' || link.hasAttribute('download')) return;
    if (href.indexOf('mailto:') === 0 || href.indexOf('tel:') === 0) return;

    var url;
    try { url = new URL(href, location.href); } catch (err) { return; }
    if (url.origin !== location.origin) return;

    // Same page (with or without hash)
    if (url.pathname === location.pathname) return;

    e.preventDefault();
    navigate(url.pathname, true);
  }

  function handlePopState() {
    if (navigating) return;
    navigate(location.pathname, false);
  }

  // --- Hover prefetch ---
  var prefetchTimer = null;

  function handleMouseOver(e) {
    var link = e.target.closest('a[href]');
    if (!link) return;
    var href = link.getAttribute('href');
    if (!href || href.charAt(0) === '#' || link.target === '_blank') return;

    var url;
    try { url = new URL(href, location.href); } catch (err) { return; }
    if (url.origin !== location.origin) return;
    if (htmlCache[url.pathname]) return;

    prefetchTimer = setTimeout(function () {
      fetch(url.pathname).then(function (r) {
        if (r.ok) return r.text();
      }).then(function (html) {
        if (html) htmlCache[url.pathname] = html;
      }).catch(function () {});
    }, 65);
  }

  function handleMouseOut() {
    if (prefetchTimer) { clearTimeout(prefetchTimer); prefetchTimer = null; }
  }

  // --- Init ---
  history.scrollRestoration = 'manual';
  document.addEventListener('click', handleClick);
  window.addEventListener('popstate', handlePopState);
  document.addEventListener('mouseover', handleMouseOver);
  document.addEventListener('mouseout', handleMouseOut);

  // Mark dep scripts that are already loaded on the initial page
  var page = document.getElementById('page');
  if (page) {
    var initialDeps = parseAttr(page, 'data-deps');
    var pathname = location.pathname;
    initialDeps.forEach(function (s) {
      loadedDeps[resolveUrl(s, pathname)] = true;
    });
  }

})();
