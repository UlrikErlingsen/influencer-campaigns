"""Capture README screenshots from a running InfluenceSignal (fictional demo loaded).

Dev-only helper; not a runtime dependency. Usage:

    python -m pip install playwright
    python -m streamlit run app.py --server.port=8590   # in another terminal, demo data loaded
    python scripts/take_screenshots.py --browser-channel msedge   # or: python -m playwright install chromium
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = [
    ("welcome", "welcome", ""),
    ("creators", "creators", ""),
    ("campaigns", "campaigns", "fjellbrus-hostfjell-2026"),
    ("pipeline", "pipeline", "fjellbrus-hostfjell-2026"),
    ("deliverables", "deliverables", "fjellbrus-hostfjell-2026"),
    ("compliance", "compliance", "fjellbrus-hostfjell-2026"),
    ("results", "results", "fjellbrus-varlop-2026"),
    ("report", "report", "fjellbrus-varlop-2026"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8590")
    parser.add_argument("--out", default=str(ROOT / "assets" / "screenshots"))
    parser.add_argument("--browser-channel", default=None, help="e.g. msedge or chrome to use an installed browser")
    parser.add_argument("--only", nargs="*", help="names to capture (default: all)")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.browser_channel)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        for name, slug, campaign in SHOTS:
            if args.only and name not in args.only:
                continue
            query = f"?page={slug}" + (f"&campaign={campaign}" if campaign else "")
            page.goto(args.url + "/" + query)
            page.wait_for_selector(".ps-masthead", timeout=60_000)
            page.wait_for_timeout(3500)
            page.screenshot(path=str(out / f"{name}.png"))
            print("saved", out / f"{name}.png")
        browser.close()


if __name__ == "__main__":
    main()
