#!/usr/bin/env python3
"""
NotebookLM Studio Download
Lists ALL generated Studio artifacts (audio, slides, report, infographic, etc.)
and downloads the chosen one via the 更多 menu.

Usage:
  python scripts/run.py studio_download.py             # interactive list
  python scripts/run.py studio_download.py --index 0   # download first item
  python scripts/run.py studio_download.py --output ~/Downloads/file.mp3
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
from browser_utils import BrowserFactory

# Icon name → (type label, default extension)
ICON_TYPE_MAP = {
    "audio_magic_eraser": ("音频概览",  "mp3"),
    "subscriptions":       ("视频概览",  "mp4"),
    "flowchart":           ("思维导图",  "pdf"),
    "auto_tab_group":      ("报告",     "pdf"),
    "cards_star":          ("闪卡",     "pdf"),
    "grid_view":           ("信息图",   "png"),
    "slideshow":           ("演示文稿", "pdf"),
    "table_chart":         ("数据表格", "csv"),
    "tablet":              ("演示文稿", "pdf"),   # NotebookLM uses tablet icon for slides
    "quiz":                ("测验",     "pdf"),
}
# Fallback for any unknown icon
DEFAULT_EXT = "bin"

# Icons that are NOT generated artifacts — exclude these
EXCLUDED_ICONS = {"description", "article", "link", "insert_drive_file"}


def studio_download(notebook_url: str, pick_index: int = None, output_path: str = None) -> bool:
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️  Not authenticated. Run: python scripts/run.py auth_manager.py setup")
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

        # ── Scan all generated artifact cards ──
        cards = _find_all_artifact_cards(page)
        if not cards:
            print("❌ No generated artifacts found in Studio panel.")
            print("   Use studio_generate.py to generate something first.")
            return False

        # ── Show list ──
        print(f"\n📦 Found {len(cards)} artifact(s):\n")
        for i, c in enumerate(cards):
            dl_mark = "⬇️ " if c["has_download"] else "👁️ "
            print(f"  [{i}] {dl_mark}{c['type_label']:<8}  {c['title']}")
        print()

        # ── Pick ──
        idx = pick_index
        if idx is None:
            if len(cards) == 1:
                idx = 0
                print(f"Auto-selecting [0]")
            else:
                raw = input("Enter index to download: ").strip()
                idx = int(raw)

        if idx < 0 or idx >= len(cards):
            print(f"❌ Invalid index: {idx}")
            return False

        chosen = cards[idx]

        if not chosen["has_download"]:
            print(f"⚠️  '{chosen['type_label']}' may not support download. Trying anyway...")

        print(f"\n⬇️  Downloading: [{chosen['type_label']}] {chosen['title']}")

        # ── Open 更多 menu ──
        chosen["more_btn"].click()
        time.sleep(1)

        # ── Find download menu item ──
        download_item = _find_menu_download_item(page)
        if not download_item:
            # Show what's in the menu for debugging
            items = page.query_selector_all('[role="menuitem"], [role="option"]')
            visible = [el.inner_text().strip() for el in items if el.is_visible()]
            print(f"❌ No download option in menu. Available: {visible}")
            # Close menu
            page.keyboard.press("Escape")
            return False

        # ── Resolve output path ──
        if not output_path:
            output_path = _build_output_path(chosen)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # ── Trigger download ──
        with page.expect_download(timeout=60000) as dl_info:
            download_item.click()

        dl = dl_info.value

        # Use suggested filename if available and no explicit output
        suggested = dl.suggested_filename
        if suggested and not output_path.endswith(Path(suggested).suffix):
            # Fix extension from actual file
            ext = Path(suggested).suffix
            if ext and not output_path.lower().endswith(ext.lower()):
                output_path = str(Path(output_path).with_suffix(ext))

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_all_artifact_cards(page) -> list:
    """
    Scan Studio panel for all generated artifact cards.
    Pattern: a visible button containing an icon name + title + metadata,
    paired with a nearby more_vert (更多) button.
    """
    all_buttons = page.query_selector_all("button")

    # Collect more_vert buttons (candidates for artifact menus)
    more_btns = []
    for btn in all_buttons:
        try:
            if not btn.is_visible(): continue
            aria = btn.get_attribute("aria-label") or ""
            text = btn.inner_text().strip()
            if aria == "更多" or text == "more_vert":
                box = btn.bounding_box()
                if box:
                    more_btns.append({"btn": btn, "box": box})
        except Exception:
            pass

    # Collect artifact card buttons: contain known icon names + "个来源"
    known_icons = list(ICON_TYPE_MAP.keys())
    cards = []

    for btn in all_buttons:
        try:
            if not btn.is_visible(): continue
            text = btn.inner_text().strip()

            # Must contain source metadata (个来源) to be a generated card
            if "个来源" not in text:
                continue

            # Skip source document cards (tablet, description, etc.)
            if any(ex_icon in text for ex_icon in EXCLUDED_ICONS):
                continue

            # Identify type by icon name in text
            detected_icon = None
            for icon in known_icons:
                if icon in text:
                    detected_icon = icon
                    break

            # Skip cards with completely unknown icons (likely non-artifact UI elements)
            if detected_icon is None and not any(kw in text for kw in ["概览", "报告", "测验", "闪卡", "导图", "文稿", "表格", "信息图"]):
                continue

            type_label, default_ext = ICON_TYPE_MAP.get(detected_icon, ("未知", DEFAULT_EXT))

            # Extract title: text before "· N 个来源"
            title = _extract_title(text, detected_icon)

            box = btn.bounding_box()

            # Find nearest more_vert button (within 60px vertically)
            more_btn = _nearest_more_btn(box, more_btns, max_dist_y=60)

            # Check if download is likely available (has a more_vert)
            has_download = more_btn is not None

            cards.append({
                "title":       title,
                "type_label":  type_label,
                "icon":        detected_icon,
                "ext":         default_ext,
                "card_btn":    btn,
                "more_btn":    more_btn,
                "has_download": has_download,
                "box":         box,
            })
        except Exception:
            pass

    return cards


def _extract_title(text: str, icon: str) -> str:
    """Extract clean title from card button text."""
    # Remove icon name prefix
    if icon:
        text = text.replace(icon, "", 1)

    # Remove trailing metadata: "· N 个来源 · X 分钟前 ..." or "N 个来源 ..."
    text = re.sub(r'\s*·?\s*\d+\s*个来源.*', '', text, flags=re.DOTALL)

    # Remove trailing icon texts like "play_arrow", "more_vert"
    text = re.sub(r'\b(play_arrow|more_vert|play_arr|file_download)\b.*', '', text, flags=re.DOTALL)

    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text or "未命名"


def _nearest_more_btn(card_box, more_btns: list, max_dist_y: int = 60):
    """Return the more_vert button closest in Y to the card box."""
    if not card_box:
        return None
    card_y = card_box["y"] + card_box["height"] / 2
    best, best_dist = None, float("inf")
    for mb in more_btns:
        mb_y = mb["box"]["y"] + mb["box"]["height"] / 2
        dist = abs(mb_y - card_y)
        if dist < best_dist and dist <= max_dist_y:
            best_dist = dist
            best = mb["btn"]
    return best


def _find_menu_download_item(page):
    """Find visible download menu item after 更多 is clicked."""
    for text in ["下载", "Download", "download"]:
        try:
            el = page.wait_for_selector(
                f'[role="menuitem"]:has-text("{text}"), a:has-text("{text}")',
                timeout=4000, state="visible"
            )
            if el:
                return el
        except Exception:
            pass
    return None


def _build_output_path(card: dict) -> str:
    """Build a clean output file path from card metadata."""
    clean = re.sub(r'\s+', ' ', card["title"]).strip()
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', clean)[:40].strip('_')
    ext = card["ext"]
    return str(Path.home() / "Downloads" / f"{safe}.{ext}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download any generated NotebookLM Studio artifact")
    parser.add_argument("--notebook-url", help="NotebookLM notebook URL")
    parser.add_argument("--notebook-id",  help="Notebook ID from library")
    parser.add_argument("--index", type=int, default=None, help="Artifact index (0-based); interactive if omitted")
    parser.add_argument("--output", help="Output file path (auto-named if omitted)")
    args = parser.parse_args()

    # Resolve notebook URL
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
            print("❌ No active notebook. Specify --notebook-url or --notebook-id")
            return 1

    success = studio_download(notebook_url, pick_index=args.index, output_path=args.output)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
