#!/usr/bin/env python3
"""Debug: find source list selectors in NotebookLM sidebar."""

import sys
import time
import re
from pathlib import Path
from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from browser_utils import BrowserFactory

NOTEBOOK_URL = "https://notebooklm.google.com/notebook/e7adf325-8e42-4060-9152-26efd85b444e"
SCREENSHOT_DIR = Path(__file__).parent.parent / "data" / "debug_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️ Not authenticated")
        return

    playwright = sync_playwright().start()
    context = BrowserFactory.launch_persistent_context(playwright, headless=False)
    page = context.new_page()

    try:
        page.goto(NOTEBOOK_URL, wait_until="domcontentloaded")
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)
        time.sleep(6)

        # Screenshot current state
        path = SCREENSHOT_DIR / "sources_current.png"
        page.screenshot(path=str(path))
        print(f"📸 {path}")

        # Search for known text in the page
        print("\n--- Searching for source-related text nodes ---")
        results = page.evaluate("""() => {
            const found = [];
            const keywords = ['Uh0F_suae5Q', 'transcript', 'summary', 'Amazon AGI', 'youtube'];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                const txt = walker.currentNode.textContent.trim();
                for (const kw of keywords) {
                    if (txt.toLowerCase().includes(kw.toLowerCase()) && txt.length < 200) {
                        const el = walker.currentNode.parentElement;
                        found.push({
                            keyword: kw,
                            text: txt.substring(0, 120),
                            tag: el ? el.tagName : 'null',
                            id: el ? (el.id || '') : '',
                            cls: el ? (String(el.className || '')).substring(0, 80) : '',
                        });
                        break;
                    }
                }
            }
            return found.slice(0, 30);
        }""")
        for r in results:
            print(f"  [{r['keyword']}] <{r['tag']}> id=\"{r['id']}\" class=\"{r['cls']}\"")
            print(f"    text: \"{r['text']}\"")

        # Get all checkboxes
        print("\n--- Checkboxes ---")
        cbs = page.query_selector_all("mat-checkbox, input[type='checkbox'], [role='checkbox']")
        for i, cb in enumerate(cbs):
            try:
                text = page.evaluate("""(el) => {
                    let p = el;
                    for (let j = 0; j < 6; j++) {
                        if (!p) break;
                        let t = p.innerText ? p.innerText.trim() : '';
                        if (t && t.length > 3) return t.substring(0, 100);
                        p = p.parentElement;
                    }
                    return '';
                }""", cb)
                if text:
                    print(f"  [{i}] {text}")
            except:
                pass

    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()
    finally:
        time.sleep(1)
        context.close()
        playwright.stop()

if __name__ == "__main__":
    main()
