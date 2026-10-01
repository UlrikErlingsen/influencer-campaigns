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
    files = [ROOT / "app.py", *sorted((ROOT / "pages").glob("*.py"))]
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
    assert 'KEY = "influence"' in (ROOT / "pages" / "ui.py").read_text(encoding="utf-8")
    assert "from influencesignal.ui import signal_theme as sig" in sources
    assert "<style>" not in sources
    assert "lockup-dark" not in sources
    for old_colour in OLD_COLOURS:
        assert old_colour not in sources.lower(), old_colour
        assert old_colour not in (ROOT / "src" / "influencesignal" / "report.py").read_text(encoding="utf-8").lower()
    # Charts use the per-app Plotly template (via sig.chart), not the process-wide default or Streamlit's theme.
    results = (ROOT / "pages" / "results.py").read_text(encoding="utf-8")
    assert "sig.chart(KEY, figure)" in results
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

