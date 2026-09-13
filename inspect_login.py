"""Read-only inspection of the unauthenticated page; does not select a chat."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

folder = Path(__file__).resolve().parent / "debug"
folder.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()
    page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(15000)
    page.screenshot(path=str(folder / "login-inspection.png"), full_page=True)
    (folder / "login-inspection.html").write_text(page.content(), encoding="utf-8")
    print(json.dumps(page.locator("[role], [aria-label], input, button").evaluate_all(
        "els => els.filter(e => e.getBoundingClientRect().width).map(e => ({tag:e.tagName,role:e.getAttribute('role'),label:e.getAttribute('aria-label'),text:(e.innerText||'').slice(0,100)})).slice(0,80)"), indent=2))
    browser.close()
