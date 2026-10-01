# Contributing

Contributions should preserve CreatorSignal's boundaries:

- **Not legal advice.** Never label a post or campaign "compliant". Every screen that shows compliance carries "Checklist support, not legal advice."
- **Sourced rules only.** A new or changed rule in `src/creatorsignal/rules/*.yaml` needs an official `https://` source and, where possible, a quoted passage with the date it was fetched. If a legal detail is unclear, write `TODO(verify)` instead of guessing.
- **No causal claims** from code redemptions or tracked clicks.
- **Local-first.** No telemetry, accounts, external AI calls, scraping or social-network APIs.
- **Architecture.** Logic and storage live in `src/creatorsignal/` and must not import Streamlit; SQLite stays inside `storage.py`. `tests/test_architecture.py` enforces this.

Before submitting a change:

```bash
python -m pytest
python -m ruff check .
python -m build
```

Use fictional test data only (handles starting with `demo_`, e-mail at `example.com`). Never commit real creator data or a `data/` folder.
