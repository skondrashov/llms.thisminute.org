// ─── Mermaid Init ─────────────────────────────────────
function initMermaid() {
  if (typeof mermaid === 'undefined') return;
  const isLight = document.body.classList.contains('light-mode');
  mermaid.initialize({
    startOnLoad: false,
    theme: isLight ? 'default' : 'dark',
    themeVariables: isLight ? {
      primaryColor: '#fffbf8',
      primaryTextColor: '#3d2a30',
      primaryBorderColor: '#7fbb8f',
      lineColor: '#7a5e64',
      secondaryColor: '#faeae4',
      tertiaryColor: '#fef6f1'
    } : {
      primaryColor: '#2a1e22',
      primaryTextColor: '#f0e0dc',
      primaryBorderColor: '#a8d8b5',
      lineColor: '#b8a19c',
      secondaryColor: '#352830',
      tertiaryColor: '#1f1618'
    }
  });
}
initMermaid();

// ─── Constants ────────────────────────────────────────
const HIERARCHY_LABELS = {
  'adversarial': 'Adversarial',
  'chain-of-command': 'Chain of Command',
  'orchestrated': 'Orchestrated',
  'swarm': 'Swarm',
  'mesh': 'Mesh',
  'pipeline': 'Pipeline',
  'consensus': 'Consensus',
  'federated': 'Federated'
};
const SEARCH_DEBOUNCE_MS = 120;
const SCROLL_TOP_THRESHOLD = 600;
const COPY_FEEDBACK_MS = 1500;
const MAX_VISIBLE_TAGS = 5;
const MAX_SIMILAR_ITEMS = 8;
const MAX_EXAMPLE_LENGTH = 120;
const STAGGER_DELAY_MS = 25;
const MAX_STAGGER_MS = 400;
const CARD_VISIBILITY_THRESHOLD = 0.05;

// Structural classes (loaded from data.js, written by build.py)
const SC = window.STRUCTURAL_CLASSES || {};
const SC_COLORS = {};
const SC_LABELS = {};
Object.entries(SC).forEach(([key, val]) => {
  SC_COLORS[key] = val.color || '#888';
  SC_LABELS[key] = val.label || key;
});

const CATEGORY_COLORS = {
  'Military & Defense': '#ef4444',
  'Corporate & Business': '#3b82f6',
  'Government & Political': '#8b5cf6',
  'Academic & Research': '#f59e0b',
  'Creative & Arts': '#ec4899',
  'Technology & Engineering': '#22d3ee',
  'Medical & Emergency': '#10b981',
  'Historical & Traditional': '#d97706',
  'Nature-Inspired': '#4ade80',
  'Network Topologies': '#6366f1',
  'Agile & Software': '#06b6d4',
  'Social & Community': '#f472b6',
  'Novel & Experimental': '#a78bfa',
  'Religious & Spiritual': '#fbbf24',
  'Legal & Judicial': '#fb923c',
  'Education & Training': '#38bdf8',
  'Intelligence & Espionage': '#64748b',
  'Maritime & Aviation': '#0ea5e9',
  'Sports & Competition': '#f97316',
  'Media & Communications': '#e879f9'
};

// ─── State ────────────────────────────────────────────
const state = {
  structures: window.STRUCTURES || [],
  activeCategory: null,
  activeStructuralClass: null,
  activeDomain: (() => { try { return localStorage.getItem('orchestration_lens_seen') ? null : 'core'; } catch { return 'core'; } })(),
  searchQuery: '',
  sortBy: 'category',
  focusedCardIndex: -1,
  visitedPatterns: (() => { try { return new Set(JSON.parse(localStorage.getItem('orchestration_visited') || '[]')); } catch { return new Set(); } })(),
  votedPatterns: (() => { try { return new Set(JSON.parse(localStorage.getItem('orchestration_votes') || '[]')); } catch { return new Set(); } })(),
  voteData: {},       // { pattern_id: { total, recent, seriousness, rate_label } }
  lightMode: (() => { try { const saved = localStorage.getItem('thisminute_theme'); if (saved !== null) return saved === 'light'; return !window.matchMedia('(prefers-color-scheme: dark)').matches; } catch { return true; } })()
};

// API base URL (empty = same origin)
const API_BASE = '';

// ─── Helpers ──────────────────────────────────────────
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function totalAgentCount(s) {
  if (!s.agents) return 0;
  return s.agents.reduce((sum, a) => sum + (a.count || 1), 0);
}

function markVisited(id) {
  state.visitedPatterns.add(id);
  try { localStorage.setItem('orchestration_visited', JSON.stringify([...state.visitedPatterns])); } catch {}
  const card = document.querySelector(`.card[data-id="${id}"]`);
  if (card) card.classList.add('visited');
}

function toList(val) {
  return Array.isArray(val) ? val.join(', ') : (val || '');
}

function highlightText(text, query) {
  if (!query) return esc(text);
  const escaped = esc(text);
  const qEsc = esc(query).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return escaped.replace(new RegExp(`(${qEsc})`, 'gi'), '<mark>$1</mark>');
}

// ─── Focus Trap (accessibility) ──────────────────────
let activeFocusTrap = null;
let preTrapFocus = null;

