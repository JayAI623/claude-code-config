#!/usr/bin/env python3
"""
Download already-generated NotebookLM Audio Overview.
Lists all generated audio cards, lets user pick one, downloads via the 更多 menu.

Usage:
  python scripts/run.py download_audio.py
  python scripts/run.py download_audio.py --index 0   # first audio
  python scripts/run.py download_audio.py --output ~/Downloads/audio.mp3
"""

import argparse
import sys
import time
import re
from pathlib import Path
from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory, StealthUtils


def download_audio(notebook_url: str, pick_index: int = None, output_path: str = None) -> bool:
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️  Not authenticated.")
        return False

    playwright = None
    context = None
    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=False)
        page = context.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        print("🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)
        print("⏳ Waiting for Studio panel (10s)...")
        time.sleep(10)

        # ── Find all generated audio cards ──
        audio_cards = _find_audio_cards(page)
        if not audio_cards:
            print("❌ No generated audio found in Studio panel.")
            return False

        # Print list
        print(f"\n🎙️  Found {len(audio_cards)} audio(s):\n")
        for i, card in enumerate(audio_cards):
            print(f"  [{i}] {card['title']}")

        # Pick index
        idx = pick_index
        if idx is None:
            if len(audio_cards) == 1:
                idx = 0
            else:
                raw = input("\nEnter index to download: ").strip()
                idx = int(raw)

        if idx < 0 or idx >= len(audio_cards):
            print(f"❌ Invalid index: {idx}")
            return False

        chosen = audio_cards[idx]
        print(f"\n⬇️  Downloading: {chosen['title']}")

        # ── Click 更多 on the chosen card ──
        more_btn = chosen["more_btn"]
        more_btn.click()
        time.sleep(1)

        # ── Find 下载 in dropdown ──
        download_item = None
        for text in ["下载", "Download", "download"]:
            try:
                el = page.wait_for_selector(
                    f'[role="menuitem"]:has-text("{text}"), '
                    f'button:has-text("{text}"), '
                    f'a:has-text("{text}")',
                    timeout=4000, state="visible"
                )
                if el:
                    download_item = el
                    break
            except Exception:
                pass

        if not download_item:
            print("❌ No download option found in menu.")
            # Show menu items for debug
            items = page.query_selector_all('[role="menuitem"]')
            print(f"   Menu items: {[i.inner_text().strip() for i in items]}")
            return False

        # ── Download ──
        if not output_path:
            clean_title = re.sub(r'\s+', ' ', chosen['title']).strip()
            safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', clean_title)[:40].strip('_')
            output_path = str(Path.home() / "Downloads" / f"{safe_title}.mp3")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with page.expect_download(timeout=60000) as dl_info:
            download_item.click()

        dl = dl_info.value
        dl.save_as(output_path)
        size = Path(output_path).stat().st_size / 1024
        print(f"✅ Saved ({size:.0f} KB): {output_path}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if context:
            try: context.close()
            except: pass
        if playwright:
            try: playwright.stop()
            except: pass


def _find_audio_cards(page) -> list:
    """
    Find all generated audio cards in Studio panel.
    Each card has a play_arrow button and a more_vert button.
    Card title is extracted from the card button text.
    """
    cards = []
    buttons = page.query_selector_all("button")

    for btn in buttons:
        try:
            if not btn.is_visible(): continue
            text = btn.inner_text().strip()
            # Audio cards contain 'audio_magic_eraser' icon + title + 'play_arr'
            if "audio_magic_eraser" in text and "play_arr" in text:
                # Extract title: between icon name and timestamp
                # Format: "audio_magic_eraser TITLE · N 个来源 · X 分钟前 play_arr..."
                match = re.search(r'audio_magic_eraser\s+(.+?)\s+\d+ 个来源', text)
                title = match.group(1).strip() if match else text[:50]

                # The more_vert button is the NEXT visible button after this card button
                # We'll find it by position in the buttons list
                card_box = btn.bounding_box()
                cards.append({"title": title, "card_btn": btn, "more_btn": None, "box": card_box})
        except Exception:
            pass

    # Now find the matching more_vert buttons (aria='更多') near each card
    more_btns = []
    for btn in buttons:
        try:
            aria = btn.get_attribute("aria-label") or ""
            text = btn.inner_text().strip()
            if (aria == "更多" or text == "more_vert") and btn.is_visible():
                box = btn.bounding_box()
                if box:
                    more_btns.append({"btn": btn, "box": box})
        except Exception:
            pass

    # Match each card to its nearest more_vert button (same vertical position)
    for card in cards:
        if not card["box"]:
            continue
        card_y = card["box"]["y"]
        best = None
        best_dist = float("inf")
        for mb in more_btns:
            if mb["box"]:
                dist = abs(mb["box"]["y"] - card_y)
                if dist < best_dist:
                    best_dist = dist
                    best = mb["btn"]
        card["more_btn"] = best

    # Filter out cards without a more_vert button
    return [c for c in cards if c["more_btn"] is not None]


def main():
    parser = argparse.ArgumentParser(description="Download generated NotebookLM audio")
    parser.add_argument("--notebook-url", help="NotebookLM notebook URL")
    parser.add_argument("--notebook-id", help="Notebook ID from library")
    parser.add_argument("--index", type=int, default=None, help="Audio index to download (0-based)")
    parser.add_argument("--output", help="Output MP3 path")
    args = parser.parse_args()

    notebook_url = args.notebook_url
    if not notebook_url and args.notebook_id:
        nb = NotebookLibrary().get_notebook(args.notebook_id)
        if nb:
            notebook_url = nb["url"]
    if not notebook_url:
        active = NotebookLibrary().get_active_notebook()
        if active:
            notebook_url = active["url"]
            print(f"📚 Using active notebook: {active['name']}")
        else:
            print("❌ No active notebook.")
            return 1

    success = download_audio(notebook_url, pick_index=args.index, output_path=args.output)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
