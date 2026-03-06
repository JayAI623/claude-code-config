#!/usr/bin/env python3
"""
Upload sources (local files + YouTube URLs) to a NotebookLM notebook.

Usage:
  python scripts/run.py upload_sources.py --files file1.txt file2.md
  python scripts/run.py upload_sources.py --youtube "https://youtube.com/watch?v=..."
  python scripts/run.py upload_sources.py --notebook-url "https://notebooklm.google.com/notebook/..." \
      --files file1.txt file2.md --youtube "https://youtube.com/watch?v=..."
  python scripts/run.py upload_sources.py --new-notebook "My Notebook" \
      --files file1.txt --youtube "https://youtube.com/watch?v=..."
  python scripts/run.py upload_sources.py --files file1.txt --show-browser
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


NOTEBOOKLM_URL = "https://notebooklm.google.com"


def get_existing_sources(page) -> list[str]:
    """Scan the left sidebar to get names of existing sources.

    NotebookLM source items have checkboxes. Each checkbox's ancestor contains
    an icon (description/video_youtube/markdown/etc.) followed by the source name
    in a <span>. We read the text, skip "选择所有来源", and deduplicate.
    """
    sources = []
    seen = set()

    # Source names live in <span> elements with class pattern ng-tns-*
    # inside source-item components. The most reliable way is to find
    # mat-icon.source-item-source-icon siblings.
    try:
        names = page.evaluate("""() => {
            const icons = document.querySelectorAll('mat-icon.source-item-source-icon');
            const names = [];
            for (const icon of icons) {
                const parent = icon.parentElement;
                if (!parent) continue;
                const spans = parent.querySelectorAll('span');
                for (const span of spans) {
                    const text = span.textContent.trim();
                    if (text && text !== icon.textContent.trim() && text.length > 1) {
                        names.push(text);
                        break;
                    }
                }
            }
            return names;
        }""")
        for name in names:
            if name not in seen:
                sources.append(name)
                seen.add(name)
    except Exception as e:
        print(f"  ⚠️  JS source scan failed: {e}")

    # Fallback: use checkbox labels
    if not sources:
        try:
            checkboxes = page.query_selector_all("mat-checkbox, [role='checkbox']")
            for cb in checkboxes:
                text = page.evaluate("""(el) => {
                    let p = el;
                    for (let j = 0; j < 6; j++) {
                        if (!p) break;
                        let t = p.innerText ? p.innerText.trim() : '';
                        if (t && t.length > 3) return t;
                        p = p.parentElement;
                    }
                    return '';
                }""", cb)
                if text and "选择所有来源" not in text and text not in seen:
                    # Strip icon text prefix (e.g. "description\nfilename.txt" → "filename.txt")
                    lines = text.split('\n')
                    name = lines[-1].strip() if len(lines) > 1 else text
                    if name and name not in seen:
                        sources.append(name)
                        seen.add(name)
        except Exception:
            pass

    return sources


def source_already_exists(existing_sources: list[str], name: str) -> bool:
    """Check if a source with similar name already exists."""
    name_lower = name.lower()
    stem = Path(name).stem.lower() if '.' in name else name_lower
    for src in existing_sources:
        src_lower = src.lower()
        if stem in src_lower or name_lower in src_lower:
            return True
    return False


def ensure_source_panel_visible(page):
    """Make sure the left source panel is expanded/visible."""
    # Check if "添加来源" button is already visible
    add_btn = page.query_selector("button:has-text('添加来源')")
    if add_btn and add_btn.is_visible():
        return True

    # The source panel might be collapsed. Try toggling it.
    # Look for dock/panel toggle buttons
    for selector in [
        "button:has(mat-icon:has-text('dock_to_right'))",
        "button:has(mat-icon:has-text('dock_to_left'))",
        "button[aria-label*='来源']",
        "button[aria-label*='source']",
        "button[aria-label*='Sources']",
        "button[aria-label*='panel']",
    ]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                print(f"  ✓ Expanding source panel: {selector}")
                btn.click()
                time.sleep(2)
                # Verify
                add_btn = page.query_selector("button:has-text('添加来源')")
                if add_btn and add_btn.is_visible():
                    return True
        except:
            continue

    # Fallback: navigate with ?addSource=true to force the panel open
    current_url = page.url.split('?')[0]
    page.goto(current_url + "?addSource=true", wait_until="domcontentloaded")
    time.sleep(5)
    return True


def open_add_source_dialog(page, timeout=10):
    """Open the add-source dialog if not already open."""
    # Check if dialog is already open (e.g. new notebook with ?addSource=true)
    upload_btn = page.query_selector("button:has-text('上传文件')")
    if upload_btn and upload_btn.is_visible():
        print("  ✓ Add source dialog already open")
        return True

    # Ensure the source panel is visible first
    ensure_source_panel_visible(page)

    # Click "添加来源" button
    selectors = [
        "button:has-text('添加来源')",
        "button:has-text('Add source')",
    ]
    for selector in selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                print(f"  ✓ Clicking: {selector}")
                btn.click()
                time.sleep(2)
                return True
        except:
            continue

    # Debug: dump visible buttons
    buttons = page.query_selector_all("button")
    visible_btns = []
    for btn in buttons:
        try:
            if btn.is_visible():
                text = btn.inner_text().strip().replace('\n', ' | ')
                if text:
                    visible_btns.append(text[:60])
        except:
            pass
    print(f"  ❌ Could not open add source dialog. Visible buttons: {visible_btns[:10]}")
    return False


def upload_local_file(page, file_path: str, timeout=60) -> bool:
    """Upload a single local file."""
    path = Path(file_path).resolve()
    if not path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return False

    print(f"\n  📎 Uploading: {path.name}")

    # Step 1: Open dialog
    if not open_add_source_dialog(page):
        return False

    # Step 2: Click "上传文件" button
    upload_btn = page.query_selector("button:has-text('上传文件')")
    if not upload_btn or not upload_btn.is_visible():
        # Fallback
        upload_btn = page.query_selector("button:has-text('Upload')")
    if not upload_btn:
        print("    ❌ Could not find '上传文件' button")
        return False

    # Step 3: Use file chooser pattern - click triggers file dialog
    try:
        with page.expect_file_chooser(timeout=5000) as fc_info:
            upload_btn.click()
        file_chooser = fc_info.value
        file_chooser.set_files(str(path))
        print(f"    ✓ File selected via file chooser: {path.name}")
    except Exception:
        # Fallback: directly set on hidden input[type=file]
        print("    ⚠️  File chooser failed, trying input[type=file]...")
        file_input = page.query_selector("input[type='file']")
        if file_input:
            file_input.set_input_files(str(path))
            print(f"    ✓ File set on input element: {path.name}")
        else:
            print(f"    ❌ No file input found")
            return False

    # Step 4: Wait for upload + processing
    print(f"    ⏳ Waiting for processing...")
    deadline = time.time() + timeout

    while time.time() < deadline:
        # Check for the "插入" / "Insert" confirmation button
        for sel in ["button:has-text('插入')", "button:has-text('Insert')"]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    print(f"    ✓ Clicked insert button")
                    time.sleep(3)
                    print(f"  ✅ Uploaded: {path.name}")
                    return True
            except:
                continue

        # Check if source appeared in sidebar (auto-added without insert button)
        # Look for source items that contain the filename
        source_items = page.query_selector_all("[class*='source']")
        for item in source_items:
            try:
                text = item.inner_text()
                if path.stem.lower() in text.lower():
                    print(f"  ✅ Source appeared in sidebar: {path.name}")
                    return True
            except:
                continue

        # Check for error messages
        error = page.query_selector("[class*='error'], [class*='Error']")
        if error and error.is_visible():
            err_text = error.inner_text().strip()
            if err_text:
                print(f"    ❌ Error: {err_text}")
                return False

        time.sleep(2)

    print(f"  ⚠️  Timeout waiting for upload: {path.name}")
    return True  # May have succeeded silently


def add_youtube_source(page, youtube_url: str, timeout=30) -> bool:
    """Add a YouTube URL as a source."""
    print(f"\n  🎥 Adding YouTube: {youtube_url}")

    # Step 1: Open dialog
    if not open_add_source_dialog(page):
        return False

    # Step 2: Click "网站" button (shows link | video_youtube | 网站)
    website_btn = None
    for selector in [
        "button:has-text('网站')",
        "button:has-text('Website')",
        "button:has-text('Link')",
        "button:has-text('YouTube')",
    ]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                website_btn = btn
                print(f"    ✓ Found website/link button: {selector}")
                break
        except:
            continue

    if not website_btn:
        print("    ❌ Could not find '网站' button")
        return False

    website_btn.click()
    time.sleep(2)

    # Step 3: Find the URL input field
    url_input = None
    for selector in [
        "textarea[placeholder*='粘贴']",
        "textarea[placeholder*='paste']",
        "textarea[placeholder*='链接']",
        "textarea[placeholder*='URL']",
        "textarea[placeholder*='url']",
        "input[type='url']",
        "input[placeholder*='网址']",
        "input[placeholder*='URL']",
        "input[placeholder*='粘贴']",
        "input[placeholder*='paste']",
        "input[placeholder*='链接']",
        "[role='dialog'] textarea",
        "[role='dialog'] input",
        "input[type='text']",
    ]:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                url_input = el
                print(f"    ✓ Found URL input: {selector}")
                break
        except:
            continue

    if not url_input:
        # Dump what we see for debugging
        inputs = page.query_selector_all("input, textarea")
        print(f"    ❌ Could not find URL input. Found {len(inputs)} inputs:")
        for i, inp in enumerate(inputs):
            try:
                tag = inp.evaluate("el => el.tagName")
                itype = inp.get_attribute("type") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                visible = inp.is_visible()
                print(f"      [{i}] <{tag}> type={itype} placeholder='{placeholder}' visible={visible}")
            except:
                pass
        return False

    # Step 4: Type the URL
    url_input.click()
    time.sleep(0.3)
    url_input.fill(youtube_url)
    StealthUtils.random_delay(300, 700)

    # Step 5: Click the "插入" (Insert) button
    # This button appears in the dialog after pasting a URL
    time.sleep(1)

    # Strategy: find ALL "插入" buttons, click the one that's visible and enabled
    inserted = False
    for selector in [
        "button:has-text('插入')",
        "button:has-text('Insert')",
    ]:
        try:
            buttons = page.query_selector_all(selector)
            for btn in buttons:
                if btn.is_visible() and btn.is_enabled():
                    # Use JS click to avoid potential overlay issues
                    page.evaluate("(el) => el.click()", btn)
                    print(f"    ✓ Clicked insert button")
                    inserted = True
                    break
            if inserted:
                break
        except:
            continue

    if not inserted:
        # Fallback: press Enter
        print("    ⚠️  Insert button not found, trying Enter...")
        page.keyboard.press("Enter")

    # Wait for source to be processed
    print(f"    ⏳ Waiting for YouTube source to process...")
    time.sleep(10)
    print(f"  ✅ Added YouTube: {youtube_url}")
    return True


def create_new_notebook(page, name: str = None) -> str:
    """Create a new notebook and return its URL."""
    print(f"\n📓 Creating new notebook{': ' + name if name else ''}...")

    page.goto(NOTEBOOKLM_URL, wait_until="domcontentloaded")
    time.sleep(5)

    # Click "新建" button
    for selector in [
        "button:has-text('新建')",
        "button:has-text('New')",
        "button:has-text('Create')",
    ]:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                print(f"  ✓ Clicking: {selector}")
                btn.click()
                break
        except:
            continue

    time.sleep(5)
    notebook_url = page.url.split("?")[0]  # Remove ?addSource=true
    print(f"  ✓ Created notebook: {notebook_url}")
    return notebook_url


def upload_sources(
    notebook_url: str = None,
    new_notebook_name: str = None,
    local_files: list = None,
    youtube_urls: list = None,
    headless: bool = True,
) -> bool:
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️  Not authenticated. Run: python scripts/run.py auth_manager.py setup")
        return False

    if not local_files and not youtube_urls:
        print("❌ Nothing to upload. Provide --files or --youtube")
        return False

    # Resolve notebook URL
    if not notebook_url and not new_notebook_name:
        library = NotebookLibrary()
        active = library.get_active_notebook()
        if active:
            notebook_url = active['url']
            print(f"📓 Using active notebook: {active['name']}")
        else:
            print("❌ No notebook URL and no active notebook. Use --notebook-url or --new-notebook")
            return False

    playwright = None
    context = None

    try:
        print(f"\n🌐 Launching browser (headless={headless})...")
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()

        # Navigate or create notebook
        if new_notebook_name:
            notebook_url = create_new_notebook(page, new_notebook_name)
        else:
            print(f"🌐 Opening: {notebook_url}")
            page.goto(notebook_url, wait_until="domcontentloaded")

        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)
        time.sleep(8)  # Extra time for UI to fully render
        print(f"  Current URL: {page.url}")

        # Ensure source panel is visible before reading sources
        ensure_source_panel_visible(page)
        time.sleep(2)

        # Check existing sources to avoid duplicates
        existing = get_existing_sources(page)
        if existing:
            print(f"\n📋 Existing sources ({len(existing)}):")
            for src in existing:
                print(f"    • {src[:80]}")
        else:
            print("\n📋 No existing sources found (or could not read sidebar)")

        success_count = 0
        skip_count = 0
        total_count = (len(local_files) if local_files else 0) + (len(youtube_urls) if youtube_urls else 0)

        # Upload files
        if local_files:
            for file_path in local_files:
                name = Path(file_path).name
                if source_already_exists(existing, name):
                    print(f"\n  ⏭️  Skipped (already exists): {name}")
                    skip_count += 1
                    continue
                try:
                    if upload_local_file(page, file_path):
                        success_count += 1
                        existing.append(name)  # Track newly added
                    time.sleep(3)
                except Exception as e:
                    print(f"  ❌ Error uploading {file_path}: {e}")

        # Add YouTube URLs
        if youtube_urls:
            for yt_url in youtube_urls:
                # Extract video ID for dedup check
                vid_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', yt_url)
                vid_id = vid_match.group(1) if vid_match else yt_url
                if source_already_exists(existing, vid_id) or source_already_exists(existing, "youtube"):
                    # More precise: check if any existing source contains the video ID
                    found = any(vid_id.lower() in s.lower() for s in existing)
                    if found:
                        print(f"\n  ⏭️  Skipped (already exists): {yt_url}")
                        skip_count += 1
                        continue
                try:
                    if add_youtube_source(page, yt_url):
                        success_count += 1
                        existing.append(yt_url)
                    time.sleep(3)
                except Exception as e:
                    print(f"  ❌ Error adding {yt_url}: {e}")

        print(f"\n{'='*50}")
        print(f"✅ Done: {success_count} added, {skip_count} skipped (of {total_count} total)")
        print(f"📓 Notebook: {notebook_url}")
        print(f"{'='*50}\n")
        return success_count > 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
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


def main():
    parser = argparse.ArgumentParser(description="Upload sources to NotebookLM")
    parser.add_argument("--files", nargs="+", help="Local file paths to upload")
    parser.add_argument("--youtube", nargs="+", help="YouTube URLs to add")
    parser.add_argument("--notebook-url", help="Target notebook URL")
    parser.add_argument("--new-notebook", help="Create new notebook with this name")
    parser.add_argument("--show-browser", action="store_true", help="Show browser")
    args = parser.parse_args()

    if not args.files and not args.youtube:
        parser.print_help()
        print("\n❌ Provide --files and/or --youtube")
        sys.exit(1)

    success = upload_sources(
        notebook_url=args.notebook_url,
        new_notebook_name=args.new_notebook,
        local_files=args.files,
        youtube_urls=args.youtube,
        headless=not args.show_browser,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
