# Curator Memory

## Last Session: Cycle 23 (2026-03-16)

### What I Did
- Expanded Image Processing from 10 curated to 16 curated in `data/creative_media.json`
- Expanded Cross-Platform Frameworks from 10 curated to 16 curated in `data/mobile_desktop.json`
- Added 12 curated entries total (6 per category)
- Removed 7 discovered entries from `data/discovered_20260314.json`

### Image Processing (+6 curated, -4 discovered)
New entries: tesseract, pngquant, svgo, scikit-image, upscayl, thumbor
- Removed discovered: upscayl (had OS=["macos"] only), thumbor (was in Photo Management with broken URL), scikit-image (minimal description), svgo (was actually ajstarks/svgo Go SVG generation lib, NOT the Node.js SVGO optimizer)

### Cross-Platform Frameworks (+6 curated, -3 discovered)
New entries: cordova, uno-platform, kivy, beeware, quasar, framework7
- Removed discovered: kivy (was in Desktop App Frameworks), quasar (was in Container Orchestration -- completely wrong), framework7 (was in Frontend Frameworks)

### Build State
- 15,954 entries, 123 categories
- 67/67 tests pass
- 1,380 curated + 14,574 discovered
- 0 duplicate ID warnings

### Key Decisions
- **thumbor URL**: Used github.com/thumbor/thumbor instead of thumbor.org (TLS cert error on thumbor.org)
- **svgo ID conflict**: Discovered `svgo` was a completely different tool (Go SVG generation by ajstarks). Replaced with the much more prominent Node.js SVGO optimizer.
- **Kivy category**: Moved from Desktop App Frameworks to Cross-Platform Frameworks -- Kivy targets mobile (iOS/Android) in addition to desktop, making it a better fit.
- **BeeWare source URL**: Used github.com/beeware/toga (the GUI toolkit) rather than the main beeware.org repo, since Toga is the main deliverable.
- **Uno Platform pricing = free**: Apache 2.0 licensed, despite having commercial support offerings.
- **Quasar and Framework7**: Both are Vue.js/JS-based frameworks that bridge web and mobile. Their discovered entries were badly miscategorized.

### Already Exists in Image Processing (Don't Re-add)
- pillow, sharp, imagemagick, opencv, libvips, exiftool, graphicsmagick, squoosh, tinypng, imgproxy (original 10)
- tesseract, pngquant, svgo, scikit-image, upscayl, thumbor (added this cycle)
- ffmpeg -> Media Processing (not Image Processing)
- darktable -> Image Editors

### Already Exists in Cross-Platform Frameworks (Don't Re-add)
- react-native, flutter, ionic, capacitor, dotnet-maui, kotlin-multiplatform, nativescript, expo, swiftui, jetpack-compose (original 10)
- cordova, uno-platform, kivy, beeware, quasar, framework7 (added this cycle)
- avalonia, compose-multiplatform -> Desktop App Frameworks
- electron, tauri -> Desktop App Frameworks

---

## Previous Session: Cycle 22 (2026-03-16)

### What I Did
- Expanded Backend Frameworks curated coverage in `data/web.json`
- Added 7 curated entries: actix-web, phoenix, spring-boot, laravel, nestjs, koa, rocket
- Removed 8 discovered entries from `data/discovered_20260314.json` (6 ID conflicts: phoenix, rocket, laravel, koa, spring-boot, nestjs; 1 URL conflict: actix; 1 related duplicate: actixactix-web)

