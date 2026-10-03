# Changelog

## [1.1.0] - 2026-10-03

### Larger datasets

- **Larger datasets: no built-in data limits when run locally** (was 20 MB, 50,000 rows, 100 columns and 100 MB of expanded XLSX). On your own computer, a local Signal Hub or an internal company deployment the file size, rows and columns are limited only by memory; running out of memory (including Arrow allocation failures) is reported as a plain message. A public demo (`SIGNAL_PUBLIC=1`) keeps the old values as demo caps, all in the new `influencesignal.limits` module, and its messages say the downloaded app has no such limit.
- CSV uploads are parsed straight from the uploaded bytes into Arrow-backed text (no decoded copy of the file, a fraction of the memory of Python strings). `pyarrow` is now a declared dependency (it already came with Streamlit).
- Creator and results validation is vectorized column by column, with the same checks and messages; plain numeric columns take one Arrow cast and only Norwegian-formatted cells (spaces, decimal commas, %, NOK/kr) take the clean-up path. Problem lists show the first 25 with a count of the rest instead of thousands of lines; the old quadratic duplicate check on `deliverable_id` is gone.
- Imports are batched in one transaction: `Store.import_creators` converts 250,000 rows at a time and rolls everything back on a problem; the new `Store.import_results` applies a results table with blank cells left unchanged (as before). Measured on this machine: 5 million creators (555 MB) read in 15 s, validated in 20 s and imported in 39 s at 4.5 GB peak memory; 5 million results rows (190 MB) in 8 s, 6 s and 13 s at 2.8 GB.
- Screens stay responsive with big workspaces: upload previews and the creator and per-creator tables show the first 1,000 rows with a note, creator pick lists show the first 2,000 matches (the shortlist picker gets a name search for large rosters), and the results chart shows the best 40 creators with a note. Every row is still validated, imported and exported.
- Launchers accept `INFLUENCESIGNAL_MAX_UPLOAD_MB` (default 10000) for `--server.maxUploadSize`; the Dockerfile sets `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000`. Hub mode (`SIGNAL_HUB=1`) is unchanged.
- New `tests/test_large_data.py`: local mode accepts a roster above the demo row and column caps, `SIGNAL_PUBLIC=1` enforces every cap with its demo message, out-of-memory becomes a plain message, the summarized problem list, blank-preserving bulk results import, and the launcher/Docker/config cap.

### Suite

- Suite: Rival, Reach, Learn and Blueprint Signal added to the suite table; the synced Signal config raises `maxUploadSize` to 10000.

### English

- All app text is in English. The checklist shows English labels and questions only (the Norwegian label and question columns are gone from the rules file, the checklist, *Settings & data* and the report); source quotes stay verbatim in Norwegian and now carry an unofficial English translation (`quote_en`), shown first with the original below it. Law, regulator and source names keep their Norwegian name with an English gloss on first use (for example the Marketing Control Act (markedsføringsloven)). "Region (fylke)" is now "Region (county)" and the welcome pill reads "advertising-label checklist". The XLSX `rules_and_sources` sheet has `label`, `quote_english_unofficial` and `quote_original_norwegian` instead of `label_no`, `label_en` and `quote`. The demo stays Norwegian (names, campaigns, post texts), with a note that the tool is built for the Norwegian market. Checklist support, not legal advice.

## [1.0.0] - 2026-10-02

First release of **Influence Signal**, the Signal suite's local-first influencer campaign manager for the Norwegian market: creator roster, campaigns, an eight-stage pipeline, deliverables with tracked links and codes, a sourced Norwegian advertising-label checklist with a Paid gate, results at cost per result, and an XLSX + one-page HTML report. Checklist support, not legal advice.

### Signal Hub

