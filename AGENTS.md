# AGENTS.md — Influence Signal (repo: influencer-campaigns)

You are building **Influence Signal** (package `influencesignal`), a new product in Ulrik Erlingsen's **Signal** suite
(open-source, local-first marketing tools; see sibling repos such as `brand-tracking`
= TrackSignal for house style). This repo starts empty except for this file, a README stub,
LICENSE and .gitignore. Build v1 from this brief.

> Renamed from the working name **CreatorSignal** on 2026-10-01 after a name screen found an active product with that exact name; see `docs/name-screen.md`.


## What it is

An open, local-first **influencer campaign manager for the Norwegian market**.
Free alternative to paid tools such as Upfluence, Grin and Modash for small brands,
agencies and student projects. No open-source tool on GitHub covers this (checked 2026-10-01:
only outreach bots and AI "skills" packs exist).

The Norwegian angle is the differentiator: every sponsored post carries a **compliance
checklist for Norwegian advertising rules** (advertising identification and the
retouched-advertising label), so a brand can show it ran a campaign properly.

## The question it answers

> Which creators delivered for this campaign, at what cost per result — and was every post
> correctly labelled under Norwegian rules?

## v1 scope (build this, nothing more)

1. **Creators** — roster: name, handle(s) per platform (Instagram, TikTok, YouTube, Snapchat),
   follower count, engagement rate (manual entry or CSV), niche tags, region (fylke), contact,
   rate card, notes. CSV import/export.
2. **Campaigns** — name, brand, goal (awareness / traffic / sales), budget (NOK), dates,
   brief text, deliverables template.
3. **Pipeline** per campaign — kanban stages: Shortlist → Contacted → Negotiating → Contracted
   → Content in review → Published → Paid → Reported. Drag or select-box to move.
4. **Deliverables** — per creator per campaign: platform, format (reel, story, post, video),
   due date, agreed fee (NOK), discount code, tracked link (UTM fields generated in a
   consistent scheme: `utm_source=<platform>&utm_medium=influencer&utm_campaign=<slug>&utm_content=<creator>`).
5. **Compliance checklist** per published deliverable (see section below). A deliverable cannot
   move to *Paid* until the checklist is completed or an override reason is written.
6. **Results** — manual or CSV entry: reach, views, clicks, code redemptions, revenue (NOK).
   Computed: CPM, CPC, cost per redemption, ROAS. Show per creator and per campaign with
   plain-language notes on what the numbers can and cannot say (no causal claims; codes leak).
7. **Campaign report** — export XLSX + a one-page HTML/PDF summary (creators, spend, results,
   compliance status).

Out of scope for v1: scraping social platforms, creator discovery from the web, auto-DMs,
payments, multi-user auth. Do not call any social-network API.

## Norwegian compliance checklist (configurable, not legal advice)

Store rules in `src/influencesignal/rules/no.yaml` so they can be edited without code changes.
Each rule: id, label (Norwegian + English), source URL, applies_when (e.g. image shows a body),
check type (yes/no). Seed with:

- **Advertising clearly identified** — post labelled as advertising at the start, visible
  without clicking "more" (markedsføringsloven § 3; Forbrukertilsynet guidance on labelling
  advertising in social media).
- **Label wording** — uses the wording Forbrukertilsynet currently recommends.
  *Before writing this rule, fetch Forbrukertilsynet's current guidance and quote the exact
  recommended wording and the source URL in the YAML. Do not invent wording.*
- **Retouched-advertising label** — if body shape, size or skin has been altered (filters
  included) in paid content, the standard retouching label is shown (markedsføringsloven § 2,
  in force from 1 July 2022; Prop. 134 L (2020–2021)). Verify current details before seeding.
- **Restricted categories flag** — warn if the campaign category is alcohol, gambling,
  tobacco/nicotine, or targets children; these have stricter Norwegian rules. Flag only;
  link to the source; never say "compliant".

Every screen that shows compliance must carry: *"Checklist support, not legal advice."*

## Demo data

Ship a deterministic fictional demo (seeded generator in `src/influencesignal/demo.py`):
fictional brand "Fjellbrus" (sports drink), ~25 fictional creators with Norwegian-sounding
handles that are clearly fake (e.g. `@demo_kari_trener`), 2 campaigns, mixed pipeline states,
one deliverable with a missing label so the compliance warning is visible. The demo must
represent no real person, brand or result — state this on screen and in the README.

## Stack and house style (match the other Signal repos)

- Python 3.10+, **Streamlit** app (`app.py`), package in `src/influencesignal/`, tests in `tests/`.
- No Streamlit import anywhere under `src/influencesignal/` **except `src/influencesignal/ui/`**, which holds
  the Signal theme synced from Signal Hub (`ui/signal_theme.py`, `ui/assets/marks/`; never edit the synced files).
  Streamlit code otherwise lives in `app.py` (thin standalone entry) and `src/influencesignal/ui/` (shell and pages). `tests/test_architecture.py` enforces this.
- Display name in user-facing text is **Influence Signal** (with a space); technical identifiers stay
  `influencesignal` / `INFLUENCESIGNAL_*`. Never use the old working name as a display name.
- Persistence: **SQLite** file in a user-chosen local folder (default `./data/influencesignal.db`,
  gitignored). This is a workflow tool, so unlike the analytics Signal apps it saves state.
- pandas, plotly, openpyxl, pyyaml. No telemetry, no accounts, no external AI calls.
- `pyproject.toml` (setuptools, AGPL-3.0-or-later, author "Ulrik Erlingsen"), `requirements.txt`,
  `Dockerfile`, `run_app.bat` (Windows) — mirror `brand-tracking`.
- ruff (line length 120) + pytest. Tests for: metric calculations, UTM builder, rule loading,
  "cannot mark Paid without checklist" gate, CSV import validation.
- README in the same structure as TrackSignal's: banner, badges, one-sentence promise,
  "Read this first", "Try the fictional demo in three minutes", data contract, limits.
- Also add: CHANGELOG.md, SECURITY.md, PRIVACY.md (state that creator contact data stays local;
  the user is the data controller under GDPR), CONTRIBUTING.md.

## Definition of done for v1

- `run_app.bat` starts the app with the demo preloaded.
- All seven v1 features work on the demo; `pytest` and `ruff check` pass.
- Compliance rule texts quote a fetched official source URL.
- README screenshots in `assets/`.

## Working rules

- Ulrik commits and pushes from **GitHub Desktop** himself; you do not push.
- Keep commits small and logical; write a short summary of what changed at the end of each session.
- Norwegian UI labels are optional in v1; English UI with Norwegian rule texts is fine.
- When unsure about a legal detail, leave a `TODO(verify)` and say so; never guess.