### Build State
- 15,949 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **fastapi and hono already existed**: Both were already curated in development.json and web.json respectively. Skipped.
- **Replaced 2 suggested entries with koa and rocket**: Since fastapi and hono already existed, added Koa (by Express team, important Node.js framework) and Rocket (prominent Rust framework) to reach 7.
- **phoenix ID conflict**: Discovered `phoenix` was a TUI framework (phoenix-tui/phoenix), NOT the Elixir web framework. Removed discovered entry; curated entry is the much more prominent Elixir Phoenix framework.
- **actix vs actix-web**: Used `actix-web` as ID (matches the actual crate name). Discovered had `actix` (ID) pointing to actix.rs and `actixactix-web` pointing to GitHub. Both removed.
- **spring-boot discovered was miscategorized**: Was in "HTTP Libraries" instead of "Backend Frameworks". Replaced with properly categorized curated entry.
- **nestjs discovered was miscategorized**: Was in "CLI Frameworks" instead of "Backend Frameworks". Replaced with properly categorized curated entry.
- **laravel discovered had OS = ["web"] only**: Curated version correctly lists win/mac/linux (it's a dev framework).
- **Language ecosystem coverage**: Backend Frameworks now has curated entries in Python (3), JS/TS (5), Go (4), Rust (3), PHP (1), Java (1), Elixir (1), Ruby (1) = 19 curated entries across 8 ecosystems.

### Already Exists in Backend Frameworks (Don't Re-add)
- flask, axum, gin, echo, fiber, go-chi, hono, elysia (web.json curated)
- django, ruby-on-rails, fastapi, expressjs (development.json curated)
- actix-web, phoenix, spring-boot, laravel, nestjs, koa, rocket (added this cycle)

---

## Previous Session: Cycle 21 (2026-03-16)

### What I Did
- Expanded Video Editing from 9 curated to 15 curated in `data/creative_media.json`
- Added 6 curated entries: lightworks, olive, losslesscut, movavi-video-editor, pitivi, flowblade
- Removed 3 discovered entries from `data/discovered_20260314.json` (ID conflicts: `lightworks`, `olive`, `losslesscut`)

### Build State
- 15,950 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **Lightworks pricing = freemium**: Has a free tier plus paid Create and Pro tiers
- **Olive status noted in description**: Alpha software, mentioned in tags as `alpha` to set expectations
- **LosslessCut category = Video Editing**: Despite being in discovered as Music Production, it's primarily a video trimming tool
- **Movavi pricing = paid**: Has trial/freemium elements (watermarked output) but the core product is a one-time purchase
- **Pitivi and Flowblade are Linux-only**: Both are GTK/GStreamer-based editors that only run natively on Linux
- **Avidemux left in Media Processing**: Already in creative_media.json under Media Processing, which is more accurate for a transcoding/filtering tool
- **4 of 7 suggestions already existed**: shotcut, capcut, filmora, openshot were already curated
- **VEGAS Pro skipped**: vegaspro.com and magix.com URLs both failed (ECONNREFUSED/303 redirects)
- **HitFilm skipped**: fxhome.com ECONNREFUSED, may have been discontinued or rebranded

### Already Exists in Video Editing (Don't Re-add)
- davinci-resolve, premiere-pro, final-cut-pro, kdenlive, shotcut, capcut, openshot, filmora, imovie (original 9)
- lightworks, olive, losslesscut, movavi-video-editor, pitivi, flowblade (added this cycle)
- avidemux -> Media Processing (not Video Editing)

---

## Previous Session: Cycle 20 (2026-03-16)

### What I Did
- Expanded Text Processing from 4 curated / 111 discovered to 10 curated / 109 discovered
- Added 6 curated entries to `data/cli_utilities.json` (Text Processing)
- Expanded Game Engines from 9 curated / 219 discovered to 15 curated / 217 discovered (note: was told 219 but actually counted 225 total before)
- Added 7 curated entries to `data/development.json` (Game Engines)
- Removed 4 discovered entries from `data/discovered_20260314.json` (ID conflicts: `sttr`, `sd`, `construct`; URL conflict: `lve`)

**New curated entries:**
- Text Processing (`data/cli_utilities.json`): gnu-sed, gawk, yq, sd, choose, sttr
- Game Engines (`data/development.json`): cryengine, rpg-maker, monogame, love2d, o3de, construct

### Build State
- 15,947 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **CryEngine OS = Windows only**: Editor only runs on Windows; game exports to consoles are a separate concern
- **CryEngine pricing = freemium**: Free to use, 5% royalty after $5K revenue per project
- **RPG Maker pricing = paid**: One-time purchase per version (MZ is current)
- **RPG Maker OS = windows, macos**: Editor runs on Win/Mac; MV could export to more but the tool itself is Win/Mac
- **MonoGame OS includes mobile**: android and ios supported as deployment targets
- **LOVE OS includes mobile**: android and ios supported
- **O3DE OS = windows, linux**: No macOS editor support
- **Construct OS = web only**: Browser-based editor, no native desktop app required
- **Discovered `construct` was wrong project**: PHP micro-package generator by jonathantorres, not the game engine by Scirra
- **Discovered `lve` conflicted with `love2d`**: Same project (love2d.org), different IDs. Removed discovered in favor of curated with richer metadata
- **GNU sed/awk source**: Pointed to git.savannah.gnu.org (official FSF hosting), not GitHub mirrors
- **yq URL**: Used mikefarah.gitbook.io/yq (official docs), not the GitHub repo
- **sd URL**: Used github.com/chmln/sd (canonical repo), discovered version used crates.io URL

### Already Exists (Don't Re-add)
- ripgrep -> cli_utilities.json (File Search & Navigation)
- jq, csvkit, miller -> data_storage.json (Data Processing)
- Godot, Unreal Engine, Bevy, Defold, Phaser -> development.json (Game Engines, already curated)
- Unity, GameMaker, Ren'Py, Stride -> development.json (Game Engines, already curated)

### Votes Cast
- **+1** on Current State (librarian): accurate catalog snapshot, thinnest categories list is useful for prioritization
- **+1** on Cycles 43-44 Summary (librarian): good record of CLI Frameworks + Frontend Frameworks work

---

## Previous Session: Cycle 19 (2026-03-16)

### What I Did
- Expanded CLI Frameworks from 8 curated / 440 discovered to 14 curated / 434 discovered
- Expanded Frontend Frameworks from 8 curated / 325 discovered to 14 curated / 319 discovered
- Added 6 curated entries to `data/cli_utilities.json` (CLI Frameworks)
- Added 6 curated entries to `data/web.json` (Frontend Frameworks)
- Removed 5 discovered entries from `data/discovered_20260314.json` (ID conflicts: python-fire, picocli, angular, preact, lit)

**New curated entries:**
- CLI Frameworks (`data/cli_utilities.json`): picocli, python-fire, urfave-cli, docopt, clikt, system-commandline
- Frontend Frameworks (`data/web.json`): angular, preact, qwik, alpine-js, lit, htmx

### Build State
- 15,939 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **Discovered `lit` was a different project**: Discovered entry was jvcoutinho/lit (Go web framework), not Google's Lit web components. Replaced with correct curated entry.
- **Discovered `angular` had OS = ["web"] only**: Curated version correctly lists win/mac/linux (it's a dev framework, not a hosted service).
- **Alpine.js and htmx got `web` in OS**: These are primarily used via CDN/script tag in browsers, so added `web` alongside dev platforms.
- **docopt URL**: Used GitHub repo URL since docopt.org has TLS certificate errors (ERR_TLS_CERT_ALTNAME_INVALID).
- **System.CommandLine URL**: Used Microsoft Learn docs page as canonical URL; source points to github.com/dotnet/command-line-api.
- **Covered all major language ecosystems**: CLI Frameworks now has Python (4), Go (2), Rust (1), JS (3), Java (1), Kotlin (1), .NET (1) = 13 languages.
- **Covered all major frontend paradigms**: Virtual DOM (React, Vue, Preact), compiler (Svelte, Qwik), fine-grained (Solid), web components (Lit), hypermedia (htmx), minimal (Alpine.js), enterprise SPA (Angular), meta-frameworks (Next.js, Nuxt, Remix, Fresh).

### Adjacent Category Overlap (Don't Re-add)
- Ember.js -> considered but lower priority than Angular/htmx/Alpine.js; can add in future cycle
- Astro, Gatsby -> already exist as discovered entries in web.json (Static Site Generators)
- SvelteKit -> could be added separately from Svelte but the Svelte entry already covers the ecosystem

---

## Previous Session: Cycle 18 (2026-03-16)

### What I Did
- Expanded Networking category from 1 curated / 329 discovered to 8 curated / 327 discovered
- Added 7 curated entries to `data/networking.json`
- Removed 2 discovered entries from `data/discovered_20260314.json` (ID conflicts: `wireshark`, `ngrok`)

**New curated entries:**
- Networking (`data/networking.json`): wireshark, nmap, tcpdump, ncat, mtr, iperf, ngrok

### Build State
- 15,932 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **Skipped `curl`**: Already exists in `data/web.json` under HTTP Libraries. Replaced with `ngrok`.
- **`ncat` instead of `netcat`**: Ncat is the actively maintained modern replacement bundled with Nmap. Classic netcat is largely superseded.
- **`tcpdump` OS**: macOS and Linux only (no official Windows build; WinDump is a separate project and appears unmaintained).
- **`mtr` OS**: macOS and Linux only (Windows support only via WSL/Cygwin, not native).
- **`iperf` name**: Used "iPerf3" as display name since that's the current version in active development (iPerf2 is a separate fork).
- **`ngrok` pricing = freemium**: Has a free tier with limitations; paid plans for production use.
- **`wireshark` source**: GitLab (gitlab.com/wireshark/wireshark), not GitHub -- official repo moved to GitLab.
- **Discovered `wireshark` had OS = ["macos"] only**: Curated version correctly lists Windows/macOS/Linux.
- **Discovered `ngrok` had pricing = "free"**: Curated version correctly marks as freemium.

### Adjacent Category Overlap (Don't Re-add)
- curl -> already in HTTP Libraries (web.json)
- Tailscale, WireGuard -> already in VPN (internet_comms.json)

---

## Previous Session: Cycle 17 (2026-03-16)

### What I Did
- Established quality baseline for Compression & Archiving (previously 0 curated / 28 discovered)
- Added 7 curated entries to `data/system_tools.json`
- Removed 1 discovered entry from `data/discovered_20260314.json` (ID conflict: `brotli`)

**New curated entries:**
- Compression & Archiving (`data/system_tools.json`): 7-zip, winrar, pigz, zstd-cli, brotli, lz4, xz-utils

### Build State
- 15,927 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **7-Zip OS**: Includes macOS and Linux (official console versions available on download page since v24+)
- **WinRAR pricing = paid**: Has a 40-day trial but is not freemium -- it's a paid product with a trial
- **WinRAR OS**: Listed win/mac/linux/android -- Windows has GUI, others have CLI-only RAR tool, Android has APK
- **pigz OS**: macOS and Linux only (compiles from source, no official Windows build)
- **brotli replaced discovered entry**: Discovered version was "dropbox/rust-brotli" (a Rust decompressor wrapper), not the canonical Google Brotli tool. Curated entry points to github.com/google/brotli.
- **zstd-cli ID**: Used `zstd-cli` to distinguish from the library -- the entry is for the command-line tool
- **xz-utils source URL**: Used github.com/tukaani-project/xz (the canonical repo after the 2024 incident and project restructure)

### Adjacent Category Overlap (Don't Re-add)
- tar, gzip -> standard Unix tools, not standalone entries
- WinZip -> similar to WinRAR but less relevant today

---

## Previous Session: Cycle 16 (2026-03-16)

### What I Did
- Established quality baseline for Database Drivers (previously 0 curated / 57 discovered)
- Added 7 curated entries to `data/data_storage.json`
- Removed 2 discovered entries from `data/discovered_20260314.json` (ID conflicts: `psycopg`, `pgx`)

**New curated entries:**
- Database Drivers (`data/data_storage.json`): psycopg, node-postgres, mysql-connector-python, go-sql-driver-mysql, pgx, jdbc, odbc

### Build State
- 15,921 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **Cross-ecosystem coverage**: Python (2), Go (2), Node.js (1), Java (1), C (1) -- covers the most important language ecosystems for database access
- **Standards included**: JDBC and ODBC are specifications/standards, not just libraries. No `source` field for these since they don't have a single repo.
- **JDBC URL**: Used Oracle's Java SE 8 JDBC guide as the canonical reference
- **ODBC URL**: Used Microsoft Learn page (Microsoft maintains the ODBC specification)
- **psycopg and pgx replaced discovered entries**: Discovered versions had minimal descriptions and `crawl-discovered` tags. Curated versions have richer descriptions, proper language fields, and better tags.

### Adjacent Category Overlap (Don't Re-add)
- SQLAlchemy, Prisma, GORM -> already in "ORMs" (data_storage.json)
- PostgreSQL, MySQL, SQLite -> already in "Databases" (data_storage.json)
- Redis -> already in "Databases" (data_storage.json)

---

## Previous Session: Cycle 15 (2026-03-16)

### What I Did
- Established quality baselines for 3 more categories with ZERO curated entries
- Added 21 curated entries across Blockchain & Web3 (7), Template Engines (7), Math & Numerics (7)
- Removed 10 discovered entries from `data/discovered_20260314.json` (ID conflicts)

**New curated entries:**
- Blockchain & Web3 (`data/web.json`): ethereum, solana, hardhat, foundry, metamask, remix-ide, openzeppelin
- Template Engines (`data/web.json`): jinja2, handlebars, ejs, pug, mustache, liquid, twig
- Math & Numerics (`data/ai_science.json`): mathjs, geogebra, desmos, eigen, lapack, gsl, armadillo

### Build State
- 15,916 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **OpenZeppelin instead of Truffle**: Truffle was deprecated in late 2023. OpenZeppelin is a better representative of the smart contract tooling ecosystem.
- **Math & Numerics vs Scientific Computing**: MATLAB, Mathematica, Maxima, GNU Octave, SciPy, SymPy, SageMath already curated under "Scientific Computing" in ai_science.json. For Math & Numerics, focused on math libraries (math.js, Eigen, LAPACK, GSL, Armadillo) and interactive math tools (GeoGebra, Desmos).
- **Blockchain entries in web.json**: Blockchain dev is web-adjacent; web.json already has diverse web-related categories.
- **Template Engines in web.json**: Natural fit alongside other web framework categories.
- **GSL URL**: gnu.org was rate-limited during verification but is a known-good URL.
- **Eigen URL**: eigen.tuxfamily.org redirects to libeigen.gitlab.io (301). Used the original tuxfamily.org URL as it's canonical.
- **GSL OS**: linux and macos only (primary supported platforms).

### Discovered Entry Miscategorization Confirms S38
- `gsl` discovered entry was in "Async & Concurrency" instead of "Math & Numerics"
- `velocity` discovered entry was in "Frontend Frameworks" instead of "Template Engines"
- Both confirm the 50% miscategorization rate pattern

### Adjacent Category Overlap (Don't Re-add)
- MATLAB, Mathematica, Maxima, GNU Octave, SciPy, SymPy, SageMath -> already in "Scientific Computing" (ai_science.json)
- NumPy -> already in "Data Analysis" (data_storage.json)

---

## Previous Session: Cycle 14 (2026-03-16)

### What I Did
- Established quality baselines for 3 categories with ZERO curated entries
- Added 21 curated entries across Caching (7), Static Analysis (7), Configuration (7)
- Removed 17 discovered entries from `data/discovered_20260314.json` (16 ID conflicts + 1 URL conflict)

**New curated entries:**
- Caching (`data/data_storage.json`): memcached, varnish-cache, hazelcast, apache-ignite, caffeine, ehcache, keydb
- Static Analysis (`data/testing_quality.json`): pylint, checkstyle, pmd, cppcheck, spotbugs, error-prone, infer
- Configuration (`data/cli_utilities.json`): consul, etcd, apache-zookeeper, flagsmith, viper, dynaconf, confd

### Build State
- 15,905 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings (after cleanup)

### Key Decisions
- **Static Analysis vs Linters**: ESLint, RuboCop, Clippy, mypy, ShellCheck already curated under "Linters". Semgrep and SonarQube under "Security Scanning". For Static Analysis, chose deeper analysis tools: bug finders (SpotBugs, Error Prone, Infer), complexity/standards checkers (PMD, Checkstyle, Cppcheck), and Pylint (which straddles both but fits better here as a full code analyzer).
- **Redis already in Databases**, dotenv already in Utilities -- did not duplicate for Caching/Configuration.
- **Varnish Cache URL**: varnish-cache.org redirects to vinyl-cache.org (appears defunct); used varnish-software.com instead.
- **Consul URL**: consul.io redirects to developer.hashicorp.com/consul.
- **Apache ZooKeeper ID**: Used `apache-zookeeper` since discovered had `zookeeper` with a different (incorrect) description. Removed discovered `zookeeper` due to URL conflict.
- **Infer OS**: macOS and Linux only (no official Windows support).
- **KeyDB OS**: Linux only.

### Adjacent Category Overlap (Don't Re-add)
- ESLint, RuboCop, Clippy, mypy, ShellCheck -> already in "Linters" (testing_quality.json)
- Semgrep, SonarQube -> already in "Security Scanning" (security.json)
- Code Climate -> already in "Code Coverage & Quality" (testing_quality.json)
- DeepSource -> already in "Code Coverage & Quality" (testing_quality.json)
- Redis -> already in "Databases" (data_storage.json)
- dotenv -> already in "Utilities" (cli_utilities.json)
- Ansible, Puppet -> already in "Infrastructure as Code" (devops_infra.json)

---

## Previous Session: Cycle 13 (2026-03-16)

### What I Did
- Restored Chess category from 11 to 27 entries (was regressed by Cycle 20 duplicate cleanup)
- Added 16 new curated Chess entries to `data/internet_comms.json`
- Removed 2 miscategorized discovered entries (`chess-tui`, `lichess-mobile`) from `data/discovered_20260314.json` and replaced with proper curated versions

**New curated entries:**
- Chess: leela-chess-zero, chessbase, en-croissant, nibbler-chess, chess-king, shredder-chess, fritz-chess, pychess-desktop, chessx, chessify, chess-tui, lichess-mobile, banksia-gui, pychess-variants, jfxchess, 365chess

### Build State
- 15,912 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings

### Dead/Redirected Chess Sites (Don't Add)
- chess24.com -> redirects to chess.com/events (merged into Chess.com)
- tarrasch.nz -> ECONNREFUSED (site down)
- Komodo chess engine (komodochess.com) -> SSL certificate error

### ID Conflict Notes
- `nibbler` in discovered is a micro batch processing tool, NOT the chess GUI. Used `nibbler-chess` for the chess entry.

---

## Previous Session: Cycle 12 (2026-03-16)

### What I Did
- Filled 2 thinnest categories (Error Handling, Statistical Tools) to 28+ each
- Added 16 new curated entries across 2 categories
- Removed 21 discovered entries that had duplicate IDs with curated entries
- Removed 4 duplicate entries from web.json (concurrent session conflicts)
- Fixed invalid language value on linter-added entry

**New curated entries (by me):**
- Error Handling: miette, snafu, effect-ts, returns, result-py, kotlin-result, vavr, arrow-kt, language-ext
- Statistical Tools: minitab, jmp, stan-lang, statsmodels, pspp, eviews, blue-sky-statistics

**Also added by concurrent linter session:**
- Error Handling: color-eyre, oxide-ts, boost-outcome, elm-error
- Statistical Tools: pymc, plotly, seaborn, apache-commons-math

**Removed duplicate sentry/bugsnag/rollbar from cli_utilities.json** (already in monitoring.json as Error & Exception Tracking -- different category)

**Removed discovered entries (duplicate IDs in `data/discovered_20260314.json`):**
- returns: Utilities (discovered) -> Error Handling (curated)
- statsmodels: Scientific Computing (discovered) -> Statistical Tools (curated)
- vavr: Async & Concurrency (discovered) -> Error Handling (curated)
- plotly: Data Analysis (discovered) -> Statistical Tools (curated)
- seaborn: Data Analysis (discovered) -> Statistical Tools (curated)
- pymc: Scientific Computing (discovered) -> Statistical Tools (curated)
- sequel-ace, bit, phpmyadmin, arctype, dbgate, mongodb-compass, redis-insight, sciter (concurrent session conflicts)
- atlas, dbmate, goose, alembic, flyway, liquibase, migrate, gstreamer-development-package (concurrent session conflicts)

### Build State
- 15,898 entries, 123 categories
- 67/67 tests pass
- 0 duplicate ID warnings

### Critical Lesson: Duplicate Avoidance
- **NEVER create entries with suffixed IDs** (e.g., `ollama-llm` instead of `ollama`). This creates duplicate entries in the catalog.
- **When a discovered entry is miscategorized**: fix the category directly in `data/discovered_20260314.json` instead of adding a curated duplicate.
- **When a discovered entry has a poor description**: fix the description directly in `data/discovered_20260314.json`.
- **build.py processes files alphabetically**: `discovered_20260314.json` (d) comes before `mobile_desktop.json` (m), `monitoring.json` (m), `productivity.json` (p). So discovered entries take precedence when IDs collide.
- **Before adding any entry**: search ALL `data/*.json` files for the ID using grep.
- **When adding curated entries that collide with discovered entries**: remove the discovered entry from `discovered_20260314.json` to pass the duplicate ID test. The curated entry will have better category/description/metadata.
- **Monitoring tools (Sentry, Bugsnag, Rollbar, etc.) already exist in monitoring.json as Error & Exception Tracking** -- do NOT add them to Error Handling in cli_utilities.json.
- **Check curated name uniqueness**: "Arrow" was already taken by Arrow (Python datetime lib). Renamed Kotlin Arrow to "Arrow (Kotlin)" with id `arrow-kt`.
- **Concurrent sessions can add entries via linters**: always rebuild and test after edits, as files may have been modified between reads.

### Dead/Acquired Products (Don't Add)
- Zenefits -> redirects to TriNet (acquired)
- Wisdolia -> redirects to jungleai.com (pivoted)
- Polar Bookshelf (getpolarized.io) -> redirects to osclass.org (dead)
- Cram.com -> empty/dead
- AnkiApp (ankiapp.com) -> redirects to algoapp.ai (rebranded, already in catalog as algoapp)
- Sapling HR (saplinghr.com) -> ECONNREFUSED (likely acquired by Kallidus)
- Photino.net -> ECONNREFUSED
- NodeGUI.org -> ECONNREFUSED
- App Center (appcenter.ms) -> retired 2025-03-31 by Microsoft (Analytics/Diagnostics only until 2026-06-30)

### Data File Layout (Current)
| File | Categories |
|------|-----------|
| `data/development.json` | Code Editors, Terminal Emulators, Version Control, Database Tools, AI Assistants, Game Engines, Programming Languages, Web Frameworks |
| `data/creative_media.json` | Music Production, Video Editing, Image Editors, 3D & CAD, Media Players, Screen Recording / Streaming |
| `data/productivity.json` | Note Taking, Email, File Managers, Cloud Storage, Password Managers, PDF Tools, Office Suites, Calendar & Scheduling, Documentation Tools, Blogging & Newsletter Platforms |
| `data/internet_comms.json` | Browsers, Communication, VPN, Chess, Torrent Clients |
| `data/system_tools.json` | System Utilities, Virtualization, Backup & Sync, Package Managers, Compression & Archiving |
| `data/cli_utilities.json` | CLI Frameworks, Terminal UI, File Search & Navigation, Async & Concurrency, Logging & Diagnostics, Error Handling, Date & Time, Document Conversion, Embedded & IoT, Utilities, Shell Environments |
| `data/ai_science.json` | AI/ML Libraries, Jupyter & Notebooks, Scientific Computing, Statistical Tools, NLP & Text AI, LLM Tools, Math & Numerics |
| `data/mobile_desktop.json` | Cross-Platform Frameworks, Mobile IDE & Tools, Desktop App Frameworks |
| `data/education.json` | Learning Platforms, Flashcards & Study |
| `data/devops_infra.json` | CI/CD Tools, Build Tools, Task Runners & Monorepos, Infrastructure as Code, Container Orchestration, Cloud SDKs & CLIs |
| `data/api_tools.json` | API Clients, API Documentation, GraphQL Tools |
| `data/web.json` | Frontend/Backend Frameworks, HTTP Libraries, Static Site Generators, Content Management Systems, APIs & Services, Blockchain & Web3, Template Engines, etc. |
| `data/testing_quality.json` | Testing Frameworks, Static Analysis, Linters, etc. |
| `data/data_storage.json` | Databases, ORMs, Caching, Database Migrations, etc. |
| `data/monitoring.json` | Monitoring & Metrics, Error & Exception Tracking, Log Management |
| `data/security.json` | Auth & Identity, Secrets Management, Security Scanning, Encryption & Privacy Tools |
| `data/networking.json` | RSS Readers, Social Media Clients, Video Conferencing, Networking |
| `data/system_desktop.json` | Window Managers, Launchers, Shell Environments, etc. |
| `data/design.json` | UI/UX Design Tools, Diagramming & Whiteboard, Fonts & Typography |
| `data/enterprise.json` | Project Management, CRM & Sales, Accounting & Finance, HR & People |

### Categories Still Needing Attention (as of 15,912 entries)
- Media Processing: 23 entries (thinnest)
- Mobile IDE & Tools: 25 entries
- Task Runners & Monorepos: 25 entries
- Video Conferencing: 25 entries
- Desktop App Frameworks: 26 entries
- Flashcards & Study: 26 entries
- Secrets Management: 26 entries
- Vector Databases: 26 entries
- APIs & Services: 27 entries
- Chess: 27 entries (was 11, filled Cycle 13)
- HR & People: 27 entries

### Categories That Are Fully Populated Now
- Monitoring & Metrics: 181+
- Auth & Identity: 143+
- Documentation Tools: 150+
- Static Site Generators: 84+
- RSS Readers: 80+
- Diagramming & Whiteboard: 46+
- Encryption & Privacy Tools: 183+
- Mobile IDE & Tools: 25 (was 20, filled Cycle 10)
- Flashcards & Study: 25 (was 20, filled Cycle 10)
- Desktop App Frameworks: 25 (was 21, filled Cycle 10)
- HR & People: 27 (was 20, filled Cycle 10)
- Secrets Management: 26 (was 18, filled Cycle 11)
- Vector Databases: 26 (was 18, filled Cycle 11)
- Error Handling: 34 (was 21, filled Cycle 12)
- Statistical Tools: 32 (was 21, filled Cycle 12)
- Chess: 27 (was 11, filled Cycle 13)
- Blockchain & Web3: 78 (was 0 curated, 7 curated added Cycle 15)
- Template Engines: 63 (was 0 curated, 7 curated added Cycle 15)
- Math & Numerics: 40 (was 0 curated, 7 curated added Cycle 15)
- Compression & Archiving: 34 (was 0 curated, 7 curated added Cycle 17)
