"""Architecture rules for a future merged Signal Hub: the package is UI-free and storage sits behind one module."""

import ast
from pathlib import Path

import creatorsignal

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def test_no_file_under_src_imports_streamlit() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in SRC.rglob("*.py")
        if any(module == "streamlit" or module.startswith("streamlit.") for module in _imported_modules(path))
    ]
    assert not offenders, f"Streamlit belongs in app.py or pages/, not the package: {offenders}"


def test_only_storage_module_touches_sqlite() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in SRC.rglob("*.py")
        if path.name != "storage.py" and "sqlite3" in _imported_modules(path)
    ]
    assert not offenders, f"Keep SQLite behind storage.py so it can be swapped: {offenders}"


def test_public_api_is_exported() -> None:
    for name in creatorsignal.__all__:
        assert hasattr(creatorsignal, name), name
    for name in ("Store", "load_rules", "checklist_status", "paid_gate", "build_tracked_url", "summarize_results",
                 "build_report", "load_demo"):
        assert name in creatorsignal.__all__