function enableFocusTrap(container) {
  if (activeFocusTrap) {
    // Re-entering (e.g. prev/next nav) — remove old listener, keep original preTrapFocus
    container.removeEventListener('keydown', activeFocusTrap);
  } else {
    preTrapFocus = document.activeElement;
  }
  activeFocusTrap = function(e) {
    if (e.key !== 'Tab') return;
    const focusable = container.querySelectorAll(
      'button:not([disabled]), [href], input:not([tabindex="-1"]), select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) { e.preventDefault(); last.focus(); }
    } else {
      if (document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  };
  container.addEventListener('keydown', activeFocusTrap);
}

function disableFocusTrap(container) {
  if (activeFocusTrap) {
    container.removeEventListener('keydown', activeFocusTrap);
    activeFocusTrap = null;
  }
  if (preTrapFocus) {
    preTrapFocus.focus();
    preTrapFocus = null;
  }
}

// ─── Theme ────────────────────────────────────────────
function applyTheme() {
  state.lightMode = document.body.classList.contains('light-mode');
  initMermaid();
}
applyTheme();
new MutationObserver(() => applyTheme()).observe(document.body, { attributes: true, attributeFilter: ['class'] });

// ─── Categories ───────────────────────────────────────
function getCategories() {
  const cats = {};
  state.structures.forEach(s => {
    cats[s.category] = (cats[s.category] || 0) + 1;
  });
  return Object.entries(cats).sort((a, b) => b[1] - a[1]);
}

function generateAgentFile(s) {
  const lines = [];
  lines.push(`# ${s.name}`);
  lines.push('');
  lines.push(s.description || s.summary);
  lines.push('');

  if (s.category) {
    lines.push(`**Category:** ${s.category}`);
    lines.push('');
  }

  if (s.structuralClass) {
    lines.push(`**Structure:** ${SC_LABELS[s.structuralClass] || s.structuralClass}`);
    lines.push('');
  }

  if (s.hierarchyTypes && s.hierarchyTypes.length) {
    lines.push(`**Topology:** ${s.hierarchyTypes.map(t => HIERARCHY_LABELS[t] || t).join(', ')}`);
    lines.push('');
  }

  if (s.whenToUse) {
    lines.push('## When to Use');
    lines.push('');
    lines.push(s.whenToUse);
    lines.push('');
  }

  if (s.strengths && s.strengths.length) {
    lines.push('## Strengths');
    lines.push('');
    s.strengths.forEach(x => lines.push(`- ${x}`));
    lines.push('');
  }

  if (s.weaknesses && s.weaknesses.length) {
    lines.push('## Weaknesses');
    lines.push('');
    s.weaknesses.forEach(x => lines.push(`- ${x}`));
    lines.push('');
  }

  if (s.agents && s.agents.length) {
    lines.push('## Roles');
    lines.push('');
    s.agents.forEach(a => {
      const count = a.count && a.count > 1 ? ` (×${a.count})` : '';
      lines.push(`### ${a.name || a.role}${count}`);
      lines.push('');
      if (a.description) lines.push(`${a.description}`);
      if (a.memory) lines.push(`- **Memory:** ${a.memory}`);
      lines.push('');
    });
  }

  if (s.forums && s.forums.length) {
    lines.push('## Communication Channels');
    lines.push('');
    s.forums.forEach(f => {
      lines.push(`### ${f.name}`);
      lines.push('');
      lines.push(`- **Type:** ${f.type || 'general'}`);
      const parts = f.participants ? (toList(f.participants)) : 'all';
      lines.push(`- **Participants:** ${parts}`);
      lines.push('');
    });
  }

  if (s.memoryArchitecture) {
    lines.push('## Information Flow');
    lines.push('');
    if (s.memoryArchitecture.shared) {
      const val = toList(s.memoryArchitecture.shared);
      lines.push(`- **Shared knowledge:** ${val}`);
    }
    if (s.memoryArchitecture.private) {
      const val = toList(s.memoryArchitecture.private);
      lines.push(`- **Private to individuals:** ${val}`);
    }
    if (s.memoryArchitecture.description) {
      lines.push(`- **How it works:** ${s.memoryArchitecture.description}`);
    }
    lines.push('');
  }

  if (s.diagram) {
    lines.push('## Topology');
    lines.push('');
    lines.push('```mermaid');
    lines.push(s.diagram);
    lines.push('```');
    lines.push('');
  }

  if (s.tags && s.tags.length) {
    lines.push(`**Tags:** ${s.tags.join(', ')}`);
    lines.push('');
  }

  lines.push('---');
  lines.push(`*Generated from [Orchestration](https://thisminute.org/orchestration#${s.id})*`);
  lines.push('');

  return lines.join('\n');
}

function downloadAgentFile(s) {
  const content = generateAgentFile(s);
  const blob = new Blob([content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = s.id + '.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function renderStats() {
  document.getElementById('total-count').textContent = state.structures.length;
  document.getElementById('category-count').textContent = getCategories().length;
  document.getElementById('structure-count').textContent = Object.keys(SC).length;
  const totalAgents = state.structures.reduce((sum, s) => sum + totalAgentCount(s), 0);
  document.getElementById('agent-count').textContent = totalAgents;
}

// ─── Shared filter tile helpers ─────────────────────
function buildFilterTiles(items, activeValue, attr, colorMap, labelMap) {
  let html = `<div class="filter-tile filter-tile-all${!activeValue ? ' active' : ''}" data-${attr}="" style="--tile-color:var(--accent)" tabindex="0" role="button">
    <div class="filter-tile-name">All</div>
    <div class="filter-tile-count">${state.structures.length}</div>
  </div>`;
  items.forEach(([key, count]) => {
    html += `<div class="filter-tile${activeValue === key ? ' active' : ''}" data-${attr}="${esc(key)}" style="--tile-color:${colorMap[key] || '#888'}" tabindex="0" role="button">
      <div class="filter-tile-name">${esc(labelMap ? (labelMap[key] || key) : key)}</div>
      <div class="filter-tile-count">${count}</div>
    </div>`;
  });
  return html;
}

function wireFilterTiles(container, attr, onActivate) {
  container.querySelectorAll(`[data-${attr}]`).forEach(tile => {
    const activate = () => onActivate(tile.dataset[attr] || null);
    tile.addEventListener('click', activate);
    tile.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); } });
  });
}

function renderCategories() {
  const container = document.getElementById('category-tiles');
  container.innerHTML = buildFilterTiles(getCategories(), state.activeCategory, 'category', CATEGORY_COLORS);
  wireFilterTiles(container, 'category', val => {
    state.activeCategory = val;
    renderCategories();
    updateCategoryLabel();
    updateFilterDescriptions();
    renderGrid();
    syncMobileCategories();
  });
  updateCategoryLabel();
}

function updateFilterLabel(elementId, activeValue, colorMap, labelMap) {
  const label = document.getElementById(elementId);
  if (activeValue) {
    const color = (colorMap || {})[activeValue] || '#888';
    label.textContent = (labelMap || {})[activeValue] || activeValue;
    label.style.cssText = `background:${color}22;color:${color}`;
  } else {
    label.textContent = '';
    label.style.cssText = '';
  }
}

function updateCategoryLabel() {
  updateFilterLabel('category-active-label', state.activeCategory, CATEGORY_COLORS);
}

// ─── Structural Class Tiles ──────────────────────────
function getStructuralClassCounts() {
  const counts = {};
  state.structures.forEach(s => {
    const sc = s.structuralClass;
    if (sc) counts[sc] = (counts[sc] || 0) + 1;
  });
  return Object.entries(counts).sort((a, b) => b[1] - a[1]);
}

function renderStructureTiles() {
  const container = document.getElementById('structure-tiles');
  container.innerHTML = buildFilterTiles(getStructuralClassCounts(), state.activeStructuralClass, 'sc', SC_COLORS, SC_LABELS);
  wireFilterTiles(container, 'sc', val => {
    state.activeStructuralClass = val;
    renderStructureTiles();
    updateStructureLabel();
    updateFilterDescriptions();
    renderGrid();
    syncMobileCategories();
  });
  updateStructureLabel();
}

function updateStructureLabel() {
  updateFilterLabel('structure-active-label', state.activeStructuralClass, SC_COLORS, SC_LABELS);
}

