"""Architecture rules for a future merged Signal Hub: the package is UI-free (except its ``ui/`` subpackage, which holds
the synced Signal theme) and storage sits behind one module."""

import ast
from pathlib import Path

import influencesignal

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
UI_PACKAGE = SRC / "influencesignal" / "ui"  # the one place under src/ that may import Streamlit


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _imports_streamlit(path: Path) -> bool:
    return any(module == "streamlit" or module.startswith("streamlit.") for module in _imported_modules(path))


def _in_ui_package(path: Path) -> bool:
    return path.is_relative_to(UI_PACKAGE)


def test_no_file_under_src_imports_streamlit_except_ui() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in SRC.rglob("*.py")
        if not _in_ui_package(path) and _imports_streamlit(path)
    ]
    assert not offenders, f"Streamlit belongs in app.py, pages/ or src/influencesignal/ui/, not the package: {offenders}"


def _app_code() -> list[Path]:
    """Every first-party Python file except tests and dev scripts."""
    skip = {".venv", "build", "dist", "tests", "scripts", ".git"}
    return [path for path in ROOT.rglob("*.py") if not skip & set(path.relative_to(ROOT).parts)]


def test_streamlit_only_in_app_pages_and_ui_package() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in _app_code()
        if path.name != "app.py" and path.parent.name != "pages" and not _in_ui_package(path)
        and _imports_streamlit(path)
    ]
    assert not offenders, f"Streamlit code belongs in app.py, pages/ or src/influencesignal/ui/: {offenders}"


def test_only_storage_module_touches_sqlite() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in _app_code()
        if path.name != "storage.py" and "sqlite3" in _imported_modules(path)
    ]
    assert not offenders, f"Keep SQLite behind storage.py so it can be swapped: {offenders}"


def test_every_page_module_exposes_render() -> None:
    import importlib

    modules = sorted(path.stem for path in (ROOT / "pages").glob("*.py") if path.stem not in ("__init__", "ui"))
    assert len(modules) == 9
    for name in modules:
        module = importlib.import_module(f"pages.{name}")
        assert callable(getattr(module, "render", None)), name


def test_public_api_is_exported() -> None:
    for name in influencesignal.__all__:
        assert hasattr(influencesignal, name), name
    for name in ("Store", "load_rules", "checklist_status", "paid_gate", "build_tracked_url", "summarize_results",
                 "build_report", "load_demo"):
        assert name in influencesignal.__all__
