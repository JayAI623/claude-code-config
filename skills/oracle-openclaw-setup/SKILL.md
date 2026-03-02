---
name: oracle-openclaw-setup
description: |
  Automated setup wizard for Oracle Cloud Always Free (4 ARM CPU, 24 GB RAM, permanent free)
  + OpenClaw personal AI assistant. Use when user wants to: set up a free cloud server for
  OpenClaw, deploy OpenClaw on Oracle Cloud, create an OCI ARM instance, install OpenClaw
  on a VPS, or run OpenClaw for free forever. Automates: interactive config → OCI console
  browser automation (Patchright) → SSH Docker + OpenClaw install. Interactive user prompts
  at each step.
author: Claude Code
version: 1.0.0
date: 2026-03-02
---

# Oracle Cloud Always Free + OpenClaw Setup

Fully automated wizard: configure → create OCI ARM instance → install Docker + OpenClaw via SSH.

**Cost: $0/month forever** (Oracle Always Free: 4 ARM CPU + 24 GB RAM + 200 GB storage)

## Critical: Always Use run.py Wrapper

```bash
# ✅ CORRECT — always use run.py:
python scripts/run.py setup.py

# ❌ WRONG — never call directly (missing venv):
python scripts/setup.py
```

`run.py` automatically creates `.venv`, installs all dependencies, and installs Chrome for Patchright.

## Usage

### Full Setup (first time)
```bash
python scripts/run.py setup.py
```
Runs all 3 steps: config → OCI browser → SSH install.

### Skip OCI browser (instance already exists)
```bash
python scripts/run.py setup.py --ip 1.2.3.4
```

### Edit config only
```bash
python scripts/run.py setup.py --config
```

### Create instance only (skip SSH install)
```bash
python scripts/run.py setup.py --skip-ssh
```

### Resume SSH install on existing instance
```bash
python scripts/run.py setup.py --skip-oracle
# (reads saved IP from data/config.json)
```

## Wizard Steps

### Step 1: Configuration (Interactive)
Prompts for:
- **SSH key path** — generates new ed25519 key if none exists
- **LLM provider** — Google Gemini (free), Anthropic Claude, or OpenAI
- **API key** — entered securely (hidden input)
- **Messaging platform** — Telegram, WhatsApp, Slack, Discord, or WebChat
- **Platform token** — bot token for chosen platform
- **OCI home region** — e.g. `us-ashburn-1`, `ap-tokyo-1`
- **Instance name** — defaults to `openclaw-server`

Config saved to `data/config.json` (gitignored).

### Step 2: Oracle Cloud Browser (Patchright)
1. Opens Chrome browser (visible — you can interact at any point)
2. Navigates to `https://cloud.oracle.com`
3. **Waits for you to log in** (handles MFA, CAPTCHA manually)
4. Automatically navigates to Compute → Instances → Create Instance
5. Fills in: name, Ubuntu 22.04 image, Ampere A1.Flex shape (4 OCPU, 24 GB), SSH key
6. Submits the form
7. Polls the page for the instance's public IP address
8. Falls back to prompting you for the IP if auto-detection fails

> **Automation is best-effort**: OCI console is complex. When automation can't click
> something, the wizard pauses and asks you to do it manually, then press Enter.

### Step 3: SSH Installation (Automated)
Connects via SSH and runs:
1. `apt-get update && apt-get install` prerequisites
2. `curl -fsSL https://get.docker.com | sudo sh` — Docker
3. `git clone https://github.com/openclaw/openclaw` — OpenClaw
4. Writes `.env` file via SFTP (safe for special chars in API keys)
5. `docker compose up -d` — starts OpenClaw
6. Shows service status

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Create instance" not found | Click it manually in the browser, press Enter |
| Shape selectors don't work | Set manually in browser, press Enter |
| SSH connection refused | Check OCI Security List has port 22 open |
| SSH times out (30 retries) | Instance may still be booting — wait and retry with `--ip` |
| docker compose fails | SSH in manually: `ssh -i KEY ubuntu@IP` and check `~/openclaw/.env` |
| IP not detected automatically | Copy from OCI console, paste when prompted |
| OCI "Out of capacity" error | Try a different region or retry later (ARM instances are popular) |

## Data Storage

All data in `data/` (gitignored):
- `config.json` — saved configuration (API keys, IP, etc.)
- `browser_state/` — Chrome persistent cookies/session for OCI

## After Setup

```bash
# SSH into your instance
ssh -i ~/.ssh/id_ed25519 ubuntu@<IP>

# View OpenClaw logs
cd ~/openclaw && docker compose logs -f

# Restart OpenClaw
cd ~/openclaw && docker compose restart

# Update OpenClaw
cd ~/openclaw && git pull && docker compose up -d
```

Send a message to your configured bot to test it! 🦞

## Architecture

```
oracle-openclaw-setup/
├── SKILL.md               ← this file
├── requirements.txt       ← patchright, paramiko, rich
├── .gitignore
├── data/                  ← gitignored
│   ├── config.json        ← saved config
│   └── browser_state/     ← Chrome session
└── scripts/
    ├── run.py             ← venv wrapper (always use this)
    ├── setup_environment.py ← venv + deps installer
    ├── config.py          ← constants
    ├── setup.py           ← main wizard (orchestrates all phases)
    ├── oracle_browser.py  ← Patchright OCI console automation
    └── ssh_install.py     ← SSH Docker + OpenClaw installer
```
