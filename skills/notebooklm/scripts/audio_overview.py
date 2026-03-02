#!/usr/bin/env python3
"""
NotebookLM Audio Overview Generator & Downloader
Generates Audio Overview (Chinese) and downloads the MP3

Selectors discovered via debug_ui.py:
  - Audio section: BASIC-CREATE-ARTIFACT-BUTTON containing 'audio_magic_eraser'
  - Customize btn: button[aria-label='自定义音频概览']
  - Generate btn:  appears inside the artifact panel after clicking the main button
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


def generate_and_download_audio(notebook_url: str, output_path: str, language: str = "Chinese") -> bool:
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

        print(f"🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)

        print("⏳ Waiting for Studio panel (10s)...")
        time.sleep(10)

        # ── Step 1: Check if audio already generated (download button visible) ──
        download_button = _find_download_button(page)
        if download_button:
            print("✅ Audio already exists — downloading directly...")
            return _do_download(page, download_button, output_path)

        # ── Step 2: Click the Audio Overview main button to expand / trigger ──
        print("🎙️  Clicking 音频概览 button...")
        audio_btn = page.query_selector("basic-create-artifact-button")

        # If multiple artifact buttons, find the audio one
        all_artifact_btns = page.query_selector_all("basic-create-artifact-button")
        for btn in all_artifact_btns:
            try:
                if "audio_magic_eraser" in btn.inner_text() or "音频概览" in btn.inner_text():
                    audio_btn = btn
                    break
            except Exception:
                pass

        if not audio_btn:
            print("❌ 音频概览 button not found in Studio panel")
            return False

        # Click the main area (not the edit icon)
        try:
            # Click the span/text area inside, avoiding the edit button
            span = audio_btn.query_selector("span")
            if span:
                span.click()
            else:
                audio_btn.click()
        except Exception as e:
            print(f"  ⚠️ Click error: {e}, trying JS...")
            page.evaluate("(el) => el.click()", audio_btn)

        print("  ⏳ Waiting for generation panel to open (3s)...")
        time.sleep(3)

        # ── Step 3: Handle language customization ──
        # Click 自定义音频概览 edit button to open customize dialog
        customize_btn = page.query_selector("button[aria-label='自定义音频概览']")
        if customize_btn and language == "Chinese":
            print(f"🌐 Opening customize dialog for language: {language}...")
            customize_btn.click()
            time.sleep(2)

            # Look for language selector inside the dialog
            _set_language_in_dialog(page, language)

            # Find and click Generate inside the dialog
            gen_in_dialog = _find_generate_btn_in_dialog(page)
            if gen_in_dialog:
                print("  ▶ Clicking Generate in customize dialog...")
                gen_in_dialog.click()
                time.sleep(2)
            else:
                # Close dialog and fall through to find generate button
                page.keyboard.press("Escape")
                time.sleep(1)

        # ── Step 4: Find and click standalone Generate button ──
        generate_btn = _wait_for_generate_btn(page, timeout=15)
        if generate_btn:
            print("  ▶ Clicking Generate...")
            try:
                generate_btn.click(timeout=5000)
            except Exception:
                page.evaluate("(el) => el.click()", generate_btn)
            time.sleep(2)

            # Handle any confirmation modal
            _handle_confirm_modal(page)

        # ── Step 5: Wait for audio to be generated ──
        print("⏳ Waiting for Audio Overview generation (this may take 2–8 min)...")
        deadline = time.time() + 600
        tick = 0
        while time.time() < deadline:
            download_button = _find_download_button(page)
            if download_button:
                print("✅ Audio Overview is ready!")
                break
            tick += 1
            if tick % 6 == 0:
                elapsed = int(time.time() - (deadline - 600))
                print(f"   ⏳ {elapsed}s elapsed, still generating...")
            time.sleep(5)

        if not download_button:
            print("❌ Timed out waiting for generation.")
            _dump_buttons(page)
            return False

        return _do_download(page, download_button, output_path)

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_download_button(page):
    selectors = [
        'button[aria-label*="下载" i]',
        'button[aria-label*="Download" i]',
        'button[aria-label*="download" i]',
        'button:has(mat-icon:has-text("file_download"))',
        'button:has(mat-icon:has-text("download"))',
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue
    return None


def _wait_for_generate_btn(page, timeout=15):
    """Wait up to `timeout` seconds for a visible, enabled Generate button."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for text in ["生成", "Generate"]:
            try:
                el = page.query_selector(f'button:has-text("{text}")')
                if el and el.is_visible():
                    disabled = page.evaluate("(e) => e.disabled || e.hasAttribute('disabled')", el)
                    if not disabled:
                        return el
            except Exception:
                pass
        time.sleep(1)
    return None


