#!/usr/bin/env python3
"""
Oracle Cloud console browser automation (Patchright)
Handles: login detection, ARM instance creation, IP extraction
"""

import re
import sys
import time
from pathlib import Path

from patchright.sync_api import sync_playwright
from rich.console import Console
from rich.prompt import Prompt

sys.path.insert(0, str(Path(__file__).parent))
from config import OCI_URL, OCI_INSTANCES_URL, BROWSER_PROFILE_DIR, BROWSER_ARGS, USER_AGENT

console = Console()


def _safe_click(page, element):
    """Click with JS fallback (from playwright-disabled-element-click skill)."""
    try:
        element.click(timeout=8000)
    except Exception:
        try:
            page.evaluate("(el) => el.click()", element)
        except Exception as e:
            console.print(f"  [yellow]⚠ Click failed: {e}[/yellow]")


def _try_fill(page, selectors, value, label="field"):
    """Try a list of CSS selectors, fill the first one found."""
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.triple_click()
                el.fill(value)
                console.print(f"  [green]✓[/green] {label} set")
                return True
        except Exception:
            pass
    console.print(f"  [yellow]⚠ Could not locate {label} automatically.[/yellow]")
    return False


def _try_click_text(page, texts, label="button"):
    """Try clicking a button by its text content."""
    for text in texts if isinstance(texts, list) else [texts]:
        try:
            btn = page.query_selector(f'button:has-text("{text}")')
            if btn and btn.is_visible():
                _safe_click(page, btn)
                console.print(f"  [green]✓[/green] Clicked '{text}'")
                return True
        except Exception:
            pass
    console.print(f"  [yellow]⚠ Could not find {label} — please click it manually.[/yellow]")
    input("  Press Enter to continue...")
    return False


