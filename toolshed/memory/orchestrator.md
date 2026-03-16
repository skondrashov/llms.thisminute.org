# Orchestrator Memory

## Session 2026-03-14 (Cycle 8)

### What Happened
- Spawned curator → +30 curated entries across 5 thin categories (Terminal UI, NLP, LLM Tools, Desktop App Frameworks, Flashcards)
- Spawned designer → dark/light toggle polish, "See Also" section, "Copy Link" button
- Spawned skeptic → found 10 issues (S27-S36), 2 bugs, 3 warnings, 5 notes
- Fixed S27 (duplicates), S28 (dead AllenNLP), S29 (ncurses OS), S33 (matchMedia listener), S34 (breadcrumb hover), S35 (shuffle See Also)
- Final state (Cycle 8): 15,585 entries, 123 categories, 65 tests passing
- Final state (Cycle 9): 15,601 entries, 123 categories, 65 tests passing

### Cycle Count
- Cycles 1-4: Catalog expansion (121 -> 290 entries)
- Cycle 5: Major categorization fixes + re-scrape (290 -> 16,186)
- Cycle 6: Categorization cleanup round 2 + Networking category (16,186 -> 16,175)
- Cycle 7: Deep categorization cleanup + design UX (16,175 -> 15,555)
- Cycle 8: Thin category curation + design polish + skeptic review (15,555 -> 15,585)
- Cycle 9: Category expansion + mobile UX + search highlighting (15,585 -> 15,601)
- Cycle 10: S22/S23 categorization fix (Code Editors 279->147, Data Analysis 159->92) (15,601 -> 16,247)
- Cycle 11: Quality automation scripts (find_duplicates, check_urls), fixed 4 dupes + 5 URL collisions (16,247 -> 16,243)
- Cycle 12: Skeptic review S37-S49, orchestrator fixed S44-S49 (dead URLs, script bugs, test gap)
- Cycle 13: S37 Backend Frameworks fix (453->205), Tier 3 threshold 0.15->0.20 (16,243 -> 15,803)
- Cycle 14: JSON-LD structured data (1,153 sampled entries, 455.6 KB)
- Cycle 15: UI overhaul (view tabs, pricing/language/tag filters, forge integration, light mode, a11y), 2x curator (+45 entries, all thin categories filled), skeptic S50-S57, fixes applied (15,803 -> 15,859)
- Cycle 16: Curator Cycle 11 (+24 entries, 3 thin categories filled), S52 light-mode fix, librarian cleanup (15,859 -> 15,866)
- Cycle 17: Designer polish — covered/unique split on built cards, forge summary unique/covered stats, sparse requests message, tag bar forge exclusions
- Cycle 18: Builder fixed S40 — O(n^2) Levenshtein → SymSpell deletion neighborhoods, 10+ min → ~3s
- Cycle 19: Skeptic S58-S62, fixed S58 (sparse msg filtered bug), S59 (contrast), S60 (contrast)
- Cycle 20: Curator Cycle 12 — Error Handling 21→34, Statistical Tools 21→32, +16 entries, cleaned 28 dupes (15,866 → 15,898)
- Cycle 21: Librarian cleanup round 3. Chess regressed 24→11 (discovered entries removed in Cycle 20 cleanup)
- Cycle 22: Curator Cycle 13 — Chess restored 11→27 (+16 curated entries). Total: 15,912
- Cycle 23: Builder fixed S41 (SSL verification default) + S43 (per-domain rate limiting) in check_urls.py
- Cycle 24: Skeptic S63-S66. Fixed S64/S65 (removed 11 miscategorized discovered entries). S63 (TOCTOU race) noted. S66 (stale counts) deferred to librarian. (15,912 → 15,901)
- Cycle 25: Librarian cleanup round 4. S66 fixed. S40/S41/S43 marked resolved in docs. All counts current at 15,901.
- Cycle 26: Curator Cycle 14 — added 21 curated entries to 3 zero-curated categories (Caching, Static Analysis, Configuration), cleaned 17 dupes. Net: 15,905.
- Cycle 27: Designer Cycle 4 — forge search boost (forge entries sort first in All view), forge match count in search results, color-coded search highlights (green for ideas, blue for built).
- Cycle 28: Skeptic S67-S68 (notes only, no bugs). Fixed S68 stale counts in AGENTS.md + STRATEGY.md (curated: 1,289, discovered: 14,616, total: 15,905).
- Cycle 29: Curator Cycle 15 — added 21 curated entries to 3 more zero-curated categories (Blockchain 7, Template Engines 7, Math & Numerics 7), cleaned 10 dupes. Total: 15,916.
- Cycle 30: Librarian cleanup round 5. All docs current at 15,916 / 1,310 curated. Stale notes S15/S30-S32/S36/S66 removed.
- Cycle 31: Curator Cycle 16 — Database Drivers baseline (7 curated, 2 dupes removed). Total: 15,921.
- Cycle 32: Skeptic S69-S70. Fixed S69 (Eigen URL redirect), S70 (OpenZeppelin invalid language field).
- Cycle 33: Librarian cleanup round 6. Docs current at 15,921 / 1,317 curated.
- Cycle 34: Builder added --strict flag to build.py for S38. Excludes Tier 3 discovered entries (6,721 = 46%). Normal: 15,921. Strict: 9,200.
- Cycle 35: Skeptic S71-S72. S71 (T3 logic mismatch, no impact). S72 (28.6% of kept entries may disagree on category — future improvement for --strict).
- Cycle 36: Librarian cleanup round 7. S38 marked mitigated. --strict documented in AGENTS.md Commands.
- Cycle 37: Enhanced --strict with S72 category agreement (orchestrator direct fix). get_confidence_tier now returns (tier, category). Strict: 15,921→6,597 (was 9,200 before agreement check).
- Cycle 38: Curator Cycle 17 — Compression & Archiving baseline (7 curated, 1 dupe removed). Total: 15,927. Only 2 zero-curated categories remain (iOS-specific).
- Cycle 39: Skeptic S73. Fixed T2 first-match→best-match in get_confidence_tier(). Strict: 6,597→6,957 (recovered 360 false excludes).
- Cycle 40: Librarian cleanup round 8. Docs current at 15,927 / 1,384 curated / strict 6,957.
- Cycle 41: Curator Cycle 18 — Networking baseline (7 curated, 2 dupes removed). Stripped forge summary promotional text + landing page manifesto toned down per user feedback. Total: 15,932.
- Cycle 42: Librarian cleanup round 9. Docs current at 15,932 / 1,391 curated / strict 6,962.
- Cycle 43: Skeptic light review — all clear. S73 correctly absent from issues (was fixed Cycle 37).
- Cycle 44: Curator Cycle 19 — CLI Frameworks 8→14, Frontend Frameworks 8→14 (+12 curated, -5 dupes). Total: 15,939.
- Cycle 45: Librarian cleanup round 10. Docs at 15,939 / 1,343 curated. Deploy queued for landing page + toolshed overhaul.
- Cycle 46: Curator Cycle 20 — Text Processing 4→10, Game Engines 9→16 (+13 curated, -4 dupes). Total: 15,947.
- Cycle 47: Deploy confirmed live (5c6856b). Skeptic post-deploy review — all production endpoints verified. S74 (stale counts) noted for librarian.
- Cycle 48: Librarian cleanup round 11. S73 removed (was fixed), S74 fixed. Docs at 15,947 / 1,355 curated. Only S38 (mitigated) + S63 remain as warnings.
- Cycle 49: Curator Cycle 21 — Video Editing 9→15 (+6 curated, -3 dupes). Total: 15,950.
- Cycle 50: Curator Cycle 22 — Backend Frameworks +7 curated (19 total across 8 langs), -8 dupes. Total: 15,949.
- Cycle 51: Librarian cleanup round 12. Docs at 15,949 / 1,368 curated / strict 6,988.
- Cycle 52: Skeptic review — zero issues. All clean.
- Cycle 53: Curator Cycle 23 — Image Processing 10→16, Cross-Platform Frameworks 10→16 (+12 curated, -7 dupes). Total: 15,954.
- Cycle 54: Librarian cleanup round 13. Docs at 15,954 / 1,380 curated / strict 6,997.