// Wire up panel expand/collapse (close siblings, only one open at a time)
const PANEL_IDS = ['domain-panel', 'structure-panel', 'category-panel'];
function togglePanel(headerId, panelId) {
  const panel = document.getElementById(panelId);
  const header = document.getElementById(headerId);
  const opening = !panel.classList.contains('expanded');
  // Close all panels
  PANEL_IDS.forEach(id => {
    const p = document.getElementById(id);
    const h = document.getElementById(id + '-header');
    p.classList.remove('expanded');
    h.setAttribute('aria-expanded', 'false');
  });
  // Open the clicked one if it was closed
  if (opening) {
    panel.classList.add('expanded');
    header.setAttribute('aria-expanded', 'true');
    // Position the dropdown body just below the header
    const rect = header.getBoundingClientRect();
    const body = panel.querySelector('.filter-panel-body');
    body.style.top = (rect.bottom + 4) + 'px';
  }
}
// Click outside closes all dropdowns
document.addEventListener('click', e => {
  if (!e.target.closest('.filter-panel')) {
    PANEL_IDS.forEach(id => {
      const p = document.getElementById(id);
      const h = document.getElementById(id + '-header');
      p.classList.remove('expanded');
      h.setAttribute('aria-expanded', 'false');
    });
  }
});
PANEL_IDS.forEach(id => {
  const headerId = id + '-header';
  const el = document.getElementById(headerId);
  el.addEventListener('click', () => togglePanel(headerId, id));
  el.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      togglePanel(headerId, id);
    }
  });
});

// ─── Vote Data Loading ──────────────────────────────────
async function loadVoteData() {
  try {
    const resp = await fetch(API_BASE + '/orchestration/api/votes');
    if (resp.ok) {
      state.voteData = await resp.json();
      renderGrid(); // re-render with vote data
    }
  } catch (e) {
    // API unavailable — graceful degradation
  }
}

async function castVote(patternId) {
  if (state.votedPatterns.has(patternId)) return;
  try {
    const resp = await fetch(API_BASE + '/orchestration/api/vote/' + patternId, { method: 'POST' });
    if (resp.ok || resp.status === 409) {
      state.votedPatterns.add(patternId);
      try { localStorage.setItem('orchestration_votes', JSON.stringify([...state.votedPatterns])); } catch {}
      // Optimistic update — only increment on new vote, not duplicate
      if (resp.ok) {
        if (!state.voteData[patternId]) state.voteData[patternId] = { total: 0, recent: 0, seriousness: 0 };
        state.voteData[patternId].total++;
        state.voteData[patternId].recent++;
        state.voteData[patternId].seriousness = state.voteData[patternId].total + state.voteData[patternId].recent * 3;
      }
      return true;
    }
  } catch (e) { /* API unavailable */ }
  return false;
}

async function loadComments(patternId) {
  try {
    const resp = await fetch(API_BASE + '/orchestration/api/comments/' + patternId);
    if (resp.ok) return await resp.json();
  } catch (e) { /* API unavailable */ }
  return [];
}

async function postComment(patternId, displayName, body) {
  try {
    const resp = await fetch(API_BASE + '/orchestration/api/comments/' + patternId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: displayName || 'Anonymous', body, honeypot: '' })
    });
    if (resp.ok) return await resp.json();
  } catch (e) { /* API unavailable */ }
  return null;
}

async function flagComment(commentId) {
  try {
    const resp = await fetch(API_BASE + '/orchestration/api/comments/' + commentId + '/flag', { method: 'POST' });
    if (resp.ok) return await resp.json();
  } catch (e) { /* API unavailable */ }
  return null;
}

// ─── Filtering & Sorting ──────────────────────────────
function getFiltered() {
  let results = state.structures.filter(s => {
    if (state.activeDomain && getDomain(s) !== state.activeDomain) return false;
    if (state.activeCategory && s.category !== state.activeCategory) return false;
    if (state.activeStructuralClass && s.structuralClass !== state.activeStructuralClass) return false;
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      const scText = (SC_LABELS[s.structuralClass] || s.structuralClass || '').toLowerCase();
      const htText = (s.hierarchyTypes || []).map(t => HIERARCHY_LABELS[t] || t).join(' ').toLowerCase();
      return (s.name || '').toLowerCase().includes(q) ||
             (s.summary || '').toLowerCase().includes(q) ||
             (s.category || '').toLowerCase().includes(q) ||
             (s.tags || []).some(t => t.toLowerCase().includes(q)) ||
             scText.includes(q) ||
             htText.includes(q);
    }
    return true;
  });
  if (state.sortBy === 'name') {
    results.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  } else if (state.sortBy === 'agents') {
    results.sort((a, b) => totalAgentCount(b) - totalAgentCount(a));
  } else if (state.sortBy === 'category') {
    results.sort((a, b) => (a.category || '').localeCompare(b.category || '') || (a.name || '').localeCompare(b.name || ''));
  } else if (state.sortBy === 'structure') {
    results.sort((a, b) => (a.structuralClass || '').localeCompare(b.structuralClass || '') || (a.name || '').localeCompare(b.name || ''));
  } else if (state.sortBy === 'votes') {
    results.sort((a, b) => ((state.voteData[b.id] || {}).total || 0) - ((state.voteData[a.id] || {}).total || 0));
  } else if (state.sortBy === 'trending') {
    results.sort((a, b) => ((state.voteData[b.id] || {}).seriousness || 0) - ((state.voteData[a.id] || {}).seriousness || 0));
  } else if (state.sortBy === 'random') {
    for (let i = results.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [results[i], results[j]] = [results[j], results[i]];
    }
  }
  return results;
}

function setSort(by) {
  state.sortBy = by;
  document.querySelectorAll('.toolbar button').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('sort-' + by);
  if (btn) btn.classList.add('active');
  renderGrid();
}

// Sort button listeners
['name', 'agents', 'category', 'structure', 'votes', 'trending', 'random'].forEach(key => {
  document.getElementById('sort-' + key).addEventListener('click', () => setSort(key));
});

// ─── Grid Rendering ───────────────────────────────────
let lastFiltered = [];
let gridObserver = null;