def run_oracle_setup(cfg: dict) -> str:
    """
    Open Oracle Cloud console, guide login, automate instance creation.
    Returns the public IP of the new instance (or empty string on failure).
    """
    console.print("\n[bold cyan]🌐 Oracle Cloud Instance Creation[/bold cyan]")
    console.print("[dim]Browser will open. Please log in when prompted.[/dim]\n")

    playwright = sync_playwright().start()
    context = None

    try:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            channel="chrome",
            headless=False,
            no_viewport=True,
            ignore_default_args=["--enable-automation"],
            user_agent=USER_AGENT,
            args=BROWSER_ARGS,
        )
        page = context.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        # ── Step 1: Navigate and wait for login ──────────────────────────────
        console.print("📂 Opening Oracle Cloud console...")
        page.goto(OCI_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Detect if already logged in (URL won't be on sign-in page)
        current = page.url
        if "sign-in" in current or "cloud.oracle.com" == current.rstrip("/"):
            console.print("\n[yellow]⏳ Please log in to Oracle Cloud in the browser.[/yellow]")
            console.print("   (The wizard continues automatically after login)\n")
            # Wait up to 5 min for URL to change away from sign-in
            try:
                page.wait_for_url(
                    re.compile(r"cloud\.oracle\.com/(?!sign-in|$)"),
                    timeout=300000
                )
            except Exception:
                console.print("[yellow]Could not detect login. Continuing...[/yellow]")

        console.print("[green]✓[/green] Logged in!\n")
        time.sleep(2)

        # ── Step 2: Navigate to Compute Instances ────────────────────────────
        console.print("📂 Navigating to Compute → Instances...")
        page.goto(OCI_INSTANCES_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        # ── Step 3: Click "Create instance" ─────────────────────────────────
        console.print("🖱  Clicking 'Create instance'...")
        try:
            btn = page.wait_for_selector(
                'button:has-text("Create instance"), a:has-text("Create instance")',
                timeout=15000
            )
            _safe_click(page, btn)
            time.sleep(4)
        except Exception:
            console.print("[yellow]⚠ Could not find 'Create instance' button.[/yellow]")
            input("  Please click it manually, then press Enter...")

        # ── Step 4: Instance name ────────────────────────────────────────────
        instance_name = cfg.get("instance_name", "openclaw-server")
        console.print(f"✏️  Setting instance name: {instance_name}")
        _try_fill(
            page,
            [
                'input[placeholder*="name" i]',
                'input[id*="display-name" i]',
                'input[id*="name" i]',
            ],
            instance_name,
            "instance name",
        )
        time.sleep(1)

        # ── Step 5: Change image → Ubuntu 22.04 ─────────────────────────────
        console.print("🐧 Selecting Ubuntu 22.04 image...")
        changed = _try_click_text(page, "Change image", "Change image button")
        if changed:
            time.sleep(3)
            # Select Ubuntu
            for sel in [
                'label:has-text("Ubuntu")',
                'input[value="Ubuntu"]',
                'div:has-text("Ubuntu Minimal 22.04")',
            ]:
                el = page.query_selector(sel)
                if el:
                    _safe_click(page, el)
                    time.sleep(1)
                    break

            # Select 22.04 version if multiple options
            for sel in ['label:has-text("22.04")', 'option:has-text("22.04")']:
                el = page.query_selector(sel)
                if el:
                    _safe_click(page, el)
                    time.sleep(1)
                    break

            # Confirm image selection
            for text in ["Select image", "Select"]:
                btn = page.query_selector(f'button:has-text("{text}")')
                if btn and btn.is_visible():
                    _safe_click(page, btn)
                    time.sleep(2)
                    break
        else:
            console.print("  Please select Ubuntu 22.04 manually.")

        # ── Step 6: Change shape → Ampere A1.Flex (4 OCPU, 24 GB) ──────────
        console.print("⚙️  Selecting Ampere ARM shape (VM.Standard.A1.Flex, 4 OCPU, 24 GB)...")
        changed = _try_click_text(page, "Change shape", "Change shape button")
        if changed:
            time.sleep(3)
            # Click Ampere radio/tab
            for sel in [
                'label:has-text("Ampere")',
                'input[value="AMPERE"]',
                'div[data-value="AMPERE"]',
                'span:has-text("Ampere")',
            ]:
                el = page.query_selector(sel)
                if el:
                    _safe_click(page, el)
                    time.sleep(1)
                    break

            # Select VM.Standard.A1.Flex
            for sel in [
                'label:has-text("VM.Standard.A1.Flex")',
                'input[value="VM.Standard.A1.Flex"]',
                'td:has-text("VM.Standard.A1.Flex")',
            ]:
                el = page.query_selector(sel)
                if el:
                    _safe_click(page, el)
                    time.sleep(1)
                    break

            # OCPU = 4
            _try_fill(
                page,
                [
                    'input[aria-label*="OCPU" i]',
                    'input[id*="ocpu" i]',
                    'input[name*="ocpu" i]',
                ],
                "4",
                "OCPU count",
            )
            time.sleep(0.5)

            # Memory = 24
            _try_fill(
                page,
                [
                    'input[aria-label*="memory" i]',
                    'input[aria-label*="GB" i]',
                    'input[id*="memory" i]',
                    'input[name*="memory" i]',
                ],
                "24",
                "memory (GB)",
            )
            time.sleep(0.5)

            # Confirm shape
            for text in ["Select shape", "Select"]:
                btn = page.query_selector(f'button:has-text("{text}")')
                if btn and btn.is_visible():
                    _safe_click(page, btn)
                    time.sleep(2)
                    break
        else:
            console.print("  Please select VM.Standard.A1.Flex (4 OCPU, 24 GB) manually.")

        # ── Step 7: Add SSH public key ────────────────────────────────────────
        pub_key = cfg.get("pub_key", "")
        if pub_key:
            console.print("🔑 Adding SSH public key...")
            # Select "Paste public keys" option
            for sel in [
                'label:has-text("Paste public keys")',
                'input[value="KEYFILE"]',
                'label:has-text("Paste")',
            ]:
                el = page.query_selector(sel)
                if el:
                    _safe_click(page, el)
                    time.sleep(1)
                    break

            filled = _try_fill(
                page,
                [
                    'textarea[aria-label*="SSH" i]',
                    'textarea[aria-label*="key" i]',
                    'textarea[placeholder*="SSH" i]',
                    'textarea[placeholder*="key" i]',
                    'textarea',
                ],
                pub_key,
                "SSH public key",
            )
            if not filled:
                console.print(f"\n  [yellow]Please paste this SSH public key manually:[/yellow]")
                console.print(f"  [dim]{pub_key}[/dim]\n")
                input("  Press Enter when done...")
        else:
            console.print("[yellow]⚠ No SSH key found in config. Please add one manually.[/yellow]")
            input("  Press Enter when done...")

        # ── Step 8: Create ────────────────────────────────────────────────────
        console.print("\n🚀 Submitting instance creation...")
        created = False
        for sel in [
            'button[type="submit"]',
            'button:has-text("Create"):not(:has-text("instance"))',
            'button.oci-button-primary:has-text("Create")',
        ]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                _safe_click(page, btn)
                created = True
                console.print("[green]✓[/green] Instance creation submitted!")
                break

        if not created:
            console.print("[yellow]⚠ Could not click 'Create'. Please click it manually.[/yellow]")
            input("  Press Enter when done...")

        # ── Step 9: Wait for IP ───────────────────────────────────────────────
        console.print("\n⏳ Waiting for instance to provision and get public IP...")
        console.print("   [dim](Usually takes 2–5 minutes)[/dim]")

        ip = _poll_for_public_ip(page, timeout_sec=600)

        if not ip:
            console.print("\n[yellow]Could not auto-detect IP.[/yellow]")
            console.print("  In the Oracle Cloud console, copy the Public IP address.")
            ip = Prompt.ask("  Paste the Public IP address here")

        console.print(f"\n[green]✓[/green] Instance IP: [bold cyan]{ip}[/bold cyan]")
        return ip

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return ""
    except Exception as e:
        console.print(f"\n[red]Browser error: {e}[/red]")
        import traceback
        traceback.print_exc()
        ip = Prompt.ask("\nPlease enter your Oracle Cloud instance IP manually")
        return ip
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        try:
            playwright.stop()
        except Exception:
            pass


def _poll_for_public_ip(page, timeout_sec=600) -> str:
    """Poll the current page for a public IPv4 address (non-private)."""
    deadline = time.time() + timeout_sec
    tick = 0
    while time.time() < deadline:
        try:
            content = page.content()
            # Find all IPv4 addresses
            candidates = re.findall(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', content)
            for ip in candidates:
                parts = ip.split(".")
                if not all(0 <= int(p) <= 255 for p in parts):
                    continue
                # Skip private/loopback ranges
                if ip.startswith(("10.", "172.", "192.168.", "127.", "0.")):
                    continue
                return ip
        except Exception:
            pass

        tick += 1
        if tick % 6 == 0:
            elapsed = int(time.time() - (deadline - timeout_sec))
            console.print(f"   ⏳ {elapsed}s — still waiting...")
        time.sleep(10)

    return ""
