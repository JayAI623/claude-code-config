#!/usr/bin/env python3
"""Debug: inspect Studio panel buttons specifically, with DevTools enabled"""
import sys, time, re
from pathlib import Path
from patchright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from browser_utils import BrowserFactory

NOTEBOOK_URL = "https://notebooklm.google.com/notebook/a55961ab-c47d-47be-a9e2-03f2a712ff42"

playwright = sync_playwright().start()
context = BrowserFactory.launch_persistent_context(playwright, headless=False)
page = context.new_page()
page.set_viewport_size({"width": 1440, "height": 900})

print("🌐 Opening notebook...")
page.goto(NOTEBOOK_URL, wait_until="domcontentloaded", timeout=30000)
print("⏳ Waiting 12s for full render...")
time.sleep(12)

print("\n=== STUDIO PANEL — ALL BUTTONS (no limit) ===")
# Query buttons specifically in the Studio panel
studio_buttons = page.query_selector_all("*")
for el in studio_buttons:
    try:
        tag = el.evaluate("e => e.tagName").lower()
        if tag not in ("button",): continue
        if not el.is_visible(): continue
        text = el.inner_text().strip().replace("\n", " ")[:60]
        aria = el.get_attribute("aria-label") or ""
        disabled = el.get_attribute("disabled")
        cls = (el.get_attribute("class") or "")[:80]
        print(f"  btn: text={repr(text):<35} aria={repr(aria):<40} disabled={disabled}")
    except:
        pass

print("\n=== STUDIO PANEL HTML (audio section) ===")
try:
    studio = page.query_selector("notebook-studio-panel, [class*='studio'], #studio")
    if studio:
        html = studio.inner_html()[:3000]
        print(html)
    else:
        # Try audio-overview specific element
        audio_els = page.query_selector_all("basic-create-artifact-button, audio-overview, [class*='audio']")
        for el in audio_els:
            try:
                print(f"\n<{el.evaluate('e=>e.tagName')}> HTML:")
                print(el.inner_html()[:1000])
            except:
                pass
except Exception as e:
    print(f"Error: {e}")

print("\n✅ Inspect the browser manually (F12 for DevTools). Waiting 60s...")
time.sleep(60)
context.close()
playwright.stop()