- `influencesignal.ui` exposes `APP_INFO` and `render()`, which draws the whole app on the current page (theme, sidebar lockup, a namespaced page radio over the same page functions the standalone app uses, active-campaign selector, masthead, the selected page with the friendly error, footer). It never calls `st.set_page_config`, `st.navigation`, `st.Page`, `st.logo` or `st.stop`.
- The pages moved from `pages/` to `src/influencesignal/ui/pages/` and the shared shell to `ui/shell.py`, so a packaged install has them; `pages/` is gone. The standalone `app.py` keeps its `st.navigation` menu, URL paths and `?page=` deep links over the same page list.
- Every session-state, form and widget key is namespaced with the slug (`influence:…`) through one `k()` helper.
- Hub mode (`SIGNAL_HUB=1`): each session works in a private in-memory SQLite database seeded with the fictional demo (`Store(":memory:")`). Nothing is read from or written to disk, an existing local workspace is never opened, the `INFLUENCESIGNAL_RULES` override is ignored, and the database-folder settings are hidden with a note explaining why. Welcome, Settings and the sidebar say the Hub workspace is in memory only. Standalone behaviour is unchanged.
- Streamlit and Plotly moved to the `ui` extra (also in `test`); `requirements.txt` still installs everything.
- New `tests/test_hub_contract.py`: `APP_INFO`, Streamlit/Plotly only under `ui/`, a fresh-interpreter core import, `render()` from the packaged files alone, namespaced keys at runtime and in the source, and hub-mode tests (temporary cwd and home stay empty, an existing local database is neither read nor changed, socket/urllib/requests/feedparser calls are refused, workspaces are per session, database settings hidden).

### Signal brand refresh