### Lessons
- Curator created duplicate entries (ollama/ollama-llm, langchain/langchain-llm) instead of moving originals. Next time: explicitly tell curator to move existing entries rather than create new ones with different IDs.
- Curator also added an archived project (AllenNLP). Next time: tell curator to verify projects are actively maintained.
- The curator+designer+skeptic+fix pattern works well as a single orchestrator cycle.
- Doing concrete fixes directly as orchestrator is efficient when changes are small and scoped.

### Critical Lesson (Carried Forward): Don't re-categorize discovered file in-place
Entries in discovered_*.json don't store `source_label` or `section` metadata. Re-categorizing in-place destroys section map assignments. **Always delete and re-scrape rather than re-categorize in-place.**

### Remaining Open Issues
- S38: 50% miscategorization in random discovered sample (systemic, partially addressed)
- S40, S41, S43: Quality script improvements (O(n^2), SSL, rate limiting)
- S15, S30-S32, S36: Minor notes (no code changes needed)
- S56, S57: Schema missing status field; inconsistent filter reset on view switch (notes)
- Schema enhancement: maintenance_status, last_verified, license, popularity, alternatives (Backlog)

### Resolved (Cycles 15-16)
- S50-S55: Meta description, triage escaping, WCAG contrast, a11y on clickable stats, focus-visible, curated count in docs

### Next Priorities
1. S56: Add status field to schema.json (housekeeping)
2. Continue UI iteration -- visual polish, mobile testing, better forge pipeline viz
3. Discovered entry quality -- S38 needs structural categorizer improvement
4. Script quality (S40, S41, S43) -- low priority
5. Thin categories: Error Handling (21), Statistical Tools (21) are thinnest -- curator could fill if needed
