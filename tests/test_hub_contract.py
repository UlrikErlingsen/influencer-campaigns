"""Signal Hub contract: importable UI entry point, Streamlit only under ui/, slug-namespaced state, and hub mode
(SIGNAL_HUB=1: in-memory workspace seeded with the demo, nothing written to disk, no local workspace, no network)."""

import ast
from html import unescape
import importlib.util
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import urllib.request

import pytest
from streamlit.testing.v1 import AppTest

from influencesignal import DISCLAIMER, __version__
from influencesignal.demo import load_demo
from influencesignal.rules import load_rules
from influencesignal.storage import Store

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "influencesignal"
UI = PACKAGE / "ui"
SYNCED = {"signal_theme.py", "signal_font.py"}  # synced from Signal Hub, not app code
UI_ONLY_LIBRARIES = {"streamlit", "plotly"}
CORE_MODULES = (
    "influencesignal", "influencesignal.compliance", "influencesignal.demo", "influencesignal.errors",
    "influencesignal.io", "influencesignal.metrics", "influencesignal.report", "influencesignal.rules",
    "influencesignal.storage", "influencesignal.utm",
)
# Every Streamlit call that creates a stateful widget (or a keyed chart) must pass an explicit key.
KEYED_CALLS = {
    "button", "checkbox", "data_editor", "date_input", "download_button", "file_uploader", "form_submit_button",
    "multiselect", "number_input", "chart", "plotly_chart", "radio", "selectbox", "slider", "text_area",
    "text_input", "toggle",
}
PAGES = [
    "Welcome",
    "1 · Creators",
    "2 · Campaigns",
    "3 · Pipeline",
    "4 · Deliverables",
    "5 · Compliance",
    "6 · Results",
    "7 · Report",
    "Settings & data",
]
RENDER_SCRIPT = """
from influencesignal.ui import render

render()
"""
HUB_NOTE = "Signal Hub demo workspace."


def _ui_sources() -> list[Path]:
    return [path for path in UI.rglob("*.py") if path.name not in SYNCED]


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _render(page: str | None = None) -> AppTest:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    if page is not None:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, [error.value for error in app.exception]
    return app


def _text(app: AppTest) -> str:
    parts = [str(item.value) for item in app.markdown]
    parts += [str(item.value) for item in app.caption]
    parts += [str(item.value) for kind in (app.warning, app.error, app.info, app.success) for item in kind]
    return unescape("\n".join(parts))