function renderGrid() {
  if (gridObserver) { gridObserver.disconnect(); gridObserver = null; }
  const filtered = getFiltered();
  lastFiltered = filtered;
  const grid = document.getElementById('grid');
  const countEl = document.getElementById('result-count');

  // Update result count
  if (state.searchQuery || state.activeCategory || state.activeStructuralClass || state.activeDomain) {
    countEl.textContent = `${filtered.length} of ${state.structures.length}`;
  } else {
    countEl.textContent = '';
  }

  // Keep domain tile counts in sync
  renderDomainTiles();

  if (!filtered.length) {
    grid.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">
        <svg width="48" height="48" viewBox="0 0 16 16" fill="currentColor" opacity="0.3"><path d="M11.742 10.344a6.5 6.5 0 10-1.397 1.398h-.001l3.85 3.85a1 1 0 001.415-1.414l-3.85-3.85zm-5.242.156a5 5 0 110-10 5 5 0 010 10z"/></svg>
      </div>
      <div class="empty-state-text">No patterns match your search.</div>
      <div class="empty-state-hint">Try a different term or category.</div>
      <button class="empty-state-clear" id="clear-search">Clear filters</button>
    </div>`;
    const clearBtn = document.getElementById('clear-search');
    if (clearBtn) clearBtn.addEventListener('click', clearFilters);
    return;
  }

  grid.innerHTML = filtered.map((s, i) => {
    const color = CATEGORY_COLORS[s.category] || '#888';
    const roleCount = s.agents ? s.agents.length : 0;
    const visited = state.visitedPatterns.has(s.id) ? ' visited' : '';
    const name = highlightText(s.name, state.searchQuery);
    const summary = highlightText(s.summary, state.searchQuery);
    const sc = s.structuralClass;
    const scColor = SC_COLORS[sc] || '#888';
    const scLabel = SC_LABELS[sc] || sc || '';
    const structureBadge = sc ? `<span class="structure-badge" style="color:${scColor};border-color:${scColor}33;background:${scColor}11">${esc(scLabel)}</span>` : '';
    const vd = state.voteData[s.id];
    let voteBadge = '';
    let trendBadge = '';
    if (vd && vd.total > 0) {
      voteBadge = `<span class="card-vote-badge"><span class="vote-arrow">&#9650;</span> ${vd.total}</span>`;
      if (vd.rate_label === 'hot') trendBadge = `<span class="card-trending-badge hot">hot</span>`;
      else if (vd.rate_label === 'trending') trendBadge = `<span class="card-trending-badge">trending</span>`;
    }
    return `<div class="card${visited}" data-id="${esc(s.id)}" data-index="${i}" style="--cat-color:${color};transition-delay:${Math.min(i * STAGGER_DELAY_MS, MAX_STAGGER_MS)}ms">
      <div class="card-header">
        <span class="card-name">${name}</span>
        <span style="display:flex;align-items:center;gap:0.4rem;flex-shrink:0">${trendBadge}${voteBadge}<span class="card-badge">${roleCount} roles</span></span>
      </div>
      <div class="card-structure-badge">${structureBadge}</div>
      <div class="card-category">${esc(s.category)}</div>
      <div class="card-summary">${summary}</div>
      ${s.harnesses ? `<div class="card-harnesses" title="Ships natively in these harnesses">Ships in: ${s.harnesses.map(h => esc(h.harness)).join(' \u00b7 ')}</div>` : ''}
      ${s.realWorldExample ? `<div class="card-example">${esc(s.realWorldExample.length > MAX_EXAMPLE_LENGTH ? s.realWorldExample.slice(0, MAX_EXAMPLE_LENGTH - 3) + '...' : s.realWorldExample)}</div>` : ''}
      <div class="card-tags">${(s.tags || []).slice(0, MAX_VISIBLE_TAGS).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
    </div>`;
  }).join('');

  // Attach click handlers
  grid.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => openDetail(card.dataset.id));
  });

  // Staggered entrance animation via IntersectionObserver
  requestAnimationFrame(() => {
    gridObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          gridObserver.unobserve(entry.target);
        }
      });
    }, { threshold: CARD_VISIBILITY_THRESHOLD });
    grid.querySelectorAll('.card').forEach(card => gridObserver.observe(card));
  });

  state.focusedCardIndex = -1;
}

// ─── Lens mapping (three-lens IA) ────────────────────
// Lens is assigned by build.py from lenses.json. Three values:
//   core   — industry-standard agent patterns every dev will meet
//   wild   — real-world org / industry case studies (NASA, Toyota, airline CRM)
//   garden — nature-inspired, philosophical, and exotic patterns
function getDomain(s) {
  return s.lens || 'garden';
}
const DOMAIN_COLORS = {
  'core': '#a8d8b5',
  'wild': '#f0c56a',
  'garden': '#d8a8c8'
};
const DOMAIN_LABELS = {
  'core': 'Core',
  'wild': 'In the Wild',
  'garden': 'The Garden'
};

function getDomainCounts() {
  const counts = {};
  state.structures.forEach(s => {
    const d = getDomain(s);
    counts[d] = (counts[d] || 0) + 1;
  });
  // Fixed order
  return ['core', 'wild', 'garden'].map(d => [d, counts[d] || 0]);
}

function renderDomainTiles() {
  const container = document.getElementById('domain-tiles');
  container.innerHTML = buildFilterTiles(getDomainCounts(), state.activeDomain, 'domain', DOMAIN_COLORS, DOMAIN_LABELS);
  wireFilterTiles(container, 'domain', val => {
    state.activeDomain = val;
    renderDomainTiles();
    updateDomainLabel();
    updateFilterDescriptions();
    renderGrid();
    syncMobileCategories();
  });
  updateDomainLabel();
}

function updateDomainLabel() {
  updateFilterLabel('domain-active-label', state.activeDomain, DOMAIN_COLORS, DOMAIN_LABELS);
}

