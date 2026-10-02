# Contributing

Contributions should preserve Influence Signal's boundaries:

- **Not legal advice.** Never label a post or campaign "compliant". Every screen that shows compliance carries "Checklist support, not legal advice."
- **Sourced rules only.** A new or changed rule in `src/influencesignal/rules/*.yaml` needs an official `https://` source and, where possible, a quoted passage with the date it was fetched. If a legal detail is unclear, write `TODO(verify)` instead of guessing.
- **No causal claims** from code redemptions or tracked clicks.
- **Local-first.** No telemetry, accounts, external AI calls, scraping or social-network APIs.
- **Architecture.** Logic and storage live in `src/influencesignal/` and must not import Streamlit, except `src/influencesignal/ui/`, which holds the UI: `pages/` (one module per page with a `render()` function), `shell.py`, `app.py` and the Signal Hub entry point `render()` in `__init__.py`. Do not edit the synced `ui/signal_theme.py`, `ui/signal_font.py` or `ui/assets/marks/` here. Streamlit code otherwise lives only in the standalone `app.py`. SQLite stays inside `storage.py`. `tests/test_architecture.py` enforces this.
- **Signal Hub contract.** Every session-state, form and widget key goes through `k()` (prefix `influence:`); `render()` never calls `st.set_page_config`, `st.navigation`, `st.Page`, `st.logo` or `st.stop`. With `SIGNAL_HUB=1` the app must not write files, open a local workspace or make network requests. `tests/test_hub_contract.py` enforces this.
- **Look and feel.** Use the shared Signal theme (`from influencesignal.ui import signal_theme as sig`) rather than pasted CSS or hard-coded colours.

Before submitting a change:

```bash
python -m pytest
python -m ruff check .
python -m build
```

Use fictional test data only (handles starting with `demo_`, e-mail at `example.com`). Never commit real creator data or a `data/` folder.
