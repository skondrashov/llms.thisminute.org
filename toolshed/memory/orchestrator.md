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
- S30-S32, S36: Minor notes (no code changes needed)
- S15: Tag/source consistency across older entries
- Schema enhancement: maintenance_status, last_verified, license, popularity, alternatives (Backlog)

### Next Priorities
1. More curator work -- thin categories (Mobile IDE 11, Flashcards 14, Desktop App 15)
2. Discovered entry quality -- S38 needs structural categorizer improvement or confidence filtering
3. Script quality (S40, S41, S43) -- low priority improvements