// ─── Filter Descriptions ──────────────────────────────
const DOMAIN_DESCRIPTIONS = {
  'core': 'The industry-standard patterns every agent developer now meets in practice. Each Core pattern shows which harnesses (Claude Code, Cursor, Aider, LangGraph, CrewAI, and so on) ship it natively, so you can recognize what you\'re already using.',
  'wild': 'Real-world organizational patterns applied at scale: NASA mission control, Toyota production, airline crew resource management, military command structures, corporate hierarchies. The serious case-study layer.',
  'garden': 'Nature-inspired, philosophical, and exotic patterns. Ant-colony stigmergy, jazz ensembles, pirate democracies, mycelial networks, religious orders, thought experiments. Still educational, but the fun half.'
};
const SC_DESCRIPTIONS = {
  'hub-and-spoke': 'A central coordinator dispatches work to peripheral specialists and synthesizes their results.',
  'strict-hierarchy': 'Multi-layered tree with authority flowing down and reporting flowing up.',
  'mentor-apprentice': 'Knowledge transfer relationship with gradually increasing autonomy.',
  'peer-ensemble': 'Small group of equals with fluid leadership and shared decision-making.',
  'assembly-pipeline': 'Sequential stages where each transforms an artifact before passing it forward.',
  'compartmented-cells': 'Isolated groups connected only through intermediaries for security or independence.',
  'federation-of-sovereigns': 'Autonomous subgroups that coordinate through bridges and liaisons.',
  'democratic-assembly': 'All agents participate as equals in collective decision-making.',
  'adversarial-arena': 'Competing agents evaluated by a neutral judge or objective function.',
  'swarm-stigmergy': 'Many simple agents coordinating indirectly through environmental signals.',
  'triage-and-dispatch': 'A gatekeeper classifies incoming work and routes it to the right specialist.',
  'dual-key-safeguard': 'Multiple agents must concur before high-stakes actions proceed.',
  'creative-atelier': 'A vision-holder directs specialized departments toward a creative goal.',
  'market-ecosystem': 'Agents interact through bidding, trading, and reputation mechanisms.',
  'cyclic-renewal': 'Agents rotate through phases or roles with knowledge transfer between cycles.'
};
const CATEGORY_DESCRIPTIONS = {
  'Military & Defense': 'Command structures from armed forces — strict rank, clear authority, rapid escalation.',
  'Corporate & Business': 'Organizational patterns from companies — boards, divisions, matrix management.',
  'Government & Political': 'Governance structures — legislatures, bureaucracies, federal systems.',
  'Academic & Research': 'University and lab structures — departments, peer review, tenure tracks.',
  'Creative & Arts': 'Patterns from studios, orchestras, and creative teams — directors, ensembles, workshops.',
  'Medical & Emergency': 'Hospital and emergency response hierarchies — triage, incident command, care teams.',
  'Historical & Traditional': 'Ancient and traditional organizational forms — guilds, tribes, monastic orders.',
  'Nature-Inspired': 'Structures modeled on biological systems — colonies, flocks, ecosystems.',
  'Network Topologies': 'Patterns from network architecture — mesh, star, ring, bus topologies.',
  'Agile & Software': 'Software development patterns — sprints, standups, DevOps pipelines.',
  'Social & Community': 'Community and social movement structures — cooperatives, collectives, movements.',
  'Novel & Experimental': 'Theoretical or emerging patterns not yet widely adopted.',
  'Religious & Spiritual': 'Structures from religious organizations — parishes, monasteries, councils.',
  'Legal & Judicial': 'Court systems, legal hierarchies, adversarial proceedings.',
  'Education & Training': 'Classroom, mentorship, and training structures.',
  'Intelligence & Espionage': 'Compartmented cells, handler networks, need-to-know hierarchies.',
  'Maritime & Aviation': 'Ship and aircraft crew structures — bridge teams, cockpit resource management.',
  'Sports & Competition': 'Team structures, coaching hierarchies, tournament formats.',
  'Media & Communications': 'Newsroom, broadcast, and editorial structures.',
  'Technology & Engineering': 'Engineering team patterns and AI-native agent architectures.'
};
function updateFilterDescriptions() {
  document.getElementById('domain-desc').textContent =
    state.activeDomain ? (DOMAIN_DESCRIPTIONS[state.activeDomain] || '') : '';
  document.getElementById('structure-desc').textContent =
    state.activeStructuralClass ? (SC_DESCRIPTIONS[state.activeStructuralClass] || '') : '';
  document.getElementById('category-desc').textContent =
    state.activeCategory ? (CATEGORY_DESCRIPTIONS[state.activeCategory] || '') : '';
}

function clearFilters() {
  state.searchQuery = '';
  state.activeCategory = null;
  state.activeStructuralClass = null;
  state.activeDomain = null;
  document.getElementById('search').value = '';
  renderDomainTiles();
  renderCategories();
  renderStructureTiles();
  updateFilterDescriptions();
  renderGrid();
}

// ─── Detail Drawer ────────────────────────────────────
let diagramCounter = 0;
let currentDetailId = null;

function buildSection(title, contentHtml, defaultOpen) {
  const expanded = defaultOpen ? ' expanded' : '';
  return `<div class="detail-section${expanded}">
    <button class="section-toggle" aria-expanded="${defaultOpen}">
      ${esc(title)}
      <span class="section-chevron">&#9654;</span>
    </button>
    <div class="section-body"><div class="section-inner"><div class="section-content">${contentHtml}</div></div></div>
  </div>`;
}

let handlingPopstate = false;

