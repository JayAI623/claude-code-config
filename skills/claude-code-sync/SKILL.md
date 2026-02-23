---
name: claude-code-sync
description: Sync Claude Code config (skills, subagents, settings) to/from GitHub. Use when user wants to: backup config, push skills to git, pull new skills from remote, check if there are uninstalled skills in the repo, install from a new machine. Triggers on phrases like "sync skills", "push config to git", "pull new skills", "backup claude config", "check remote for new skills", "同步配置", "上传skill", "从git安装".
---

# Claude Code Sync

Bidirectional sync between `~/.claude` and a GitHub repo via `scripts/sync.sh`.

## Commands

| Command | What it does |
|---------|-------------|
| `push` | Package all local skills/agents/config → commit → push to GitHub |
| `pull` | Fetch remote → auto-install any new skills/agents not yet present locally |
| `status` | Show diff: local-only, remote-only, and synced items |
| `init <url>` | First-time setup: configure remote repo URL |

## What gets synced

- `~/.claude/skills/` → `skills/`
- `~/.claude/agents/` → `agents/`
- `~/.claude/CLAUDE.md` → `CLAUDE.md`
- `~/.claude/settings.json` → `settings.json`
- `~/.claude/keybindings.json` → `keybindings.json` (if exists)
- Auto-generated `install.sh` and `README.md`

## Workflow

### Push local config to GitHub

```bash
~/.claude/skills/claude-code-sync/scripts/sync.sh push
```

### Check remote for new skills and auto-install

```bash
~/.claude/skills/claude-code-sync/scripts/sync.sh pull
```

`pull` only installs skills/agents **not already present locally** — it never overwrites existing ones.

### First-time setup on a new machine

```bash
git clone <repo-url> ~/.claude-code-config
bash ~/.claude-code-config/install.sh
```

## Config file

Stored at `~/.claude/skills/claude-code-sync/config.env`:

```bash
SYNC_REPO_URL="https://github.com/JayAI623/claude-code-config"
SYNC_REPO_DIR="$HOME/.claude-code-config-repo"
```

Run `sync.sh init <url>` to create it automatically.

## Usage Instructions for Claude

When user says "sync", "push config", or "pull new skills":
1. Check if `config.env` exists; if not, run `init` first
2. Run the appropriate command via Bash: `~/.claude/skills/claude-code-sync/scripts/sync.sh <cmd>`
3. Show the output to the user
4. If `pull` installed new skills, remind user to restart Claude Code
