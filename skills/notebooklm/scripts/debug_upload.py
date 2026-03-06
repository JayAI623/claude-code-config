#!/usr/bin/env python3
"""
Debug script: Open NotebookLM, create notebook, and screenshot each step
to discover correct selectors for upload.
"""

import sys
import time
import re
from pathlib import Path
from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from browser_utils import BrowserFactory, StealthUtils

SCREENSHOT_DIR = Path(__file__).parent.parent / "data" / "debug_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def screenshot(page, name):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path))
    print(f"  📸 Screenshot: {path}")

def dump_buttons(page):
    """Dump all visible buttons and their text."""
    buttons = page.query_selector_all("button")
    print(f"\n  🔍 Found {len(buttons)} buttons:")
    for i, btn in enumerate(buttons):
        try:
            text = btn.inner_text().strip().replace('\n', ' | ')
            visible = btn.is_visible()
            if visible and text:
                print(f"    [{i}] {text[:80]}")
        except:
            pass

def dump_inputs(page):
    """Dump all input/textarea elements."""
    inputs = page.query_selector_all("input, textarea")
    print(f"\n  🔍 Found {len(inputs)} inputs:")
    for i, inp in enumerate(inputs):
        try:
            tag = inp.evaluate("el => el.tagName")
            itype = inp.get_attribute("type") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            aria = inp.get_attribute("aria-label") or ""
            visible = inp.is_visible()
            print(f"    [{i}] <{tag}> type={itype} placeholder='{placeholder}' aria='{aria}' visible={visible}")
        except:
            pass

def dump_clickable_elements(page):
    """Dump elements with role=menuitem, role=option, etc."""
    for role in ["menuitem", "option", "tab", "listitem"]:
        els = page.query_selector_all(f"[role='{role}']")
        if els:
            print(f"\n  🔍 Found {len(els)} role={role}:")
            for i, el in enumerate(els):
                try:
                    text = el.inner_text().strip().replace('\n', ' | ')
                    visible = el.is_visible()
                    if visible and text:
                        print(f"    [{i}] {text[:80]}")
                except:
                    pass

def main():
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️ Not authenticated")
        return

    playwright = sync_playwright().start()
    context = BrowserFactory.launch_persistent_context(playwright, headless=False)
    page = context.new_page()

    try:
        # Step 1: Go to NotebookLM home
        print("\n=== Step 1: NotebookLM home ===")
        page.goto("https://notebooklm.google.com", wait_until="domcontentloaded")
        time.sleep(5)
        screenshot(page, "01_home")
        dump_buttons(page)

        # Step 2: Click "New notebook"
        print("\n=== Step 2: Create new notebook ===")
        # Try various selectors
        created = False
        for selector in [
            "button:has-text('新建笔记本')",
            "button:has-text('新建')",
            "button:has-text('New notebook')",
            "button:has-text('New Notebook')",
            "button:has-text('Create')",
            "a:has-text('新建')",
            "a:has-text('Create')",
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    print(f"  ✓ Clicking: {selector}")
                    btn.click()
                    created = True
                    break
            except:
                continue

        if not created:
            print("  ❌ Could not find new-notebook button, dumping page...")
            # Try to find anything clickable
            dump_buttons(page)
            # Maybe it's a card or div
            cards = page.query_selector_all("[class*='create'], [class*='new'], [class*='add']")
            print(f"\n  🔍 Found {len(cards)} create/new/add elements:")
            for i, card in enumerate(cards):
                try:
                    tag = card.evaluate("el => el.tagName")
                    text = card.inner_text().strip()[:60]
                    cls = card.get_attribute("class") or ""
                    print(f"    [{i}] <{tag}> class='{cls[:60]}' text='{text}'")
                except:
                    pass

        time.sleep(5)
        screenshot(page, "02_new_notebook")
        print(f"  URL: {page.url}")

        # Step 3: Inspect the notebook page - find add source UI
        print("\n=== Step 3: Notebook page - looking for add source ===")
        dump_buttons(page)
        dump_inputs(page)
        dump_clickable_elements(page)

        # Step 4: Try clicking add source
        print("\n=== Step 4: Try clicking add source ===")
        for selector in [
            "button:has-text('添加来源')",
            "button:has-text('添加源')",
            "button:has-text('Add source')",
            "button:has-text('上传来源')",
            "button:has-text('Upload')",
            "button[aria-label*='添加']",
            "button[aria-label*='Add']",
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    print(f"  ✓ Found add source: {selector}")
                    btn.click()
                    time.sleep(3)
                    screenshot(page, "03_add_source_dialog")
                    print("\n  === Add source dialog ===")
                    dump_buttons(page)
                    dump_inputs(page)
                    dump_clickable_elements(page)
                    break
            except:
                continue

        # Keep browser open for manual inspection
        print("\n⏸️  Browser is open. Press Enter to close...")
        input()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n⏸️  Browser is open for inspection. Press Enter to close...")
        input()
    finally:
        context.close()
        playwright.stop()


if __name__ == "__main__":
    main()
