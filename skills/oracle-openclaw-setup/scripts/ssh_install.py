#!/usr/bin/env python3
"""
SSH-based installation of Docker + OpenClaw on the Oracle Cloud instance.
Uses paramiko for SSH, streams output live.
"""

import sys
import time
from pathlib import Path

import paramiko
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent))
from config import DEFAULT_SSH_USER, SSH_CONNECT_RETRIES, SSH_RETRY_INTERVAL

console = Console()


def ssh_connect(ip: str, key_path: str, username: str = DEFAULT_SSH_USER) -> paramiko.SSHClient:
    """Connect via SSH with retries (instance may still be booting)."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    console.print(f"🔌 Connecting to {username}@{ip}...")
    for attempt in range(1, SSH_CONNECT_RETRIES + 1):
        try:
            ssh.connect(
                ip,
                username=username,
                key_filename=str(key_path),
                timeout=10,
                banner_timeout=30,
                auth_timeout=20,
            )
            console.print(f"[green]✓[/green] SSH connected!")
            return ssh
        except Exception as e:
            console.print(
                f"  [dim]Attempt {attempt}/{SSH_CONNECT_RETRIES}: {type(e).__name__}[/dim]"
            )
            if attempt < SSH_CONNECT_RETRIES:
                time.sleep(SSH_RETRY_INTERVAL)

    raise RuntimeError(
        f"Could not SSH into {ip} after {SSH_CONNECT_RETRIES} attempts.\n"
        "Check that port 22 is open in the OCI Security List."
    )


def ssh_exec(ssh: paramiko.SSHClient, cmd: str, description: str = "") -> int:
    """Run command over SSH, stream stdout/stderr, return exit code."""
    if description:
        console.print(f"  [cyan]→[/cyan] {description}")
    _, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    for line in stdout:
        line = line.rstrip()
        if line:
            console.print(f"    [dim]{line}[/dim]")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        err = stderr.read().decode(errors="replace").strip()
        if err:
            console.print(f"    [yellow]{err}[/yellow]")
    return exit_code


def write_file_sftp(ssh: paramiko.SSHClient, remote_path: str, content: str):
    """Write a file on the remote host via SFTP (safe for special chars)."""
    sftp = ssh.open_sftp()
    try:
        with sftp.open(remote_path, "w") as f:
            f.write(content)
    finally:
        sftp.close()


def build_env_content(cfg: dict) -> str:
    """Build the OpenClaw .env file content from config."""
    lines = []

    # LLM key
    env_var = cfg.get("api_key_env", "")
    api_key = cfg.get("api_key", "")
    if env_var and api_key:
        lines.append(f"{env_var}={api_key}")

    # Messaging platform token
    token_key = cfg.get("platform_token_key", "")
    token_val = cfg.get("platform_token", "")
    if token_key and token_val:
        lines.append(f"{token_key}={token_val}")

    lines += [
        "NODE_ENV=production",
        "HEADLESS=true",
    ]
    return "\n".join(lines) + "\n"


def run_ssh_install(ip: str, cfg: dict) -> bool:
    """
    Full SSH install sequence:
      1. Install Docker
      2. Clone OpenClaw
      3. Write .env
      4. Start Docker Compose
    """
    console.print(f"\n[bold cyan]🔧 Installing Docker + OpenClaw on {ip}[/bold cyan]")

    try:
        ssh = ssh_connect(ip, cfg["ssh_key"])
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return False

    steps = [
        ("Updating apt packages",
         "sudo apt-get update -qq"),
        ("Installing prerequisites",
         "sudo apt-get install -y -qq ca-certificates curl gnupg git"),
        ("Installing Docker (official script)",
         "curl -fsSL https://get.docker.com | sudo sh"),
        ("Adding ubuntu to docker group",
         "sudo usermod -aG docker ubuntu"),
        ("Installing docker compose plugin",
         "sudo apt-get install -y -qq docker-compose-plugin"),
        ("Cloning OpenClaw repository",
         "git clone https://github.com/openclaw/openclaw ~/openclaw "
         "|| (cd ~/openclaw && git pull --ff-only)"),
        ("Copying .env.example → .env",
         "cp -n ~/openclaw/.env.example ~/openclaw/.env 2>/dev/null || true"),
    ]

    for desc, cmd in steps:
        code = ssh_exec(ssh, cmd, desc)
        if code != 0:
            console.print(f"  [yellow]⚠ Exit code {code} — continuing anyway[/yellow]")

    # Write .env via SFTP (avoids shell escaping issues with API keys)
    console.print("  [cyan]→[/cyan] Writing .env configuration")
    env_content = build_env_content(cfg)
    try:
        write_file_sftp(ssh, "/home/ubuntu/openclaw/.env", env_content)
        console.print("  [green]✓[/green] .env written")
    except Exception as e:
        console.print(f"  [yellow]⚠ SFTP write failed: {e}. Trying shell fallback...[/yellow]")
        # Escape for shell here-doc
        escaped = env_content.replace("\\", "\\\\").replace("$", "\\$").replace("`", "\\`")
        ssh_exec(
            ssh,
            f"cat > ~/openclaw/.env << 'EOF'\n{escaped}\nEOF",
            "Writing .env (fallback)",
        )

    # Start OpenClaw
    ssh_exec(
        ssh,
        "cd ~/openclaw && docker compose up -d",
        "Starting OpenClaw (docker compose up -d)",
    )

    # Wait a moment and show status
    time.sleep(5)
    console.print("  [cyan]→[/cyan] Checking service status")
    ssh_exec(ssh, "cd ~/openclaw && docker compose ps")

    ssh.close()
    return True