def _find_generate_btn_in_dialog(page):
    """Find Generate button specifically inside a dialog."""
    for text in ["生成", "Generate"]:
        try:
            els = page.query_selector_all(f'button:has-text("{text}")')
            for el in els:
                if el.is_visible():
                    in_dialog = page.evaluate("""(el) => {
                        let p = el;
                        while (p) {
                            const role = p.getAttribute && p.getAttribute('role');
                            const tag = p.tagName && p.tagName.toUpperCase();
                            if (role === 'dialog' || tag === 'DIALOG' || tag === 'MAT-DIALOG-CONTAINER') return true;
                            p = p.parentElement;
                        }
                        return false;
                    }""", el)
                    if in_dialog:
                        return el
        except Exception:
            pass
    return None


def _handle_confirm_modal(page):
    """Click Generate inside a confirmation modal if it appears."""
    time.sleep(1.5)
    btn = _find_generate_btn_in_dialog(page)
    if btn:
        print("  📋 Confirming modal...")
        btn.click()
        time.sleep(1)


def _set_language_in_dialog(page, language: str):
    """Try to set language inside the customize dialog."""
    lang_texts = {
        "Chinese": ["中文", "普通话", "Mandarin Chinese", "Chinese"],
    }
    targets = lang_texts.get(language, [language])

    # Try <select>
    try:
        sel = page.query_selector("select")
        if sel:
            for opt in targets:
                try:
                    sel.select_option(label=opt)
                    print(f"  ✓ Language set via <select>: {opt}")
                    return
                except Exception:
                    pass
    except Exception:
        pass

    # Try radio buttons or chips
    for text in targets:
        try:
            el = page.query_selector(f'[role="radio"]:has-text("{text}"), mat-radio-button:has-text("{text}")')
            if el and el.is_visible():
                el.click()
                print(f"  ✓ Language selected: {text}")
                return
        except Exception:
            pass

    print(f"  ⚠️ Could not set language — proceeding with default")


def _do_download(page, download_button, output_path: str) -> bool:
    print(f"⬇️  Downloading audio to: {output_path}")
    try:
        with page.expect_download(timeout=30000) as dl_info:
            try:
                download_button.click(timeout=5000)
            except Exception:
                page.evaluate("(el) => el.click()", download_button)
        dl = dl_info.value
        dl.save_as(output_path)
        size = Path(output_path).stat().st_size / 1024
        print(f"✅ Saved ({size:.0f} KB): {output_path}")
        return True
    except Exception as e:
        print(f"  ⚠️ Download failed: {e}")

    # Fallback: try overflow menu
    try:
        for aria in ["更多", "More", "more"]:
            menu_btn = page.query_selector(f'button[aria-label="{aria}"]')
            if menu_btn and menu_btn.is_visible():
                menu_btn.click()
                time.sleep(0.8)
                with page.expect_download(timeout=20000) as dl_info:
                    dl_item = page.wait_for_selector(
                        '[role="menuitem"]:has-text("下载"), [role="menuitem"]:has-text("Download")',
                        timeout=5000, state="visible"
                    )
                    dl_item.click()
                dl = dl_info.value
                dl.save_as(output_path)
                print(f"✅ Saved via menu: {output_path}")
                return True
    except Exception as e:
        print(f"  ⚠️ Menu fallback failed: {e}")

    return False


def _dump_buttons(page):
    try:
        buttons = page.query_selector_all("button")
        texts = [b.inner_text().strip() for b in buttons if b.is_visible()]
        print(f"  Visible buttons: {[t for t in texts if t][:20]}")
    except Exception:
        pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate & download NotebookLM Audio Overview")
    parser.add_argument("--notebook-url", help="NotebookLM notebook URL")
    parser.add_argument("--notebook-id", help="Notebook ID from library")
    parser.add_argument("--output", help="Output MP3 path (default: ~/Downloads/notebooklm-audio.mp3)")
    parser.add_argument("--language", default="Chinese", help="Language: Chinese or English (default: Chinese)")
    args = parser.parse_args()

    notebook_url = args.notebook_url
    if not notebook_url and args.notebook_id:
        library = NotebookLibrary()
        nb = library.get_notebook(args.notebook_id)
        if nb:
            notebook_url = nb["url"]
        else:
            print(f"❌ Notebook '{args.notebook_id}' not found")
            return 1

    if not notebook_url:
        library = NotebookLibrary()
        active = library.get_active_notebook()
        if active:
            notebook_url = active["url"]
            print(f"📚 Using active notebook: {active['name']}")
        else:
            print("❌ No active notebook.")
            return 1

    output_path = args.output or str(Path.home() / "Downloads" / "notebooklm-audio.mp3")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"\n🎙️  NotebookLM Audio Overview")
    print(f"📚 Notebook : {notebook_url}")
    print(f"💾 Output   : {output_path}")
    print(f"🌐 Language : {args.language}")
    print()

    success = generate_and_download_audio(notebook_url, output_path, language=args.language)
    if success:
        print(f"\n🎉 Done! Audio saved to: {output_path}")
        return 0
    else:
        print("\n❌ Audio generation/download failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