async function openDetail(id) {
  const s = state.structures.find(x => x.id === id);
  if (!s) return;

  currentDetailId = id;
  markVisited(id);

  const detail = document.getElementById('detail');
  const overlay = document.getElementById('overlay');
  const color = CATEGORY_COLORS[s.category] || '#888';
  const roleCount = s.agents ? s.agents.length : 0;
  const agentTotal = totalAgentCount(s);

  // Find prev/next in current filtered list
  const idx = lastFiltered.findIndex(x => x.id === id);
  const prevId = idx > 0 ? lastFiltered[idx - 1].id : null;
  const nextId = idx < lastFiltered.length - 1 ? lastFiltered[idx + 1].id : null;

  const detailSc = s.structuralClass;
  const detailScColor = SC_COLORS[detailSc] || '#888';
  const detailScLabel = SC_LABELS[detailSc] || detailSc || '';
  const scBadge = detailSc ? `<span class="tag" style="background:${detailScColor}22;color:${detailScColor}">${esc(detailScLabel)}</span>` : '';
  const vd = state.voteData[s.id];
  const voteCount = vd ? vd.total : 0;
  const isVoted = state.votedPatterns.has(s.id);

  let html = `<div class="detail-top-bar">
      <button class="upvote-btn${isVoted ? ' voted' : ''}" id="upvote-btn" title="Upvote this pattern">
        <span class="arrow">&#9650;</span>
        <span id="upvote-count">${voteCount}</span>
      </button>
      <button class="detail-top-btn" id="download-agent-btn" title="Download agent file (.md)">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M.5 9.9a.5.5 0 01.5.5v2.5a1 1 0 001 1h12a1 1 0 001-1v-2.5a.5.5 0 011 0v2.5a2 2 0 01-2 2H2a2 2 0 01-2-2v-2.5a.5.5 0 01.5-.5z"/><path d="M7.646 11.854a.5.5 0 00.708 0l3-3a.5.5 0 00-.708-.708L8.5 10.293V1.5a.5.5 0 00-1 0v8.793L5.354 8.146a.5.5 0 10-.708.708l3 3z"/></svg>
        Agent file
      </button>
      <button class="detail-top-btn" id="copy-link-btn" title="Copy link to this pattern">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.715 6.542L3.343 7.914a3 3 0 104.243 4.243l1.828-1.829A3 3 0 008.586 5.5L8 6.086a1 1 0 00-.154.199 2 2 0 01.861 3.337L6.88 11.45a2 2 0 11-2.83-2.83l.793-.792a4 4 0 01-.128-1.287z"/><path d="M6.586 4.672A3 3 0 007.414 9.5l.775-.776a2 2 0 01-.896-3.346L9.12 3.55a2 2 0 112.83 2.83l-.793.792c.112.42.155.855.128 1.287l1.372-1.372a3 3 0 10-4.243-4.243L6.586 4.672z"/></svg>
        Copy link
      </button>
      <button class="detail-close" id="detail-close" title="Close (Esc)">&times;</button>
    </div>
    <div class="detail-header">
      <h2>${esc(s.name)}</h2>
      <div class="detail-meta">
        <span class="tag" style="background:${color}22;color:${color}">${esc(s.category)}</span>
        ${scBadge}
        <span class="tag">${roleCount} roles${agentTotal !== roleCount ? ` (${agentTotal} agents)` : ''}</span>
        ${s.realWorldExample ? `<span style="color:var(--text-muted);font-size:0.8rem">e.g. ${esc(s.realWorldExample)}</span>` : ''}
      </div>
    </div>
    <div class="detail-body">
      <div class="detail-col">`;

  // Topology
  if (s.diagram) {
    html += buildSection('Topology', '<div class="diagram-container" id="diagram-container"></div>', true);
  }

  // Description
  html += buildSection('Description', `<p>${esc(s.description || s.summary)}</p>`, true);

  // Ships natively in (harness-native mappings, Core patterns only)
  if (s.harnesses && s.harnesses.length) {
    const items = s.harnesses.map(h => {
      const featureText = `${esc(h.harness)} <span style="color:var(--text-muted)">${esc(h.feature)}</span>`;
      return h.url
        ? `<li><a href="${esc(h.url)}" target="_blank" rel="noopener">${featureText}</a></li>`
        : `<li>${featureText}</li>`;
    }).join('');
    html += buildSection('Ships natively in', `<ul class="harness-list">${items}</ul>`, true);
  }

  // Structurally Similar
  if (detailSc) {
    const similar = state.structures
      .filter(x => x.id !== s.id && x.structuralClass === detailSc && x.category !== s.category)
      .slice(0, MAX_SIMILAR_ITEMS);
    if (similar.length) {
      const chips = similar.map(x => {
        return `<span class="similar-chip" data-id="${esc(x.id)}" title="${esc(x.category)}">${esc(x.name)}</span>`;
      }).join('');
      html += buildSection('Structurally Similar', `<p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.5rem">Different domains, same ${esc(detailScLabel)} structure</p><div class="similar-chips">${chips}</div>`, true);
    }
  }

  // When to use
  if (s.whenToUse) {
    html += buildSection('When to Use', `<p>${esc(s.whenToUse)}</p>`, true);
  }

  // Strengths / Weaknesses
  if (s.strengths || s.weaknesses) {
    let swHtml = '<div class="sw-grid">';
    if (s.strengths) {
      swHtml += `<div><h3 class="sw-strengths">Strengths</h3><ul>${s.strengths.map(x => `<li class="strength">${esc(x)}</li>`).join('')}</ul></div>`;
    }
    if (s.weaknesses) {
      swHtml += `<div><h3 class="sw-weaknesses">Weaknesses</h3><ul>${s.weaknesses.map(x => `<li class="weakness">${esc(x)}</li>`).join('')}</ul></div>`;
    }
    swHtml += '</div>';
    html += buildSection('Strengths & Weaknesses', swHtml, true);
  }

  html += `</div><div class="detail-col">`;

  // Agents
  if (s.agents && s.agents.length) {
    let agentHtml = `<table class="agent-table"><thead><tr><th>Role</th><th>Description</th><th>Memory</th></tr></thead><tbody>`;
    s.agents.forEach(a => {
      agentHtml += `<tr><td>${esc(a.name || a.role)}</td><td>${esc(a.description || '')}</td><td><span class="tag">${esc(a.memory || 'private')}</span></td></tr>`;
    });
    agentHtml += `</tbody></table>`;
    html += buildSection('Agents', agentHtml, true);
  }

  // Communication Channels
  if (s.forums && s.forums.length) {
    let chHtml = '<div class="channel-list">';
    s.forums.forEach(f => {
      const parts = f.participants ? (toList(f.participants)) : 'all';
      chHtml += `<div class="channel">
        <span class="channel-type">${esc(f.type || 'general')}</span>
        <span class="channel-name">${esc(f.name)}</span>
        <span class="channel-participants">${esc(parts)}</span>
      </div>`;
    });
    chHtml += '</div>';
    html += buildSection('Communication Channels', chHtml, false);
  }

  // Memory Architecture
  if (s.memoryArchitecture) {
    let memHtml = '<div class="memory-grid">';
    if (s.memoryArchitecture.shared) {
      const val = toList(s.memoryArchitecture.shared);
      memHtml += `<div class="memory-item"><h4>Shared</h4><p>${esc(val)}</p></div>`;
    }
    if (s.memoryArchitecture.private) {
      const val = toList(s.memoryArchitecture.private);
      memHtml += `<div class="memory-item"><h4>Private</h4><p>${esc(val)}</p></div>`;
    }
    if (s.memoryArchitecture.description) {
      memHtml += `<div class="memory-item"><h4>Notes</h4><p>${esc(s.memoryArchitecture.description)}</p></div>`;
    }
    memHtml += '</div>';
    html += buildSection('Memory Architecture', memHtml, false);
  }

  // Community Notes (comments)
  html += buildSection('Community Notes', `<div class="comments-section" id="comments-section">
    <div class="comment-list" id="comment-list"><p class="no-comments">Loading...</p></div>
    <form class="comment-form" id="comment-form">
      <input type="text" id="comment-name" placeholder="Name (optional)" maxlength="50" aria-label="Display name">
      <textarea id="comment-body" placeholder="Share what works, what doesn't, or how you've used this pattern..." maxlength="2000" aria-label="Comment"></textarea>
      <input type="text" class="hp-field" name="website" id="comment-hp" tabindex="-1" autocomplete="off">
      <button type="submit" class="comment-submit" id="comment-submit">Post</button>
    </form>
  </div>`, true);

  html += `</div></div>`;

  // Prev / Next navigation
  html += `<div class="detail-nav">
    <button class="detail-nav-btn" id="nav-prev" ${!prevId ? 'disabled' : ''} data-id="${prevId || ''}">
      <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M11.354 1.646a.5.5 0 010 .708L5.707 8l5.647 5.646a.5.5 0 01-.708.708l-6-6a.5.5 0 010-.708l6-6a.5.5 0 01.708 0z"/></svg>
      Previous
    </button>
    <button class="detail-nav-btn" id="nav-next" ${!nextId ? 'disabled' : ''} data-id="${nextId || ''}">
      Next
      <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.646 1.646a.5.5 0 01.708 0l6 6a.5.5 0 010 .708l-6 6a.5.5 0 01-.708-.708L10.293 8 4.646 2.354a.5.5 0 010-.708z"/></svg>
    </button>
  </div>`;

  detail.innerHTML = html;
  detail.scrollTop = 0;
  detail.classList.add('active');
  overlay.classList.add('active');
  if (handlingPopstate) {
    history.replaceState(null, '', '#' + s.id);
  } else {
    history.pushState(null, '', '#' + s.id);
  }

  // Focus management: trap focus in drawer
  enableFocusTrap(detail);
  const closeBtn = document.getElementById('detail-close');
  if (closeBtn) closeBtn.focus();

  // Wire up section toggles
  detail.querySelectorAll('.section-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
      const section = toggle.closest('.detail-section');
      section.classList.toggle('expanded');
      toggle.setAttribute('aria-expanded', section.classList.contains('expanded'));
    });
  });

  // Wire up similar-chip clicks + keyboard accessibility
  detail.querySelectorAll('.similar-chip').forEach(chip => {
    chip.setAttribute('tabindex', '0');
    chip.setAttribute('role', 'button');
    chip.addEventListener('click', () => openDetail(chip.dataset.id));
    chip.addEventListener('keydown', ev => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        openDetail(chip.dataset.id);
      }
    });
  });

  // Wire up close / download / copy / nav
  document.getElementById('detail-close').addEventListener('click', closeDetail);

  document.getElementById('download-agent-btn').addEventListener('click', () => downloadAgentFile(s));

  document.getElementById('copy-link-btn').addEventListener('click', async function() {
    const url = location.origin + location.pathname + '#' + s.id;
    try {
      await navigator.clipboard.writeText(url);
      this.classList.add('copied');
      this.innerHTML = `<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 010 .708l-7 7a.5.5 0 01-.708 0l-3.5-3.5a.5.5 0 11.708-.708L6.5 10.293l6.646-6.647a.5.5 0 01.708 0z"/></svg> Copied`;
      setTimeout(() => {
        this.classList.remove('copied');
        this.innerHTML = `<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.715 6.542L3.343 7.914a3 3 0 104.243 4.243l1.828-1.829A3 3 0 008.586 5.5L8 6.086a1 1 0 00-.154.199 2 2 0 01.861 3.337L6.88 11.45a2 2 0 11-2.83-2.83l.793-.792a4 4 0 01-.128-1.287z"/><path d="M6.586 4.672A3 3 0 007.414 9.5l.775-.776a2 2 0 01-.896-3.346L9.12 3.55a2 2 0 112.83 2.83l-.793.792c.112.42.155.855.128 1.287l1.372-1.372a3 3 0 10-4.243-4.243L6.586 4.672z"/></svg> Copy link`;
      }, COPY_FEEDBACK_MS);
    } catch {}
  });

  const prevBtn = document.getElementById('nav-prev');
  const nextBtn = document.getElementById('nav-next');
  if (prevBtn && prevBtn.dataset.id) prevBtn.addEventListener('click', () => openDetail(prevBtn.dataset.id));
  if (nextBtn && nextBtn.dataset.id) nextBtn.addEventListener('click', () => openDetail(nextBtn.dataset.id));

  // Upvote button
  const upvoteBtn = document.getElementById('upvote-btn');
  upvoteBtn.addEventListener('click', async () => {
    if (state.votedPatterns.has(s.id)) return;
    const ok = await castVote(s.id);
    if (ok) {
      upvoteBtn.classList.add('voted');
      document.getElementById('upvote-count').textContent = (state.voteData[s.id] || {}).total || 1;
      renderGrid();
    }
  });

  // Load and render comments
  function renderComments(comments, listEl) {
    if (!listEl) return;
    if (!comments.length) {
      listEl.innerHTML = '<p class="no-comments">No comments yet. Be the first!</p>';
      return;
    }
    listEl.innerHTML = comments.map(c => `
      <div class="comment-item${c.hidden ? ' hidden-comment' : ''}">
        <div class="comment-header">
          <span class="comment-name">${esc(c.display_name)}</span>
          <span class="comment-time">${esc(c.time_ago)}</span>
        </div>
        <div class="comment-body">${esc(c.body)}</div>
        <div class="comment-actions">
          <button class="flag-btn" data-comment-id="${c.id}" title="Flag as inappropriate">flag</button>
        </div>
      </div>
    `).join('');
    listEl.querySelectorAll('.flag-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const result = await flagComment(parseInt(btn.dataset.commentId));
        if (result) {
          btn.textContent = 'flagged';
          btn.disabled = true;
        }
      });
    });
  }

  loadComments(s.id).then(comments => {
    renderComments(comments, document.getElementById('comment-list'));
  });

  // Comment form submission
  const commentForm = document.getElementById('comment-form');
  commentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const nameInput = document.getElementById('comment-name');
    const bodyInput = document.getElementById('comment-body');
    const hpInput = document.getElementById('comment-hp');
    const submitBtn = document.getElementById('comment-submit');

    if (hpInput.value) return; // honeypot triggered
    const body = bodyInput.value.trim();
    if (!body) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Posting...';

    const result = await postComment(s.id, nameInput.value.trim(), body);
    if (result && result.ok) {
      bodyInput.value = '';
      const comments = await loadComments(s.id);
      renderComments(comments, document.getElementById('comment-list'));
    }
    submitBtn.disabled = false;
    submitBtn.textContent = 'Post';
  });

  // Render diagram (guard against navigation during async render)
  if (s.diagram && typeof mermaid !== 'undefined') {
    const renderingId = id;
    try {
      diagramCounter++;
      const { svg } = await mermaid.render('d' + diagramCounter, s.diagram);
      if (currentDetailId === renderingId) {
        const dc = document.getElementById('diagram-container');
        if (dc) dc.innerHTML = svg;
      }
    } catch (e) {
      if (currentDetailId === renderingId) {
        const dc = document.getElementById('diagram-container');
        if (dc) dc.innerHTML = `<pre style="color:var(--text-muted);font-size:0.8rem;white-space:pre-wrap">${esc(s.diagram)}</pre>`;
      }
    }
  }
}

