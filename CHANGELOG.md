# Changelog

## 1.0.0.dev0 — unreleased

First build of **InfluenceSignal**, the Signal suite's influencer campaign manager for the Norwegian market. Developed under the working name CreatorSignal; renamed before any release (see *Naming*).

### Application

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
