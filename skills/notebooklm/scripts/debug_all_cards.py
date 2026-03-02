#!/usr/bin/env python3
"""Debug: dump ALL visible cards in Studio panel with full text"""
import sys, time, re
from pathlib import Path
from patchright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).parent))
from browser_utils import BrowserFactory

NOTEBOOK_URL = "https://notebooklm.google.com/notebook/a55961ab-c47d-47be-a9e2-03f2a712ff42"

playwright = sync_playwright().start()
context = BrowserFactory.launch_persistent_context(playwright, headless=False)
page = context.new_page()
page.set_viewport_size({"width": 1440, "height": 900})
page.goto(NOTEBOOK_URL, wait_until="domcontentloaded", timeout=30000)
print("⏳ Waiting 12s...")
time.sleep(12)

print("\n=== ALL VISIBLE BUTTONS containing '个来源' ===")
for btn in page.query_selector_all("button"):
    try:
        if not btn.is_visible(): continue
        text = btn.inner_text().strip()
        if "个来源" in text:
            aria = btn.get_attribute("aria-label") or ""
            print(f"\n--- button ---")
            print(f"  aria : {repr(aria)}")
            print(f"  text : {repr(text[:300])}")
    except: pass

print("\n=== ALL div[role=button] containing '个来源' ===")
for el in page.query_selector_all("div[role='button']"):
    try:
        if not el.is_visible(): continue
        text = el.inner_text().strip()
        if "个来源" in text:
            aria = el.get_attribute("aria-label") or ""
            print(f"\n--- div[role=button] ---")
            print(f"  aria : {repr(aria)}")
            print(f"  text : {repr(text[:300])}")
    except: pass

print("\n✅ Done. Closing in 30s...")
time.sleep(30)
context.close()
playwright.stop()