function closeDetail(skipHistory) {
  const detail = document.getElementById('detail');
  disableFocusTrap(detail);
  detail.classList.remove('active');
  document.getElementById('overlay').classList.remove('active');
  currentDetailId = null;
  if (!skipHistory) history.replaceState(null, '', location.pathname);
}

// ─── Search ───────────────────────────────────────────
let searchTimeout;
document.getElementById('search').addEventListener('input', e => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    state.searchQuery = e.target.value;
    renderGrid();
  }, SEARCH_DEBOUNCE_MS);
});

// ─── Overlay / Escape ─────────────────────────────────
document.getElementById('overlay').addEventListener('click', closeDetail);

// ─── Back to Top ──────────────────────────────────────
const backToTop = document.getElementById('back-to-top');
window.addEventListener('scroll', () => {
  backToTop.classList.toggle('visible', window.scrollY > SCROLL_TOP_THRESHOLD);
}, { passive: true });
backToTop.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ─── Keyboard Shortcuts ───────────────────────────────
const shortcutsOverlay = document.getElementById('shortcuts-overlay');
let shortcutsTrigger = null;
function openShortcutsOverlay(trigger) {
  shortcutsTrigger = trigger || document.activeElement;
  shortcutsOverlay.classList.add('visible');
  shortcutsOverlay.setAttribute('tabindex', '-1');
  shortcutsOverlay.focus();
}
function closeShortcutsOverlay() {
  shortcutsOverlay.classList.remove('visible');
  if (shortcutsTrigger) { shortcutsTrigger.focus(); shortcutsTrigger = null; }
}
document.getElementById('shortcuts-btn').addEventListener('click', (e) => {
  openShortcutsOverlay(e.currentTarget);
});

