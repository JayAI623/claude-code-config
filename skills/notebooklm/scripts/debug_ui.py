#!/usr/bin/env python3
"""Debug: open notebook and dump all visible UI elements"""
import sys, time, re
from pathlib import Path
from patchright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory

NOTEBOOK_URL = "https://notebooklm.google.com/notebook/a55961ab-c47d-47be-a9e2-03f2a712ff42"

auth = AuthManager()
playwright = sync_playwright().start()
context = BrowserFactory.launch_persistent_context(playwright, headless=False)
page = context.new_page()
page.set_viewport_size({"width": 1440, "height": 900})

print("🌐 Opening notebook...")
page.goto(NOTEBOOK_URL, wait_until="domcontentloaded", timeout=30000)
print("⏳ Waiting 12s for full render...")
time.sleep(12)

print("\n=== ALL VISIBLE BUTTONS ===")
buttons = page.query_selector_all("button")
for i, b in enumerate(buttons):
    try:
        if b.is_visible():
            text = b.inner_text().strip().replace("\n", " ")
            aria = b.get_attribute("aria-label") or ""
            disabled = b.get_attribute("disabled")
            cls = (b.get_attribute("class") or "")[:60]
            print(f"  [{i}] text={repr(text):<30} aria={repr(aria):<40} disabled={disabled} class={cls}")
    except:
        pass

print("\n=== TEXT containing 'audio' or 'generate' or 'studio' (case-insensitive) ===")
els = page.query_selector_all("*")
seen = set()
for el in els:
    try:
        if not el.is_visible(): continue
        text = el.inner_text().strip()
        lower = text.lower()
        if any(k in lower for k in ["audio", "generate", "studio", "overview", "customize", "podcast"]):
            if text not in seen and len(text) < 200:
                seen.add(text)
                tag = el.evaluate("el => el.tagName")
                print(f"  <{tag}> {repr(text[:100])}")
    except:
        pass

print("\n✅ Done. Browser stays open for 30s so you can inspect manually...")
time.sleep(30)
context.close()
playwright.stop()
