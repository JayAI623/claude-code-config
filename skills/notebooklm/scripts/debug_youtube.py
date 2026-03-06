#!/usr/bin/env python3
"""Debug YouTube URL upload to NotebookLM."""

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
    print(f"  📸 {path}")

def dump_visible_buttons(page):
    buttons = page.query_selector_all("button")
    print(f"\n  Visible buttons:")
    for i, btn in enumerate(buttons):
        try:
            text = btn.inner_text().strip().replace('\n', ' | ')
            if btn.is_visible() and text:
                enabled = btn.is_enabled()
                print(f"    [{i}] {'✓' if enabled else '✗'} {text[:80]}")
        except:
            pass

def main():
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️ Not authenticated")
        return

    NOTEBOOK_URL = "https://notebooklm.google.com/notebook/e7adf325-8e42-4060-9152-26efd85b444e"
    YOUTUBE_URL = "https://www.youtube.com/watch?v=Uh0F_suae5Q"

    playwright = sync_playwright().start()
    context = BrowserFactory.launch_persistent_context(playwright, headless=False)
    page = context.new_page()

    try:
        print("Opening notebook...")
        page.goto(NOTEBOOK_URL, wait_until="domcontentloaded")
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)
        time.sleep(5)
        screenshot(page, "yt_01_notebook")

        # Click add source
        print("\nClicking '添加来源'...")
        btn = page.query_selector("button:has-text('添加来源')")
        if btn and btn.is_visible():
            btn.click()
            time.sleep(2)
        screenshot(page, "yt_02_add_source")

        # Click website/link
        print("\nClicking '网站'...")
        btn = page.query_selector("button:has-text('网站')")
        if btn and btn.is_visible():
            btn.click()
            time.sleep(2)
        screenshot(page, "yt_03_website")

        # Find and fill URL textarea
        print("\nLooking for URL input...")
        url_input = page.query_selector("textarea[placeholder*='粘贴']")
        if url_input and url_input.is_visible():
            print(f"  ✓ Found textarea with placeholder: '{url_input.get_attribute('placeholder')}'")
            url_input.click()
            url_input.fill(YOUTUBE_URL)
            time.sleep(2)
            screenshot(page, "yt_04_url_filled")
            print("\n  After filling URL:")
            dump_visible_buttons(page)
        else:
            print("  ❌ URL textarea not found")
            # Dump all visible inputs
            inputs = page.query_selector_all("input, textarea")
            for i, inp in enumerate(inputs):
                try:
                    if inp.is_visible():
                        tag = inp.evaluate("el => el.tagName")
                        ph = inp.get_attribute("placeholder") or ""
                        print(f"    [{i}] <{tag}> placeholder='{ph}'")
                except:
                    pass

        # Try pressing Enter
        print("\nPressing Enter...")
        page.keyboard.press("Enter")
        time.sleep(3)
        screenshot(page, "yt_05_after_enter")
        dump_visible_buttons(page)

        # Check for confirmation
        time.sleep(5)
        screenshot(page, "yt_06_final")
        dump_visible_buttons(page)

        print("\nDone. Check screenshots in:", SCREENSHOT_DIR)

    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()
    finally:
        time.sleep(2)
        context.close()
        playwright.stop()


if __name__ == "__main__":
    main()