@pytest.fixture
def standalone(tmp_path, monkeypatch):
    monkeypatch.delenv("SIGNAL_HUB", raising=False)
    monkeypatch.setenv("INFLUENCESIGNAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("INFLUENCESIGNAL_NO_DEMO", raising=False)


@pytest.fixture
def hub(tmp_path, monkeypatch) -> Path:
    """Hub mode in an empty temporary cwd, with home and app-data folders pointed inside it; returns the folder."""
    sandbox = tmp_path / "sandbox"
    home = sandbox / "home"
    home.mkdir(parents=True)
    monkeypatch.chdir(sandbox)
    monkeypatch.setenv("SIGNAL_HUB", "1")
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_CONFIG_HOME",
                 "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(name, str(home))
    monkeypatch.delenv("INFLUENCESIGNAL_DATA_DIR", raising=False)  # the default would be ./data in the sandbox
    monkeypatch.delenv("INFLUENCESIGNAL_NO_DEMO", raising=False)
    return sandbox


def _files_under(folder: Path) -> list[str]:
    return sorted(str(path.relative_to(folder)) for path in folder.rglob("*") if path.is_file())


# ── contract ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_ui_entry_point_matches_the_hub_contract() -> None:
    from influencesignal.ui import APP_INFO, render

    assert callable(render)
    assert APP_INFO == {
        "product": "Influence Signal",
        "version": __version__,
        "repo": "influencer-campaigns",
        "slug": "influence",
    }


def test_only_the_ui_package_imports_streamlit_or_plotly() -> None:
    offenders = {
        str(path.relative_to(PACKAGE)): sorted(_imported_roots(path) & UI_ONLY_LIBRARIES)
        for path in PACKAGE.rglob("*.py")
        if UI not in path.parents and _imported_roots(path) & UI_ONLY_LIBRARIES
    }
    assert not offenders, offenders


def test_core_package_imports_without_streamlit_or_plotly() -> None:
    # A fresh interpreter, so modules already imported by other tests cannot hide a stray import.
    code = (
        f"import sys\nsys.path.insert(0, {str(ROOT / 'src')!r})\n"
        f"import importlib\nfor name in {CORE_MODULES!r}:\n    importlib.import_module(name)\n"
        "loaded = sorted(name for name in ('streamlit', 'plotly') if name in sys.modules)\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_render_works_from_the_packaged_files_alone_in_hub_mode(tmp_path: Path) -> None:
    # Signal Hub installs the release as a normal package: only src/influencesignal/**/*.py and the declared package
    # data (rules/*.yaml, ui/assets/marks/*) exist there, so render() must not read pages/, data/ or assets/ at the
    # repo root. Run it the way the Hub does (SIGNAL_HUB=1) and check that nothing lands in the working folder.
    for path in PACKAGE.rglob("*"):
        relative = path.relative_to(PACKAGE)
        packaged = (
            path.suffix == ".py"
            or (relative.parent == Path("rules") and path.suffix == ".yaml")
            or relative.parent == Path("ui", "assets", "marks")
        )
        if path.is_file() and packaged and "__pycache__" not in relative.parts:
            target = tmp_path / "site" / "influencesignal" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    work = tmp_path / "work"
    work.mkdir()
    site = str(tmp_path / "site")
    script = f"import sys\nsys.path.insert(0, {site!r})\nfrom influencesignal.ui import render\nrender()\n"
    code = (
        "import sys\nsys.dont_write_bytecode = True\n"
        f"sys.path.insert(0, {site!r})\n"
        "from pathlib import Path\n"
        "from streamlit.testing.v1 import AppTest\n"
        "import influencesignal\n"
        f"assert Path(influencesignal.__file__).is_relative_to({site!r}), influencesignal.__file__\n"
        "from influencesignal.ui import signal_theme as sig\n"
        "assert Path(sig.page_config('influence')['page_icon']).exists()\n"
        f"app = AppTest.from_string({script!r}, default_timeout=120)\n"
        "app.run()\n"
        "assert not app.exception, [error.value for error in app.exception]\n"
        f"for page in {PAGES!r}:\n"
        "    app.sidebar.radio[0].set_value(page).run()\n"
        "    assert not app.exception, (page, [error.value for error in app.exception])\n"
        "assert app.session_state['influence:memory_store'].in_memory\n"
    )
    env = {**os.environ, "SIGNAL_HUB": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("INFLUENCESIGNAL_DATA_DIR", None)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=work, env=env
    )
    assert result.returncode == 0, result.stderr
    assert _files_under(work) == []


def test_render_never_sets_page_config_or_navigation() -> None:
    for path in _ui_sources():
        source = path.read_text(encoding="utf-8")
        for call in ("st.set_page_config(", "st.navigation(", "st.Page(", "st.stop(", "st.logo("):
            assert call not in source, (path.relative_to(UI), call)


def test_render_runs_from_a_script_without_set_page_config(standalone) -> None:
    app = _render()

    assert app.sidebar.radio[0].key == "influence:page"
    assert "influence:campaign_id" in app.session_state
    assert "influence:db_path" in app.session_state
    for bare in ("campaign_id", "db_path", "page"):
        assert bare not in app.session_state, bare
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "sg-mast" in body and "sg-foot" in body
    assert "SHORTLIST → PUBLISH → CHECK → REPORT" in body
    assert "INFLUENCER CAMPAIGNS · NORWAY" in body  # the Welcome page
    assert f"Influence Signal v{__version__}" in body
    assert DISCLAIMER in body


@pytest.mark.parametrize("page", PAGES)
def test_every_widget_key_is_namespaced(standalone, page: str) -> None:
    app = _render(page)
    widgets = [
        *app.radio, *app.selectbox, *app.checkbox, *app.toggle, *app.button, *app.number_input,
        *app.multiselect, *app.slider, *app.date_input, *app.text_input, *app.text_area,
    ]
    assert widgets
    unkeyed = [(type(widget).__name__, widget.label) for widget in widgets if widget.key is None]
    assert not unkeyed, unkeyed
    assert all(widget.key.startswith("influence:") for widget in widgets), [w.key for w in widgets]
    assert all(str(key).startswith("influence:") or str(key).startswith("$$") for key in app.session_state)


def test_every_widget_call_passes_an_explicit_key() -> None:
    # Some widgets only appear after an upload or in a given state; check the source too.
    unkeyed = [
        (str(path.relative_to(UI)), node.lineno, node.func.attr)
        for path in _ui_sources()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in KEYED_CALLS
        and not any(keyword.arg == "key" for keyword in node.keywords)
    ]
    assert not unkeyed, unkeyed


def test_session_state_form_and_widget_keys_go_through_the_namespace_helper() -> None:
    state_keys, widget_keys, form_keys = [], [], []
    for path in _ui_sources():
        source = path.read_text(encoding="utf-8")
        state_keys += re.findall(r"session_state(?:\[|\.get\(|\.pop\()\s*([^,\])]+)", source)
        widget_keys += re.findall(r"\bkey=([^,)\n]+)", source)
        form_keys += re.findall(r"\bst\.form\(([^,)\n]+)", source)
    assert state_keys and widget_keys and form_keys
    # The pipeline callback receives a key its caller already built with k().
    assert all(key.startswith("k(") or key == "key" for key in state_keys), state_keys
    # Field helpers forward a key their callers already built with k().
    assert all(key.startswith("k(") or key == "key" for key in widget_keys), widget_keys
    assert all(key.startswith("k(") for key in form_keys), form_keys
    assert 'NS = "influence"' in (UI / "shell.py").read_text(encoding="utf-8")


# ── hub mode (SIGNAL_HUB=1) ───────────────────────────────────────────────────────────────────────────────────────
def test_hub_mode_renders_every_page_in_memory_without_writing_files(hub: Path) -> None:
    app = _render()
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, (page, [error.value for error in app.exception])
    memory = app.session_state["influence:memory_store"]
    assert memory.in_memory and memory.has_demo_data() and len(memory.creators()) == 25
    assert "influence:db_path" not in app.session_state
    assert _files_under(hub) == []


def test_hub_mode_never_reads_an_existing_local_workspace(hub: Path, monkeypatch) -> None:
    local = Store(hub / "data" / "influencesignal.db")  # where the standalone app would look
    local.add_creator({"name": "Local Only Person", "instagram": "local_only"})
    monkeypatch.setenv("INFLUENCESIGNAL_DATA_DIR", str(hub / "data"))
    before = (hub / "data" / "influencesignal.db").read_bytes()

    app = _render("1 · Creators")
    roster = app.dataframe[0].value
    assert "Local Only Person" not in set(roster["name"])
    assert len(roster) == 25  # the fictional demo instead
    assert (hub / "data" / "influencesignal.db").read_bytes() == before
    assert _files_under(hub) == ["data/influencesignal.db".replace("/", os.sep)]


def test_hub_mode_ignores_a_local_rules_file(hub: Path, monkeypatch) -> None:
    monkeypatch.setenv("INFLUENCESIGNAL_RULES", str(hub / "no-such-rules.yaml"))
    app = _render("5 · Compliance")
    assert DISCLAIMER in _text(app)
    assert len(app.metric) == 5  # the checklist summary rendered, so the packaged rules loaded


def test_hub_mode_settings_hide_database_folders_and_say_why(hub: Path) -> None:
    app = _render("Settings & data")
    text = _text(app)
    assert HUB_NOTE in text and "Database folders are off in Signal Hub" in text
    assert "Current database" not in text
    assert not [box for box in app.text_input if box.label == "Data folder"]
    assert not [button for button in app.button if button.label == "Use this folder"]
    assert DISCLAIMER in text
    assert _files_under(hub) == []


def test_hub_mode_workspace_actions_stay_in_memory_and_per_session(hub: Path) -> None:
    first = _render("Settings & data")
    first.checkbox(key="influence:confirm_empty").check().run()
    next(button for button in first.button if button.label == "Delete all data").click().run()
    assert not first.exception, [error.value for error in first.exception]
    assert first.session_state["influence:memory_store"].is_empty()

    second = _render()  # another browser session gets its own demo workspace
    assert second.session_state["influence:memory_store"].has_demo_data()
    assert first.session_state["influence:memory_store"].is_empty()
    assert _files_under(hub) == []


def test_hub_mode_makes_no_network_calls(hub: Path, monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("network call in hub mode")

    real_connect = socket.socket.connect

    def connect_loopback_only(sock, address):
        # asyncio's self-pipe on Windows is a loopback socket pair; anything else would leave the machine.
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError(f"network call in hub mode: {address}")
        return real_connect(sock, address)

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", connect_loopback_only)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    if importlib.util.find_spec("requests"):
        import requests

        monkeypatch.setattr(requests.Session, "request", refuse)
    if importlib.util.find_spec("feedparser"):
        import feedparser

        monkeypatch.setattr(feedparser, "parse", refuse)

    app = _render()
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, (page, [error.value for error in app.exception])
    assert _files_under(hub) == []


def test_hub_mode_shows_the_demo_and_the_disclaimer_on_compliance_screens(hub: Path) -> None:
    for page in ("Welcome", "5 · Compliance", "7 · Report"):
        text = _text(_render(page))
        assert "Fictional demo data loaded" in text, page
        assert DISCLAIMER in text, page
    welcome = _text(_render("Welcome"))
    assert HUB_NOTE in welcome
    assert "SQLite file on this computer" not in welcome


def test_standalone_mode_still_uses_the_sqlite_file(standalone, tmp_path: Path) -> None:
    store = Store(tmp_path / "influencesignal.db")
    load_demo(store, load_rules())
    store.add_creator({"name": "Saved Locally", "tiktok": "saved_locally"})

    app = _render("1 · Creators")
    assert "Saved Locally" in set(app.dataframe[0].value["name"])
    assert "influence:memory_store" not in app.session_state
    assert HUB_NOTE not in _text(app)