- Display name is now **Influence Signal** (with a space) in the UI, page title, masthead, footer, report, error messages, launchers, README and docs. Technical identifiers are unchanged (`influencesignal`, `INFLUENCESIGNAL_*`, `influencesignal.db`, asset slugs).
- The pasted CSS, hand-written lockup, masthead, hero, cards, page headers, notes and footer are replaced by the shared Signal theme (`src/influencesignal/ui/signal_theme.py`, synced from Signal Hub): Organic look, Figtree, Market family colour (#728157). The sidebar logo is the new mark; the favicon is the 64 px mark. Demo, legal and boundary notes use `sig.note`; the "Checklist support, not legal advice." disclaimer stays on every compliance screen and in the footer.
- The results chart uses the per-app Signal Plotly template (`sig.chart`) and the family highlight colour; creator names are no longer clipped. The printable HTML report uses the Organic Market tokens instead of the old teal/coral palette.
- `.streamlit/config.toml` is the synced Signal config (Market `primaryColor`, cream background).
- Assets: synced banner (`influencesignal-banner.png`), social preview and marks (`influencesignal-mark.svg`, `-32/64/512.png`); the old `influencesignal-banner.svg` and `influencesignal-lockup-dark.svg` are removed. README screenshots are retaken.
- README follows the Signal README template (sections in suite order, Market badges, "Where this fits in Signal" table, references to the official sources, suite footer). Content, limits and honesty statements are kept.
- Architecture rule amended: no Streamlit under `src/influencesignal/` **except `src/influencesignal/ui/`** (guard test, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, PR template). `influencesignal.ui` ships its marks as package data.
- Added GitHub issue templates (bug report, feature request, config) and brand tests (theme shell, no old palette, display name, synced config and assets, README order, issue templates).

### Application

Developed under the working name CreatorSignal; renamed before any release (see *Naming*).

- Creator roster with platform handles (Instagram, TikTok, YouTube, Snapchat), followers, engagement rate, niche tags, county (the 15 fylker from 2024), contact, rate card and notes; validated CSV/XLSX import and CSV export.
- Campaigns with brand, goal, budget (NOK), dates, brief, deliverables template, landing page and category.
- Eight-stage pipeline per campaign with a select box per card and a stage log.
- Deliverables with platform, format, due date, fee, discount code and tracked links in one UTM scheme (`utm_medium=influencer`).
- Norwegian advertising checklist from an editable YAML file (`rules/no.yaml`): advertising identified at the start, recommended wording, every story labelled, retouched-advertising mark, restricted-category flag. Each rule quotes an official source fetched on 2026-10-01.
- Paid gate: a creator cannot move to *Paid* or *Reported* until each deliverable is published and its checklist is complete, or an override reason of at least 15 characters is written. Enforced in the storage layer, not only in the UI.
- Results by hand or CSV; CPM, CPC, cost per redemption and ROAS per creator and campaign, with plain-language limits (no causal claims; codes leak).
- Campaign report: XLSX workbook and a one-page printable HTML summary.
- Deterministic fictional demo (brand "Fjellbrus", 25 creators, 2 campaigns, one post missing its label), preloaded on first start.
- Local SQLite workspace in a user-chosen folder; no telemetry, accounts, external AI or social-network APIs.
- Signal-suite shell, launcher (`run_app.bat`), non-root Docker image with a data volume, CI.

### Architecture

- Package under `src/influencesignal/` never imports Streamlit and exposes a public API; SQLite is confined to `storage.py`. A test enforces both.

### Legal-reference correction

- Advertising identification cites markedsføringsloven § 8 (as Forbrukertilsynet's guide does), not § 3, which has concerned documentation of claims since 1 October 2023.

### Second pass (same day)

- Retouching rule now quotes the regulation itself (FOR-2022-06-17-1114 § 1): mark in the upper left corner below filters and usernames, about 7 % of the image, on screen for the whole video; the mark contains «REKLAME» (Forbrukertilsynet guide, 18 August 2026).
- Restricted categories cite pengespilloven § 6 (gambling) and markedsføringsloven §§ 19–21 (children). Only the nicotine-products question remains `TODO(verify)`.
- Fixed: pipeline cards now escape creator names and handles (an imported name could inject HTML).
- Fixed: an unusable data folder on *Settings & data* is refused instead of locking the session out of the app.
- Fixed: editing a creator or campaign no longer turns an unknown follower count, engagement rate or budget into 0.
- The compliance page warns when a creator is already Paid or Reported but a deliverable's checklist was reopened afterwards.
- `run_app.bat` uses CRLF line endings (pinned in `.gitattributes`), as `cmd.exe` expects; verified to start the app with the demo from a fresh folder.
- Replaced Streamlit's deprecated `use_container_width`; minimum Streamlit is now 1.50 (suite verified on 1.50.0 and 1.64.0).

### Pages split (same day)

- The UI is split into `pages/` (one module per page with `render()`, shared shell in `pages/ui.py`) and wired with `st.navigation`; `app.py` is now a short entry point. The sidebar shows a logo and grouped navigation (*Campaign workflow*, *Workspace*); each page has its own URL path, and `?page=` deep links still work.
- Architecture test extended: Streamlit only in `app.py` and `pages/`, SQLite only in `storage.py` across the repo, every page exposes `render()`. App-page tests now open pages by URL and assert they landed on the right one.

### Hardening (same day)

- End-to-end UI tests: a full campaign from an empty workspace through every form to Paid, results and report; plus restricted-category editing and the confirm-guarded *Delete all data* / *Reload demo* actions.
- Nicotine question narrowed with Helsedirektoratet's guide to the tobacco advertising ban (12 May 2026): it applies in social media and to circumvention via closely connected profiles; nicotine products are still not named, so the item stays `TODO(verify)`.
- Added `run_app.command` (macOS, mirrors TrackSignal; LF line endings pinned in `.gitattributes`), `CODE_OF_CONDUCT.md` and `CITATION.cff`.
- Name screen (`docs/name-screen.md`): an active product uses the exact name "CreatorSignal" (creatorsignal.io); the name is a working title until a public name is chosen. InfluenceSignal was the cleanest alternative screened.

### Naming

- Renamed from the working name **CreatorSignal** to **InfluenceSignal**: an active product uses the exact name CreatorSignal (creatorsignal.io); the same informal screen found no product, PyPI/npm package or GitHub repository named InfluenceSignal. Not legal clearance or a trademark opinion — see `docs/name-screen.md`.
- Package `creatorsignal` → `influencesignal`; environment variables `CREATORSIGNAL_*` → `INFLUENCESIGNAL_*`; default database `data/creatorsignal.db` → `data/influencesignal.db`; assets renamed to `influencesignal-*.svg`.
