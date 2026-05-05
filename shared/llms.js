/* llms.js — shared chrome (nav + source + theme toggle) for llms.thisminute.org */
(function () {
  var THEME_KEY = 'thisminute_theme';

  // --- Navigation links (single source of truth) ---
  var NAV_LINKS = [
    { href: '/',               label: 'LLMs',          color: '--color-home' },
    { href: '/harnesses/',     label: 'Harnesses',     color: '--color-harnesses' },
    { href: '/models/',        label: 'Models',        color: '--color-models' },
    { href: '/context/',       label: 'Context',       color: '--color-context' },
    { href: '/tools/',         label: 'Tools',         color: '--color-tools' },
    { href: '/orchestration/', label: 'Orchestration', color: '--color-orchestration' },
    { href: '/forge/',         label: 'Forge',         color: '--color-forge' }
  ];

  var SOURCE_URL = 'https://github.com/thisminute/llms.thisminute.org';

  // --- Inject site nav ---
  // Looks for .forge-theme-toggle (present on every page) and injects the
  // nav before it. Pages don't need any nav HTML — just the toggle placeholder.

  var toggleContainer = document.querySelector('.forge-theme-toggle');
  if (toggleContainer) {
    // Build nav
    var nav = document.createElement('nav');
    nav.className = 'site-nav';

    var path = window.location.pathname;

    NAV_LINKS.forEach(function (link) {
      var a = document.createElement('a');
      a.href = link.href;
      a.textContent = link.label;
      a.style.setProperty('--nav-c', 'var(' + link.color + ')');
      // Match current page: exact match, or path starts with href (for subsections)
      if (link.href === '/' ? path === '/' : path.indexOf(link.href) === 0) {
        a.setAttribute('aria-current', 'page');
      }
      nav.appendChild(a);
    });

    toggleContainer.parentNode.insertBefore(nav, toggleContainer);

    // Build top-right controls: source link + theme button
    toggleContainer.innerHTML =
      '<a href="' + SOURCE_URL + '" class="source-link" target="_blank" rel="noopener" title="View source on GitHub">source</a>' +
      '<button class="icon-btn" id="forge-theme-btn" title="Toggle light/dark mode" aria-label="Toggle theme">' +
        '<svg id="forge-icon-sun" width="16" height="16" viewBox="0 0 16 16" fill="none" style="display:none">' +
          '<path d="M8 1a.5.5 0 01.5.5v1a.5.5 0 01-1 0v-1A.5.5 0 018 1zm0 11a.5.5 0 01.5.5v1a.5.5 0 01-1 0v-1A.5.5 0 018 12zm7-4a.5.5 0 01-.5.5h-1a.5.5 0 010-1h1A.5.5 0 0115 8zM4 8a.5.5 0 01-.5.5h-1a.5.5 0 010-1h1A.5.5 0 014 8zm8.95-3.54a.5.5 0 010 .71l-.71.71a.5.5 0 11-.71-.71l.71-.71a.5.5 0 01.71 0zM4.46 11.46a.5.5 0 010 .71l-.7.71a.5.5 0 11-.71-.71l.7-.71a.5.5 0 01.71 0zm8.49 1.42a.5.5 0 01-.71 0l-.71-.71a.5.5 0 01.71-.71l.71.71a.5.5 0 010 .71zM4.46 4.54a.5.5 0 01-.71 0l-.7-.71a.5.5 0 11.7-.71l.71.71a.5.5 0 010 .71zM8 4.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7z" fill="currentColor"/>' +
        '</svg>' +
        '<svg id="forge-icon-moon" width="16" height="16" viewBox="0 0 16 16" fill="none">' +
          '<path d="M6 .278a.77.77 0 01.08.858 7.2 7.2 0 00-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.79.79 0 01.81.316.73.73 0 01-.031.893A8.35 8.35 0 018.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.75.75 0 016 .278z" fill="currentColor"/>' +
        '</svg>' +
      '</button>';

    document.getElementById('forge-theme-btn').addEventListener('click', function () {
      applyTheme(document.body.classList.contains('light-mode') ? 'dark' : 'light');
    });
  }

  // --- Theme ---

  function getTheme() {
    try {
      var s = localStorage.getItem(THEME_KEY);
      if (s) return s;
    } catch (e) {}
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    var isLight = theme === 'light';
    document.body.classList.toggle('light-mode', isLight);
    var sun = document.getElementById('forge-icon-sun');
    var moon = document.getElementById('forge-icon-moon');
    if (sun) sun.style.display = isLight ? 'block' : 'none';
    if (moon) moon.style.display = isLight ? 'none' : 'block';
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
  }

  applyTheme(getTheme());

  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      try { if (!localStorage.getItem(THEME_KEY)) applyTheme(e.matches ? 'dark' : 'light'); } catch (err) {}
    });
  }

})();