const fieldnotesOverlay = document.getElementById('fieldnotes-overlay');
let fieldnotesTrigger = null;
function openFieldnotesOverlay(trigger) {
  fieldnotesTrigger = trigger || document.activeElement;
  fieldnotesOverlay.classList.add('visible');
  const panel = fieldnotesOverlay.querySelector('.fieldnotes-panel');
  panel.setAttribute('tabindex', '-1');
  panel.focus();
}
function closeFieldnotesOverlay() {
  fieldnotesOverlay.classList.remove('visible');
  if (fieldnotesTrigger) { fieldnotesTrigger.focus(); fieldnotesTrigger = null; }
}
document.getElementById('fieldnotes-btn').addEventListener('click', (e) => {
  openFieldnotesOverlay(e.currentTarget);
});
document.getElementById('fieldnotes-inline').addEventListener('click', (e) => {
  openFieldnotesOverlay(e.currentTarget);
});
fieldnotesOverlay.addEventListener('click', e => {
  if (e.target === fieldnotesOverlay) closeFieldnotesOverlay();
});

document.addEventListener('keydown', e => {
  const tag = (e.target.tagName || '').toLowerCase();
  const isInput = tag === 'input' || tag === 'textarea' || tag === 'select';

  // Close field notes overlay on Escape
  if (fieldnotesOverlay.classList.contains('visible')) {
    if (e.key === 'Escape') { closeFieldnotesOverlay(); e.preventDefault(); }
    return;
  }

  // Close shortcuts overlay on any non-modifier key
  if (shortcutsOverlay.classList.contains('visible')) {
    if (!['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) {
      closeShortcutsOverlay();
      e.preventDefault();
    }
    return;
  }

  // Escape: close detail, then clear search
  if (e.key === 'Escape') {
    if (document.getElementById('detail').classList.contains('active')) {
      closeDetail();
    } else if (state.searchQuery || state.activeCategory || state.activeStructuralClass || state.activeDomain) {
      clearFilters();
    } else if (isInput) {
      e.target.blur();
    }
    return;
  }

  // Skip if typing in input
  if (isInput) return;

  // When detail drawer is open, only allow detail-specific keys
  if (currentDetailId) {
    if (e.key === 'ArrowLeft' || e.key === 'h') {
      const prev = document.getElementById('nav-prev');
      if (prev && prev.dataset.id) openDetail(prev.dataset.id);
      return;
    }
    if (e.key === 'ArrowRight' || e.key === 'l') {
      const next = document.getElementById('nav-next');
      if (next && next.dataset.id) openDetail(next.dataset.id);
      return;
    }
    if (e.key === 't') {
      const btn = document.getElementById('forge-theme-btn');
      if (btn) btn.click();
      return;
    }
    return;
  }

  if (e.key === '/') {
    e.preventDefault();
    document.getElementById('search').focus();
    return;
  }

  if (e.key === '?') {
    openShortcutsOverlay();
    return;
  }

  if (e.key === 't') {
    const btn = document.getElementById('forge-theme-btn');
    if (btn) btn.click();
    return;
  }

  if (e.key === 's') {
    setSort('random');
    return;
  }

  // j/k navigation
  const cards = document.querySelectorAll('.card');
  if (!cards.length) return;

  function focusCard(index) {
    state.focusedCardIndex = index;
    cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
    cards.forEach(c => c.style.outline = '');
    cards[index].style.outline = '2px solid var(--accent)';
    cards[index].style.outlineOffset = '2px';
  }

  if (e.key === 'j') {
    e.preventDefault();
    focusCard(Math.min(state.focusedCardIndex + 1, cards.length - 1));
    return;
  }

  if (e.key === 'k') {
    if (state.focusedCardIndex <= 0) return;
    e.preventDefault();
    focusCard(state.focusedCardIndex - 1);
    return;
  }

  if (e.key === 'Enter' && state.focusedCardIndex >= 0 && cards[state.focusedCardIndex]) {
    openDetail(cards[state.focusedCardIndex].dataset.id);
    return;
  }

});

// ─── Mobile ───────────────────────────────────────────
const controlsEl = document.getElementById('controls');
const mobileBar = document.getElementById('mobile-filter-bar');
const mobileTab = document.getElementById('mobile-filter-tab');
const mobilePanelEl = document.getElementById('mobile-filter-panel');

function syncMobileCategories() {
  let html = `<div class="mobile-section-label">Origin</div>`;
  html += buildFilterTiles(getDomainCounts(), state.activeDomain, 'domain', DOMAIN_COLORS, DOMAIN_LABELS);
  html += `<div class="mobile-section-label mobile-section-label-sep">Structure</div>`;
  html += buildFilterTiles(getStructuralClassCounts(), state.activeStructuralClass, 'sc', SC_COLORS, SC_LABELS);
  html += `<div class="mobile-section-label mobile-section-label-sep">Field</div>`;
  html += buildFilterTiles(getCategories(), state.activeCategory, 'category', CATEGORY_COLORS);
  mobilePanelEl.innerHTML = html;
  wireFilterTiles(mobilePanelEl, 'domain', val => {
    state.activeDomain = val;
    renderDomainTiles();
    renderGrid();
    mobileBar.classList.remove('open');
  });
  wireFilterTiles(mobilePanelEl, 'sc', val => {
    state.activeStructuralClass = val;
    renderStructureTiles();
    renderGrid();
    mobileBar.classList.remove('open');
  });
  wireFilterTiles(mobilePanelEl, 'category', val => {
    state.activeCategory = val;
    renderCategories();
    renderGrid();
    mobileBar.classList.remove('open');
  });
}

const controlsObserver = new IntersectionObserver(([entry]) => {
  if (window.innerWidth <= 768) {
    mobileBar.classList.toggle('visible', !entry.isIntersecting);
    if (entry.isIntersecting) mobileBar.classList.remove('open');
  }
}, { threshold: 0 });
controlsObserver.observe(controlsEl);

mobileTab.addEventListener('click', () => {
  syncMobileCategories();
  mobileBar.classList.toggle('open');
});

// ─── Init ─────────────────────────────────────────────
renderStats();
renderDomainTiles();
renderCategories();
renderStructureTiles();
renderGrid();
try { localStorage.setItem('orchestration_lens_seen', '1'); } catch {}

// Load vote data async (graceful degradation)
loadVoteData();

// Open from URL hash
if (location.hash) {
  const id = location.hash.slice(1);
  if (state.structures.some(s => s.id === id)) {
    openDetail(id);
  }
}

// ─── Popstate (browser back/forward) ──────────────────
window.addEventListener('popstate', async () => {
  handlingPopstate = true;
  try {
    if (location.hash) {
      const id = location.hash.slice(1);
      if (state.structures.some(s => s.id === id)) {
        await openDetail(id);
      } else {
        closeDetail(true);
      }
    } else {
      if (currentDetailId) closeDetail(true);
    }
  } finally {
    handlingPopstate = false;
  }
});
