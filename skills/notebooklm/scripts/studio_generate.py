#!/usr/bin/env python3
"""
NotebookLM Studio Generator
Generate any Studio feature (audio, report, mindmap, slides, etc.) and download.

Usage:
  python scripts/run.py studio_generate.py --list
  python scripts/run.py studio_generate.py --feature audio
  python scripts/run.py studio_generate.py --feature report --output ~/Downloads/report.pdf
  python scripts/run.py studio_generate.py   # interactive menu
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

# ── Feature definitions ────────────────────────────────────────────────────────
# icon: mat-icon text inside basic-create-artifact-button
# aria_customize: aria-label of the edit/customize button
# downloadable: whether a download button appears after generation
FEATURES = {
    "audio":       {"label": "音频概览",  "icon": "audio_magic_eraser", "aria_customize": "自定义音频概览",  "downloadable": True,  "ext": "mp3"},
    "video":       {"label": "视频概览",  "icon": "subscriptions",       "aria_customize": None,           "downloadable": False, "ext": None},
    "mindmap":     {"label": "思维导图",  "icon": "flowchart",           "aria_customize": None,           "downloadable": False, "ext": None},
    "report":      {"label": "报告",      "icon": "auto_tab_group",      "aria_customize": None,           "downloadable": True,  "ext": "pdf"},
    "flashcards":  {"label": "闪卡",      "icon": "cards_star",          "aria_customize": "自定义抽认卡",  "downloadable": False, "ext": None},
    "infographic": {"label": "信息图",    "icon": None,                  "aria_customize": "自定义信息图",  "downloadable": True,  "ext": "png"},
    "slides":      {"label": "演示文稿",  "icon": "tablet",              "aria_customize": "自定义演示文稿","downloadable": True,  "ext": "pdf"},
    "table":       {"label": "数据表格",  "icon": None,                  "aria_customize": "自定义数据表格","downloadable": True,  "ext": "csv"},
    "quiz":        {"label": "测验",      "icon": None,                  "aria_customize": "自定义测验",    "downloadable": False, "ext": None},
}


def list_features():
    print("\n📋 Available Studio features:\n")
    print(f"  {'Key':<12} {'Label':<10} {'Download?':<10} {'Format'}")
    print("  " + "─" * 45)
    for key, f in FEATURES.items():
        dl = "✅ yes" if f["downloadable"] else "👁️  view"
        ext = f["ext"] or "—"
        print(f"  {key:<12} {f['label']:<10} {dl:<10} {ext}")
    print()


def interactive_menu():
    list_features()
    keys = list(FEATURES.keys())
    print("Choose a feature (type the key):")
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k:<12} — {FEATURES[k]['label']}")
    choice = input("\nEnter key or number: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(keys):
            return keys[idx]
    if choice in FEATURES:
        return choice
    print(f"❌ Unknown choice: {choice}")
    return None


def studio_generate(notebook_url: str, feature_key: str, output_path: str = None) -> bool:
    feature = FEATURES[feature_key]
    print(f"\n🎨 Generating: {feature['label']} ({feature_key})")

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

        # ── Already generated? ──
        if feature["downloadable"]:
            dl_btn = _find_download_button(page)
            if dl_btn:
                print("✅ Already generated — downloading directly...")
                return _do_download(page, dl_btn, output_path, feature)

        # ── Find the right artifact button ──
        artifact_btn = _find_artifact_button(page, feature)
        if not artifact_btn:
            print(f"❌ Could not find '{feature['label']}' button in Studio panel")
            _dump_studio(page)
            return False

        # ── Click to generate (or open customize) ──
        print(f"▶  Clicking '{feature['label']}'...")
        _safe_click(page, artifact_btn)
        time.sleep(3)

        # ── Wait for spinner or completion ──
        _wait_and_check(page, feature, output_path)
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass


def _find_artifact_button(page, feature: dict):
    """
    Find the basic-create-artifact-button for the given feature.
    Strategy: match by icon text OR by aria_customize sibling OR by label text.
    """
    all_btns = page.query_selector_all("basic-create-artifact-button")

    for btn in all_btns:
        try:
            inner = btn.inner_text()
            # Match by icon name
            if feature["icon"] and feature["icon"] in inner:
                return btn
            # Match by Chinese label
            if feature["label"] in inner:
                return btn
        except Exception:
            pass

    # Fallback: match by customize button aria-label nearby
    if feature["aria_customize"]:
        try:
            customize_btn = page.query_selector(f'button[aria-label="{feature["aria_customize"]}"]')
            if customize_btn:
                # Walk up DOM to find the ancestor basic-create-artifact-button
                ancestor = page.evaluate("""(el) => {
                    let p = el.parentElement;
                    while (p) {
                        if (p.tagName.toLowerCase() === 'basic-create-artifact-button') return p;
                        p = p.parentElement;
                    }
                    return null;
                }""", customize_btn)
                if ancestor:
                    return ancestor
                # Return the container div next to the customize button as fallback
                return customize_btn
        except Exception:
            pass

    return None


def _wait_and_check(page, feature: dict, output_path: str):
    """Wait for generation spinner to disappear, then try to download."""
    label = feature["label"]
    spinner_text = f"正在生成{label}"

    print(f"⏳ Waiting for '{label}' generation (up to 10 min)...")
    deadline = time.time() + 600
    tick = 0

    while time.time() < deadline:
        # Check for spinner (still generating)
        spinner = _find_spinner(page, spinner_text)

        # Check for download button (done)
        if feature["downloadable"]:
            dl_btn = _find_download_button(page)
            if dl_btn and not spinner:
                print(f"✅ '{label}' is ready!")
                if output_path:
                    _do_download(page, dl_btn, output_path, feature)
                else:
                    print("ℹ️  No --output specified. File not downloaded.")
                return

        # Not downloadable — just wait for spinner to disappear
        if not feature["downloadable"] and not spinner:
            print(f"✅ '{label}' generated (displayed in browser).")
            print("ℹ️  This feature is view-only and cannot be downloaded automatically.")
            # Keep browser open so user can interact
            print("🕐 Browser will close in 60s. Press Ctrl+C to exit early.")
            time.sleep(60)
            return

        tick += 1
        if tick % 6 == 0:
            elapsed = int(time.time() - (deadline - 600))
            status = "generating..." if spinner else "waiting for download button..."
            print(f"   ⏳ {elapsed}s — {status}")

        time.sleep(5)

    print(f"❌ Timed out after 10 min.")
    _dump_studio(page)


def _find_spinner(page, spinner_text: str):
    """Check if a generation spinner with the given text is visible."""
    try:
        buttons = page.query_selector_all("button")
        for b in buttons:
            try:
                text = b.inner_text().strip()
                if spinner_text in text:
                    return b
            except Exception:
                pass
    except Exception:
        pass
    return None


def _find_download_button(page):
    """Find a visible download button using multiple selectors."""
    selectors = [
        'button[aria-label*="下载"]',
        'button[aria-label*="Download" i]',
        'button[aria-label*="download" i]',
        'button:has(mat-icon:has-text("file_download"))',
        'button:has(mat-icon:has-text("download"))',
        '[data-testid*="download"]',
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue
    return None


def _do_download(page, dl_btn, output_path: str, feature: dict) -> bool:
    if not output_path:
        ext = feature.get("ext") or "bin"
        output_path = str(Path.home() / "Downloads" / f"notebooklm-{feature['label']}.{ext}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"⬇️  Downloading to: {output_path}")

    try:
        with page.expect_download(timeout=30000) as dl_info:
            _safe_click(page, dl_btn)
        dl = dl_info.value
        dl.save_as(output_path)
        size = Path(output_path).stat().st_size / 1024
        print(f"✅ Saved ({size:.0f} KB): {output_path}")
        return True
    except Exception as e:
        print(f"  ⚠️ Direct download failed: {e}")

    # Fallback: overflow menu
    try:
        for aria in ["更多", "More", "more"]:
            m = page.query_selector(f'button[aria-label="{aria}"]')
            if m and m.is_visible():
                _safe_click(page, m)
                time.sleep(0.8)
                with page.expect_download(timeout=20000) as dl_info:
                    item = page.wait_for_selector(
                        '[role="menuitem"]:has-text("下载"), [role="menuitem"]:has-text("Download")',
                        timeout=5000, state="visible"
                    )
                    _safe_click(page, item)
                dl = dl_info.value
                dl.save_as(output_path)
                print(f"✅ Saved via menu: {output_path}")
                return True
    except Exception as e:
        print(f"  ⚠️ Menu fallback failed: {e}")

    return False


def _safe_click(page, element):
    try:
        element.click(timeout=8000)
    except Exception:
        try:
            page.evaluate("(el) => el.click()", element)
        except Exception as e:
            print(f"  ⚠️ Click failed: {e}")


def _dump_studio(page):
    """Debug: show visible Studio-area buttons."""
    try:
        buttons = page.query_selector_all("button")
        for b in buttons:
            try:
                if b.is_visible():
                    t = b.inner_text().strip().replace("\n", " ")[:60]
                    a = b.get_attribute("aria-label") or ""
                    if t or a:
                        print(f"  btn: {repr(t):<40} aria={repr(a)}")
            except Exception:
                pass
    except Exception:
        pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate any NotebookLM Studio feature")
    parser.add_argument("--feature", choices=list(FEATURES.keys()), help="Feature to generate")
    parser.add_argument("--list", action="store_true", help="List all available features")
    parser.add_argument("--notebook-url", help="NotebookLM notebook URL")
    parser.add_argument("--notebook-id", help="Notebook ID from library")
    parser.add_argument("--output", help="Output file path (auto-named if omitted)")
    args = parser.parse_args()

    if args.list:
        list_features()
        return 0

    # Resolve notebook URL
    notebook_url = args.notebook_url
    if not notebook_url and args.notebook_id:
        nb = NotebookLibrary().get_notebook(args.notebook_id)
        if nb:
            notebook_url = nb["url"]
        else:
            print(f"❌ Notebook '{args.notebook_id}' not found")
            return 1

    if not notebook_url:
        active = NotebookLibrary().get_active_notebook()
        if active:
            notebook_url = active["url"]
            print(f"📚 Using active notebook: {active['name']}")
        else:
            print("❌ No active notebook. Specify --notebook-url or --notebook-id")
            return 1

    # Resolve feature
    feature_key = args.feature
    if not feature_key:
        feature_key = interactive_menu()
    if not feature_key:
        return 1

    success = studio_generate(notebook_url, feature_key, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
