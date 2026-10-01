# Changelog

## 1.0.0.dev0 — unreleased

First build of **CreatorSignal**, the Signal suite's influencer campaign manager for the Norwegian market.

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

- Package under `src/creatorsignal/` never imports Streamlit and exposes a public API; SQLite is confined to `storage.py`. A test enforces both.

### Legal-reference correction

- Advertising identification cites markedsføringsloven § 8 (as Forbrukertilsynet's guide does), not § 3, which has concerned documentation of claims since 1 October 2023.
