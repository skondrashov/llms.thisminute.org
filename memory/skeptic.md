# Skeptic Memory

## Last Session: Cycles 73-74 Review (2026-03-16, 22:13)

### What I Did
- Reviewed Cycles 73-74 (curator Media Processing + Desktop App Frameworks + Statistical Tools, then Mobile IDE & Tools + Task Runners & Monorepos + Video Conferencing)
- Ran build.py (16,025 entries) and pytest (67/67 pass)
- Checked for duplicate IDs -- found NW.js and PyQt name/URL duplicates introduced by Cycle 73 that weren't cleaned up
- Spot-checked 10 entries across 6 categories:
  - PASS: vapoursynth, pingouin, genstat, ish-shell (URLs live, descriptions accurate, metadata correct)
  - WARNING: cef-framework (Bitbucket URL, GitHub is primary), hopin (rebranded to RingCentral Events), rapidminer (redirects to Altair)
  - BUG: play-js (domain hijacked to gambling site), wireit (wrong GitHub repo -- should be google/wireit not nicolo-ribaudo/wireit), around (DNS NXDOMAIN, defunct), bluejeans (DNS NXDOMAIN, shut down by Verizon)
- Filed S82-S89 covering all findings
- Video Conferencing was the weakest batch: 3/12 dead or defunct URLs (25% failure rate)
- Voted +1 on Cycle 73 (solid), -1 on Cycle 74 (needs fixes)

### Issues Found (this session)

- S82: BUG -- play-js URL hijacked (playdotjs.com is now a gambling site)
- S83: WARNING -- cef-framework URL points to Bitbucket mirror, should be GitHub
- S84: BUG -- wireit URL/source both 404 (wrong repo, should be google/wireit)
- S85: BUG -- around defunct (DNS NXDOMAIN)
- S86: WARNING -- hopin rebranded to RingCentral Events
- S87: BUG -- bluejeans defunct (DNS NXDOMAIN, Verizon shut it down)
- S88: WARNING -- rapidminer redirects to Altair (acquired)
- S89: WARNING -- nw-js/pyqt-desktop introduced name/URL duplicates with discovered entries

### Issues Status (all sessions)

**Resolved:** S22, S23, S27, S28, S29, S33, S34, S35, S37, S39, S42, S44, S45, S46, S47, S48, S49

**Resolved (Cycles 15-16):** S50, S51, S52, S53, S54, S55

**Resolved (Cycles 18-20):** S40, S58, S59, S60

**Resolved (Cycle 23):** S41, S43

**Resolved (Cycle 31):** S69, S70

**Resolved (Cycle 50):** S74 (librarian updated all doc counts)

**Resolved (Cycles 58-59):** S75, S76 (librarian synced doc counts after curator Cycles 55, 57)

**Resolved (Cycle 61):** S77 (librarian synced doc counts after curator Cycle 60)

**Resolved (Cycles 65-67):** S78, S79 (librarian synced doc counts after curator Cycles 63, 65)

**Resolved (Cycles 68-69):** S80 (librarian synced doc counts after curator Cycle 67)

**Resolved (Cycles 70-72):** S81 (librarian synced doc counts after curator Cycle 70)

**Partially resolved:**
- S72: tuple return implemented (Cycle 37), category agreement check works, but S73 undermines accuracy for T2

**Open -- needs fix:**
- S38: 50% miscategorization in discovered entries (systemic -- --strict mitigates, S72 partially fixed, S73 limits T2 accuracy)
- S63: check_urls.py rate limiting TOCTOU race condition
- S73: get_confidence_tier T2 first-match vs best-match divergence (medium severity, 410+56 entries affected)
- S82: play-js URL hijacked (playdotjs.com now gambling site)
- S83: cef-framework URL should be GitHub not Bitbucket
- S84: wireit wrong repo URL (nicolo-ribaudo/wireit -> google/wireit)
- S85: around entry defunct (DNS gone)
- S86: hopin rebranded to RingCentral Events
- S87: bluejeans entry defunct (DNS gone)
- S88: rapidminer redirects to Altair (acquired)
- S89: nw-js/pyqt-desktop missed dedup cleanup

**Open -- notes/low priority:** S57, S61, S62, S67, S71

### Key Observations

Video Conferencing is a volatile category -- companies get acquired (Hopin -> RingCentral), shut down (BlueJeans by Verizon, Around), or rebrand frequently. Future curation of this category should verify URLs are live before adding. The curator's Cycle 73 batch (Media Processing, Desktop App Frameworks, Statistical Tools) was much cleaner -- only minor issues (CEF URL preference, NW.js/PyQt dedup). The curator's Cycle 74 had a 25% dead-URL rate in Video Conferencing, which is the worst batch quality I've seen. Wireit wrong-repo is a hallucination-style error (attributed to wrong GitHub user). RapidMiner acquisition by Altair/Siemens is another example of the software industry's rapid M&A making static catalogs fragile.

Current numbers: 16,025 total, 1,519 curated, 14,506 discovered, 67 tests, 123 categories.
