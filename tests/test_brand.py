"""Signal brand: the shared theme, display name, family colour and synced assets."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from influencesignal import DISCLAIMER, __version__

ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
UI = ROOT / "src" / "influencesignal" / "ui"
OLD_COLOURS = ("#173c3a", "#d95b40", "#83d2b4", "#f2c66d", "#17322e", "#102c2a", "#f8f5ed", "#59716c")


def _ui_sources() -> str:
    synced = {"signal_theme.py", "signal_font.py"}  # synced from Signal Hub; they hold the shared CSS
    files = [ROOT / "app.py", *sorted(path for path in UI.rglob("*.py") if path.name not in synced)]
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("INFLUENCESIGNAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("INFLUENCESIGNAL_NO_DEMO", raising=False)


def test_shared_signal_shell_renders() -> None:
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "sg-mast" in body  # shared Signal masthead
    assert "sg-hero" in body  # welcome hero
    assert "sg-foot" in body  # shared Signal footer
    assert "SHORTLIST → PUBLISH → CHECK → REPORT" in body
    assert f"Influence Signal v{__version__}" in body
    assert DISCLAIMER in body
    assert "Part of the Signal suite" in body
    assert "AGPL-3.0-or-later" in body


def test_app_uses_shared_signal_theme_instead_of_pasted_styles() -> None:
    standalone = (ROOT / "app.py").read_text(encoding="utf-8")
    sources = _ui_sources()
    assert "st.set_page_config(**sig.page_config(KEY" in standalone
    assert "sig.apply(KEY)" in standalone
    assert 'NS = "influence"' in (UI / "shell.py").read_text(encoding="utf-8")
    assert "from influencesignal.ui import signal_theme as sig" in sources
    assert "<style>" not in sources
    assert "lockup-dark" not in sources
    for old_colour in OLD_COLOURS:
        assert old_colour not in sources.lower(), old_colour
        assert old_colour not in (ROOT / "src" / "influencesignal" / "report.py").read_text(encoding="utf-8").lower()
    # Charts use the per-app Plotly template (via sig.chart), not the process-wide default or Streamlit's theme.
    results = (UI / "pages" / "results.py").read_text(encoding="utf-8")
    assert "sig.chart(KEY, figure" in results
    assert "st.plotly_chart" not in sources


def test_display_name_has_a_space_in_user_facing_text() -> None:
    texts = _ui_sources() + "".join(
        (ROOT / "src" / "influencesignal" / name).read_text(encoding="utf-8") for name in ("report.py", "errors.py")
    )
    assert "InfluenceSignal" not in texts
    assert "Creator" + " Signal" not in texts
    assert "Influence Signal" in texts


def test_synced_theme_assets_and_config() -> None:
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'primaryColor = "#728157"' in config  # Signal Market family, 600 step
    assert "gatherUsageStats = false" in config
    assert '"influencesignal.ui" = ["assets/marks/*"]' in pyproject
    for size in ("", "-32", "-64"):
        assert (UI / "assets" / "marks" / f"influencesignal-mark{size}.{'svg' if not size else 'png'}").exists()
    assert (UI / "__init__.py").exists()


def test_readme_matches_suite_information_architecture() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Signal README template order (sections without content for this app are left out, never reordered).
    sections = [
        "## Read this first",
        "## Scope",
        "## Try the demo in three minutes",
        "## Data contract",
        "## Methods",
        "## Decision statuses",
        "## Exports",
        "## Run locally",
        "## Privacy",
        "## Development",
        "## Where this fits in Signal",
        "## References",
        "## Originality and license",
    ]
    positions = [readme.find(f"\n{heading}\n") for heading in sections]
    assert all(position >= 0 for position in positions), dict(zip(sections, positions))
    assert positions == sorted(positions)
    assert readme.startswith('<p align="center">\n  <img src="assets/influencesignal-banner.png"')
    assert "influencesignal-banner.svg" not in readme
    assert "Signal-Market-728157" in readme  # family badge in the Market 600 colour
    assert "github.com/UlrikErlingsen/influencer-campaigns/actions" in readme  # tests badge
    assert "**Influence Signal**" in readme
    assert '<img src="assets/influencesignal-mark-64.png"' in readme  # suite footer
    assert "Creator" + " Signal" not in readme
    assert "Checklist support, not legal advice." in readme
    assert "not legal clearance or a trademark opinion" in readme
    assert "represent no real person, brand or result" in readme
    for path in ("assets/influencesignal-banner.png", "assets/influencesignal-mark-64.png",
                 "assets/influencesignal-social.png", "assets/influencesignal-mark.svg"):
        assert (ROOT / path).exists(), path
    for path in ("assets/influencesignal-banner.svg", "assets/influencesignal-lockup-dark.svg"):
        assert not (ROOT / path).exists(), path


def test_issue_templates_name_the_product_and_protect_creator_data() -> None:
    folder = ROOT / ".github" / "ISSUE_TEMPLATE"
    bug = (folder / "bug_report.yml").read_text(encoding="utf-8")
    idea = (folder / "feature_request.yml").read_text(encoding="utf-8")
    config = (folder / "config.yml").read_text(encoding="utf-8")
    assert "Influence Signal" in bug and "Influence Signal" in idea
    assert "Never attach real creator data" in bug
    assert "required: true" in bug
    assert "blank_issues_enabled: false" in config
    assert "influencer-campaigns/blob/main/SECURITY.md" in config
