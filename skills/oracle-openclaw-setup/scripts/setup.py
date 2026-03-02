#!/usr/bin/env python3
"""
Oracle Cloud Always Free + OpenClaw Setup Wizard
Interactive setup: config → OCI instance → SSH install → done

Usage:
  python scripts/run.py setup.py                    # Full wizard
  python scripts/run.py setup.py --ip 1.2.3.4       # Skip OCI browser, use existing IP
  python scripts/run.py setup.py --skip-ssh          # Only create instance, skip install
  python scripts/run.py setup.py --config            # Edit config only
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent))
from config import CONFIG_FILE, LLM_PROVIDERS, MESSAGING_PLATFORMS

console = Console()


def _require_tty():
    """Exit with a helpful message if stdin is not a real terminal."""
    if not sys.stdin.isatty():
        console.print(Panel.fit(
            "[bold red]⚠  Interactive terminal required[/bold red]\n\n"
            "This wizard needs a real terminal for interactive prompts.\n"
            "Run it directly in your shell:\n\n"
            "  [bold cyan]cd ~/.claude/skills/oracle-openclaw-setup[/bold cyan]\n"
            "  [bold cyan]python scripts/run.py setup.py[/bold cyan]",
            border_style="red",
        ))
        sys.exit(1)


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    console.print(f"  [dim]Config saved → {CONFIG_FILE}[/dim]")


# ── Phase 1: Gather config ────────────────────────────────────────────────────

def gather_config() -> dict:
    cfg = load_config()

    _require_tty()

    console.print(Panel.fit(
        "[bold cyan]🦞 Oracle Cloud + OpenClaw Setup Wizard[/bold cyan]\n"
        "Sets up a [bold]free forever[/bold] ARM server (4 CPU, 24 GB RAM)\n"
        "and installs OpenClaw — your personal AI assistant.",
        border_style="cyan",
    ))

    console.print("\n[bold]Step 1 of 3 — Configuration[/bold]")
    console.print("[dim]Press Enter to accept defaults (shown in brackets)[/dim]\n")

    # ── SSH key ──
    default_key = cfg.get("ssh_key") or str(Path.home() / ".ssh" / "id_ed25519")
    if not Path(default_key).exists():
        default_key = str(Path.home() / ".ssh" / "id_rsa")

    ssh_key = Prompt.ask("SSH private key path", default=default_key)
    pub_key_path = ssh_key + ".pub"

    if not Path(ssh_key).exists():
        console.print(f"[yellow]Key not found. Generating new ed25519 key...[/yellow]")
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", ssh_key, "-N", ""],
            check=True
        )
        console.print(f"[green]✓[/green] Key generated: {ssh_key}")

    pub_key = Path(pub_key_path).read_text().strip() if Path(pub_key_path).exists() else ""
    if pub_key:
        console.print(f"  Public key: [dim]{pub_key[:60]}...[/dim]")

    # ── LLM provider ──
    console.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    for k, (_, desc) in LLM_PROVIDERS.items():
        t.add_row(f"[cyan]{k}[/cyan]", desc)
    console.print(t)

    llm = Prompt.ask(
        "LLM provider",
        choices=list(LLM_PROVIDERS.keys()),
        default=cfg.get("llm_provider", "google"),
    )
    api_key_env, _ = LLM_PROVIDERS[llm]
    api_key = Prompt.ask(
        f"  {api_key_env}",
        default=cfg.get("api_key") or os.environ.get(api_key_env, ""),
        password=True,
    )

    # OpenRouter: optionally choose a model
    if llm == "openrouter":
        console.print("\n  [dim]Popular models: openai/gpt-4o-mini · anthropic/claude-haiku-3 · google/gemini-flash-1.5 · meta-llama/llama-3.1-8b-instruct:free[/dim]")
        openrouter_model = Prompt.ask(
            "  OpenRouter model (Enter to use OpenClaw default)",
            default=cfg.get("openrouter_model", ""),
        )
        cfg["openrouter_model"] = openrouter_model

    # ── Messaging platform ──
    console.print()
    t2 = Table(show_header=False, box=None, padding=(0, 2))
    for k, env_var in MESSAGING_PLATFORMS.items():
        note = env_var if env_var else "(no token needed — web UI on port 3000)"
        t2.add_row(f"[cyan]{k}[/cyan]", note)
    console.print(t2)

    platform = Prompt.ask(
        "Messaging platform",
        choices=list(MESSAGING_PLATFORMS.keys()),
        default=cfg.get("platform", "telegram"),
    )
    token_key = MESSAGING_PLATFORMS[platform]
    platform_token = ""
    if token_key:
        platform_token = Prompt.ask(
            f"  {token_key}",
            default=cfg.get("platform_token", ""),
            password=True,
        )

    # ── Oracle Cloud ──
    console.print()
    region = Prompt.ask(
        "OCI Home Region (e.g. us-ashburn-1, ap-tokyo-1)",
        default=cfg.get("region", "us-ashburn-1"),
    )
    instance_name = Prompt.ask(
        "Instance name",
        default=cfg.get("instance_name", "openclaw-server"),
    )

    cfg.update({
        "ssh_key":          ssh_key,
        "pub_key":          pub_key,
        "llm_provider":     llm,
        "api_key_env":      api_key_env,
        "api_key":          api_key,
        "platform":         platform,
        "platform_token_key": token_key,
        "platform_token":   platform_token,
        "region":           region,
        "instance_name":    instance_name,
    })
    save_config(cfg)
    return cfg


# ── Phase 2: Oracle Cloud browser ────────────────────────────────────────────

def phase_oracle(cfg: dict) -> str:
    """Run browser automation and return instance IP."""
    from oracle_browser import run_oracle_setup
    console.print("\n[bold]Step 2 of 3 — Oracle Cloud Instance[/bold]")
    ip = run_oracle_setup(cfg)
    if ip:
        cfg["instance_ip"] = ip
        save_config(cfg)
    return ip


# ── Phase 3: SSH install ──────────────────────────────────────────────────────

def phase_ssh(ip: str, cfg: dict) -> bool:
    """Run SSH install and return success."""
    from ssh_install import run_ssh_install
    console.print("\n[bold]Step 3 of 3 — SSH Installation[/bold]")
    return run_ssh_install(ip, cfg)


# ── Success summary ───────────────────────────────────────────────────────────

def print_success(ip: str, cfg: dict):
    platform = cfg.get("platform", "?")
    ssh_key  = cfg.get("ssh_key", "~/.ssh/id_ed25519")

    lines = [
        f"[bold green]🎉 OpenClaw is live![/bold green]\n",
        f"  Server IP : [bold cyan]{ip}[/bold cyan]",
        f"  Platform  : [bold]{platform}[/bold]",
        f"  SSH       : [dim]ssh -i {ssh_key} ubuntu@{ip}[/dim]",
        f"  Logs      : [dim]cd ~/openclaw && docker compose logs -f[/dim]",
    ]
    if platform == "webchat":
        lines.append(f"  Web UI    : [dim]http://{ip}:3000[/dim]")

    lines += [
        "",
        "[dim]Send a message to your bot to test it! 🦞[/dim]",
    ]

    console.print(Panel("\n".join(lines), border_style="green"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Oracle Cloud Always Free + OpenClaw setup wizard"
    )
    parser.add_argument(
        "--ip",
        help="Skip Oracle Cloud browser step — use this existing instance IP",
    )
    parser.add_argument(
        "--skip-oracle",
        action="store_true",
        help="Same as --ip but reads IP from saved config",
    )
    parser.add_argument(
        "--skip-ssh",
        action="store_true",
        help="Stop after instance creation, skip SSH install",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Edit configuration only (no browser or SSH)",
    )
    args = parser.parse_args()

    # Config-only mode
    if args.config:
        gather_config()
        return 0

    # Phase 1: Config
    cfg = gather_config()

    # Phase 2: Oracle Cloud
    ip = args.ip
    if not ip and args.skip_oracle:
        ip = cfg.get("instance_ip", "")
        if not ip:
            ip = Prompt.ask("Enter your Oracle Cloud instance IP address")
            cfg["instance_ip"] = ip
            save_config(cfg)

    if not ip:
        ip = phase_oracle(cfg)

    if not ip:
        console.print("[red]No instance IP — cannot continue.[/red]")
        return 1

    console.print(f"\n[green]✓[/green] Instance IP: [bold cyan]{ip}[/bold cyan]")

    if args.skip_ssh:
        console.print("\n[dim]Skipping SSH install (--skip-ssh).[/dim]")
        console.print(f"Run later:  python scripts/run.py setup.py --ip {ip} --skip-oracle")
        return 0

    # Phase 3: SSH install
    ok = phase_ssh(ip, cfg)
    if not ok:
        console.print("\n[red]SSH installation failed.[/red]")
        console.print(f"Retry:  python scripts/run.py setup.py --ip {ip} --skip-oracle")
        return 1

    print_success(ip, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
