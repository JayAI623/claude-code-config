#!/usr/bin/env python3
"""
List all notebooks from NotebookLM website.

Usage:
  python scripts/run.py list_notebooks.py                # List all notebooks
  python scripts/run.py list_notebooks.py --show-browser  # Show browser for debugging
"""

import argparse
import sys
import time
import re
from pathlib import Path
from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from browser_utils import BrowserFactory

NOTEBOOKLM_URL = "https://notebooklm.google.com"


def list_notebooks(headless: bool = True) -> list[dict]:
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️  Not authenticated. Run: python scripts/run.py auth_manager.py setup")
        return []

    playwright = None
    context = None

    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()

        page.goto(NOTEBOOKLM_URL, wait_until="domcontentloaded")
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com"), timeout=15000)
        time.sleep(5)

        # Scroll down to load all notebooks (lazy loading)
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        # Extract notebook cards - they are <project-button> elements
        notebooks = page.evaluate("""() => {
            const cards = document.querySelectorAll('project-button');
            const results = [];
            for (const card of cards) {
                const text = card.innerText.trim();
                const lines = text.split('\\n').filter(l => l.trim() && l.trim() !== 'more_vert');
                if (lines.length === 0) continue;

                // First line is typically the emoji, title is next
                let emoji = '';
                let title = '';
                let date = '';
                let sourceCount = '';

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed || trimmed === 'more_vert') continue;
                    // Check if it's a single emoji
                    if (!title && trimmed.length <= 2 && /\\p{Emoji}/u.test(trimmed)) {
                        emoji = trimmed;
                    } else if (!title && trimmed.length > 2) {
                        title = trimmed;
                    } else if (trimmed.includes('·') && trimmed.includes('来源')) {
                        // "2026年3月4日·6 个来源"
                        const parts = trimmed.split('·');
                        date = parts[0].trim();
                        sourceCount = parts[1] ? parts[1].trim() : '';
                    } else if (trimmed.match(/^\\d{4}年/)) {
                        date = trimmed;
                    }
                }

                if (title) {
                    results.push({emoji, title, date, sourceCount});
                }
            }
            return results;
        }""")

        if notebooks:
            print(f"\n📚 NotebookLM 上共有 {len(notebooks)} 个笔记本:\n")
            for i, nb in enumerate(notebooks):
                emoji = nb.get('emoji', '')
                title = nb.get('title', 'Untitled')
                date = nb.get('date', '')
                sources = nb.get('sourceCount', '')
                prefix = f"{emoji} " if emoji else ""
                info = f"{date}  {sources}" if date else ""
                print(f"  [{i+1:2d}] {prefix}{title}")
                if info:
                    print(f"       {info}")
            print()
        else:
            print("❌ No notebooks found.")
            print(f"  Page: {page.url}")

        return notebooks

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if context:
            try: context.close()
            except: pass
        if playwright:
            try: playwright.stop()
            except: pass


def main():
    parser = argparse.ArgumentParser(description="List all NotebookLM notebooks")
    parser.add_argument("--show-browser", action="store_true", help="Show browser")
    args = parser.parse_args()

    list_notebooks(headless=not args.show_browser)


if __name__ == "__main__":
    main()
