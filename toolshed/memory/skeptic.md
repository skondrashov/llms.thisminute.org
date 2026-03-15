# Skeptic Memory

## Last Session: Cycles 10-11 Review (2026-03-14, 05:28)

### What I Did
- Reviewed Cycle 10 categorization fixes (Code Editors 279->147, Data Analysis 159->92)
- Spot-checked 20 Code Editor entries, 20 Data Analysis entries, 15 Backend Framework entries, 10 random discovered entries
- Reviewed `scripts/find_duplicates.py` and `scripts/check_urls.py` code quality
- Ran duplicate detector (0 name dupes, 3 URL dupe groups in discovered)
- Ran URL health checker on 1,128 curated entries (849 OK, 227 redirects, 52 problems)
- WebFetch-verified 7 URLs: Affinity Photo, Affinity Designer, Slate, TablePlus, Kaggle, PDF Expert, pacman
- Ran test suite (67/67 pass)
- Posted S37-S49 to FORUM.md

### Issues Found (this session)

**S37 -- Backend Frameworks inflated ~27% garbage (WARNING)**
- Jumped from 298 to 453 (+155) due to Cycle 10 changes
- 4/15 random sample are misrouted (slice, htmlquery, Scrutinizer, LemmyNet/lemmy)
- Entries ejected from Code Editors/Data Analysis landed here

**S38 -- 50% miscategorization rate in random discovered sample (BUG)**
- 5 of 10 random entries have wrong categories
- CircleMenu -> should be iOS UI Components, not UI/UX Design Tools
- Percentage -> should be iOS UI Components, not Backend Frameworks
- string.is -> should be Developer Utilities, not Encryption & Privacy
- componego -> should be Backend Frameworks, not Window Managers
- Tencent Docs -> should be Office Suites, not Documentation Tools

**S39 -- find_duplicates.py exit code always 1 (BUG)**
- Similar names always produces results (25,717 pairs), so exit code is always 1
- Useless for CI gating

**S40 -- find_duplicates.py Levenshtein O(n^2) too slow (WARNING)**
- ~132 million comparisons on 16k entries
- Needs algorithmic improvement for CI use

**S41 -- check_urls.py disables SSL verification (WARNING)**
- SSL_CONTEXT.check_hostname = False, verify_mode = CERT_NONE
- Masks real SSL certificate problems

**S42 -- check_urls.py URL dedup code is dead (BUG)**
- Builds unique_entries list but submits full entries list to executor

**S43 -- check_urls.py no per-domain rate limiting (WARNING)**
- 10 concurrent workers can hammer same domain simultaneously

**S44 -- Affinity Photo/Designer URLs moved to affinity.studio (BUG)**
- serif.com/en-us/photo -> 301 to affinity.studio/photo-editing-software
- serif.com/en-us/designer -> 301 to affinity.studio/graphic-design-software

**S45 -- 3 curated entries have dead domains (BUG)**
- HitFilm (fxhome.com) -- DNS failure
- Around (around.co) -- DNS failure, company shut down
- BlueJeans (bluejeans.com) -- DNS failure, shut down by Verizon 2024

**S46 -- Nix URL redirect loop (NOTE)**
- nixos.org/nix redirects to nixos.org/. Should just use nixos.org.

**S47 -- iCloud Drive URL redirect still loops (NOTE)**
- apple.com/icloud/icloud-drive redirects back to apple.com/icloud/

**S48 -- test_no_duplicate_urls doesn't strip URL fragments (BUG)**
- Test misses SwiftGen (5 entries) and go-vet (2 entries) that share base URLs with different fragments

**S49 -- AGENTS.md entry count stale (NOTE)**
- Says 15,601, actual is 16,243

### Issues Status (all sessions)

**Resolved:** S22, S23, S27, S28, S29, S33, S34, S35, S37, S39, S42, S44, S45, S46, S47, S48, S49

**Open -- needs fix:**
- S38: 50% miscategorization in random discovered sample (systemic)
- S40: find_duplicates.py Levenshtein O(n^2)
- S41: check_urls.py SSL disabled
- S43: check_urls.py no per-domain rate limiting

**Open -- notes/low priority:** S15 (tag consistency), S30 (count discrepancy), S31 (Memrise), S32 (Prompts), S36 (Copy Link file://)

### Key Observation

The categorizer has systemic quality problems. Fixing individual categories (Code Editors, Data Analysis) is whack-a-mole -- entries just shift to other wrong categories (Backend Frameworks). The 50% random sample error rate (S38) suggests the discovered catalog needs either (a) dramatically better section maps covering more awesome-list sections, or (b) a fundamentally different categorization approach (LLM-assisted, manual review of top entries per category, or confidence-threshold filtering that excludes low-confidence entries entirely).

### URL Check Baseline (curated, 2026-03-14)
- 1,128 checked, 849 OK (75.3%), 227 redirects (20.1%), 52 problems (4.6%)
- Most 403s are bot-blocking (site is fine), not actual errors
- True dead: Slate, pacman (moved), HitFilm, Around, BlueJeans (DNS dead)
- Stale URLs: Affinity Photo, Affinity Designer (moved to affinity.studio)
