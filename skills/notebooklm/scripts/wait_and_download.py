#!/usr/bin/env python3
"""Wait for any still-generating artifact to finish, then download it."""
import sys, time, re, argparse
from pathlib import Path
from patchright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory
from studio_download import _find_all_artifact_cards, _find_menu_download_item, _build_output_path

NOTEBOOK_URL = "https://notebooklm.google.com/notebook/a55961ab-c47d-47be-a9e2-03f2a712ff42"

def wait_and_download(notebook_url, keyword="演示文稿", output_path=None):
    auth = AuthManager()
    playwright = sync_playwright().start()
    context = BrowserFactory.launch_persistent_context(playwright, headless=False)
    page = context.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})

    print("🌐 Opening notebook...")
    page.goto(notebook_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_url(re.compile(r"https://notebooklm\.google\.com/"), timeout=15000)
    print("⏳ Waiting for Studio panel (10s)...")
    time.sleep(10)

    print(f"👀 Watching for '{keyword}' to finish generating...")
    deadline = time.time() + 600
    tick = 0

    while time.time() < deadline:
        # Check if still generating
        generating = False
        for btn in page.query_selector_all("button"):
            try:
                if not btn.is_visible(): continue
                text = btn.inner_text().strip()
                if "正在生成" in text and keyword in text:
                    generating = True
                    break
            except: pass

        # Check if now ready (has more_vert)
        cards = _find_all_artifact_cards(page)
        target = next((c for c in cards if keyword in c["title"] or keyword in c["type_label"]), None)

        if target and not generating:
            print(f"✅ '{keyword}' is ready: {target['title']}")
            break

        tick += 1
        if tick % 4 == 0:
            status = "still generating..." if generating else "waiting for card..."
            print(f"   ⏳ {int(time.time()-(deadline-600))}s — {status}")
        time.sleep(5)
    else:
        print("❌ Timed out.")
        context.close(); playwright.stop()
        return False

    # Download
    if not target["more_btn"]:
        print("❌ No download menu found.")
        context.close(); playwright.stop()
        return False

    target["more_btn"].click()
    time.sleep(1)

    dl_item = _find_menu_download_item(page)
    if not dl_item:
        items = page.query_selector_all('[role="menuitem"]')
        print(f"❌ No download item. Menu: {[i.inner_text().strip() for i in items]}")
        context.close(); playwright.stop()
        return False

    if not output_path:
        output_path = _build_output_path(target)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with page.expect_download(timeout=60000) as dl_info:
        dl_item.click()
    dl = dl_info.value
    suggested = dl.suggested_filename
    if suggested:
        ext = Path(suggested).suffix
        if ext:
            output_path = str(Path(output_path).with_suffix(ext))
    dl.save_as(output_path)
    size = Path(output_path).stat().st_size / 1024
    print(f"✅ Saved ({size:.0f} KB): {output_path}")

    context.close()
    playwright.stop()
    return True

parser = argparse.ArgumentParser()
parser.add_argument("--keyword", default="演示文稿")
parser.add_argument("--output", default=None)
args = parser.parse_args()

active = NotebookLibrary().get_active_notebook()
url = active["url"] if active else NOTEBOOK_URL
print(f"📚 Notebook: {active['name'] if active else url}")

wait_and_download(url, keyword=args.keyword, output_path=args.output)
