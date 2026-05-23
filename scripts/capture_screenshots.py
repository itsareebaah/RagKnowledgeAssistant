"""Capture README screenshots (requires server on BASE_URL)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Install: pip install playwright && playwright install chromium")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8765"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
SAMPLE = Path(__file__).resolve().parent.parent / "sample_docs" / "company_policy.txt"


def wait_for_server(timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE_URL}/api/health", timeout=2.0)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError(f"Server not reachable at {BASE_URL}")


def seed_document() -> None:
    with SAMPLE.open("rb") as f:
        httpx.post(
            f"{BASE_URL}/api/upload",
            files={"file": (SAMPLE.name, f, "text/plain")},
            timeout=120.0,
        )


def main() -> None:
    wait_for_server()
    seed_document()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(BASE_URL, wait_until="networkidle")

        page.screenshot(path=str(OUT_DIR / "01-dashboard.png"), full_page=True)

        page.fill("#question", "How many vacation days do new employees get?")
        page.click("#query-form button[type='submit']")
        page.wait_for_selector("#answer:not(.hidden)", timeout=120_000)
        time.sleep(0.5)
        page.screenshot(path=str(OUT_DIR / "02-query-answer.png"), full_page=True)

        page.goto(f"{BASE_URL}/docs", wait_until="networkidle")
        page.screenshot(path=str(OUT_DIR / "03-api-docs.png"), full_page=True)

        browser.close()

    print(f"Screenshots saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
