#!/usr/bin/env bash
# claude-code-sync: bidirectional sync between ~/.claude and GitHub
# Usage:
#   sync.sh push              — package local config and push to GitHub
#   sync.sh pull              — pull from GitHub and auto-install new skills/agents
#   sync.sh status            — show diff between local and remote

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"
AGENTS_DIR="$CLAUDE_DIR/agents"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

# Read config (skipped for init command)
CONFIG_FILE="$SKILL_ROOT/config.env"
CMD_PEEK="${1:-help}"
if [[ "$CMD_PEEK" != "init" ]]; then
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: $CONFIG_FILE not found. Run 'sync.sh init <github-repo-url>' first."
    exit 1
  fi
  source "$CONFIG_FILE"
  # SYNC_REPO_URL, SYNC_REPO_DIR must be set in config.env
fi

# ── helpers ──────────────────────────────────────────────────────────────────

log() { echo "[claude-sync] $*"; }

ensure_repo() {
  local repo_dir="$1"
  if [[ ! -d "$repo_dir/.git" ]]; then
    log "Cloning $SYNC_REPO_URL → $repo_dir"
    git clone "$SYNC_REPO_URL" "$repo_dir"
  else
    log "Pulling latest from remote..."
    git -C "$repo_dir" pull --ff-only 2>/dev/null || true
  fi
}

# ── commands ─────────────────────────────────────────────────────────────────

cmd_init() {
  local repo_url="${1:-}"
  if [[ -z "$repo_url" ]]; then
    echo "Usage: sync.sh init <github-repo-url>"
    exit 1
  fi

  # Write config
  cat > "$CONFIG_FILE" <<EOF
SYNC_REPO_URL="$repo_url"
SYNC_REPO_DIR="$HOME/.claude-code-config-repo"
EOF
  log "Config written to $CONFIG_FILE"
  source "$CONFIG_FILE"

  # Clone or init repo
  if [[ ! -d "$SYNC_REPO_DIR" ]]; then
    if git ls-remote "$repo_url" HEAD &>/dev/null; then
      git clone "$repo_url" "$SYNC_REPO_DIR"
    else
      mkdir -p "$SYNC_REPO_DIR"
      git -C "$SYNC_REPO_DIR" init
      git -C "$SYNC_REPO_DIR" remote add origin "$repo_url"
    fi
  fi
  log "Init complete. Run 'sync.sh push' to upload your config."
}

cmd_push() {
  local staging="$SYNC_REPO_DIR"
  ensure_repo "$staging"
  log "Syncing local config → $staging"

  # Copy top-level config files
  [[ -f "$CLAUDE_DIR/CLAUDE.md" ]]    && cp "$CLAUDE_DIR/CLAUDE.md"    "$staging/CLAUDE.md"
  [[ -f "$CLAUDE_DIR/settings.json" ]] && cp "$CLAUDE_DIR/settings.json" "$staging/settings.json"
  [[ -f "$CLAUDE_DIR/keybindings.json" ]] && cp "$CLAUDE_DIR/keybindings.json" "$staging/keybindings.json"

  # Sync skills (exclude __pycache__ and .pyc)
  if [[ -d "$SKILLS_DIR" ]]; then
    mkdir -p "$staging/skills"
    rsync -a --delete \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='.DS_Store' \
      "$SKILLS_DIR/" "$staging/skills/"
    log "Skills synced: $(ls "$SKILLS_DIR" | wc -l | tr -d ' ') skills"
  fi

  # Sync agents
  if [[ -d "$AGENTS_DIR" ]]; then
    mkdir -p "$staging/agents"
    rsync -a --delete --exclude='.DS_Store' "$AGENTS_DIR/" "$staging/agents/"
    log "Agents synced: $(ls "$AGENTS_DIR" | wc -l | tr -d ' ') agents"
  fi

  # Generate install.sh
  generate_install_script "$staging"

  # Generate README
  generate_readme "$staging"

  # Commit and push
  git -C "$staging" add -A
  if git -C "$staging" diff --cached --quiet; then
    log "Nothing changed. Already up to date."
  else
    local msg="sync: $(date '+%Y-%m-%d %H:%M') — $(ls "$SKILLS_DIR" 2>/dev/null | wc -l | tr -d ' ') skills"
    git -C "$staging" commit -m "$msg"
    git -C "$staging" push origin HEAD
    log "Pushed to $(git -C "$staging" remote get-url origin)"
  fi
}

cmd_pull() {
  local staging="$SYNC_REPO_DIR"
  ensure_repo "$staging"
  local installed=0
  local skipped=0

  log "Checking for new skills in remote repo..."

  # Auto-install new skills
  if [[ -d "$staging/skills" ]]; then
    for skill_dir in "$staging/skills"/*/; do
      local skill_name
      skill_name="$(basename "$skill_dir")"
      local target="$SKILLS_DIR/$skill_name"
      if [[ ! -d "$target" ]]; then
        log "NEW skill detected: $skill_name — installing..."
        cp -r "$skill_dir" "$target"
        ((installed++))
      else
        ((skipped++))
      fi
    done
  fi

  # Auto-install new agents
  if [[ -d "$staging/agents" ]]; then
    mkdir -p "$AGENTS_DIR"
    for agent_file in "$staging/agents"/*.md; do
      [[ -f "$agent_file" ]] || continue
      local agent_name
      agent_name="$(basename "$agent_file")"
      local target="$AGENTS_DIR/$agent_name"
      if [[ ! -f "$target" ]]; then
        log "NEW agent detected: $agent_name — installing..."
        cp "$agent_file" "$target"
        ((installed++))
      else
        ((skipped++))
      fi
    done
  fi

  # Sync config files (always overwrite)
  [[ -f "$staging/settings.json" ]] && cp "$staging/settings.json" "$CLAUDE_DIR/settings.json" && log "settings.json updated"
  [[ -f "$staging/CLAUDE.md" ]]     && cp "$staging/CLAUDE.md"     "$CLAUDE_DIR/CLAUDE.md"     && log "CLAUDE.md updated"
  [[ -f "$staging/keybindings.json" ]] && cp "$staging/keybindings.json" "$CLAUDE_DIR/keybindings.json" && log "keybindings.json updated"

  log "Done. Installed: $installed new, skipped: $skipped already present."
  if (( installed > 0 )); then
    log "Restart Claude Code to activate new skills/agents."
  fi
}

cmd_status() {
  local staging="$SYNC_REPO_DIR"
  ensure_repo "$staging"

  echo ""
  echo "=== Local vs Remote ==="

  echo ""
  echo "── Skills ──"
  local local_skills=()
  local remote_skills=()
  [[ -d "$SKILLS_DIR" ]] && mapfile -t local_skills < <(ls "$SKILLS_DIR")
  [[ -d "$staging/skills" ]] && mapfile -t remote_skills < <(ls "$staging/skills")

  for s in "${remote_skills[@]:-}"; do
    [[ -z "$s" ]] && continue
    if [[ ! -d "$SKILLS_DIR/$s" ]]; then
      echo "  [REMOTE ONLY] $s  ← run 'pull' to install"
    fi
  done
  for s in "${local_skills[@]:-}"; do
    [[ -z "$s" ]] && continue
    if [[ ! -d "$staging/skills/$s" ]]; then
      echo "  [LOCAL ONLY]  $s  ← run 'push' to upload"
    else
      echo "  [synced]      $s"
    fi
  done

  echo ""
  echo "── Git status ──"
  git -C "$staging" status --short
}

generate_install_script() {
  local dir="$1"
  cat > "$dir/install.sh" <<'INSTALL'
#!/usr/bin/env bash
# One-command installer for claude-code-config
# Usage: bash install.sh
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[install] Installing Claude Code config from $SCRIPT_DIR"

mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/agents"

# Config files
[[ -f "$SCRIPT_DIR/CLAUDE.md" ]]       && cp "$SCRIPT_DIR/CLAUDE.md"       "$CLAUDE_DIR/CLAUDE.md"       && echo "  ✓ CLAUDE.md"
[[ -f "$SCRIPT_DIR/settings.json" ]]   && cp "$SCRIPT_DIR/settings.json"   "$CLAUDE_DIR/settings.json"   && echo "  ✓ settings.json"
[[ -f "$SCRIPT_DIR/keybindings.json" ]] && cp "$SCRIPT_DIR/keybindings.json" "$CLAUDE_DIR/keybindings.json" && echo "  ✓ keybindings.json"

# Skills
if [[ -d "$SCRIPT_DIR/skills" ]]; then
  for skill in "$SCRIPT_DIR/skills"/*/; do
    name="$(basename "$skill")"
    cp -r "$skill" "$CLAUDE_DIR/skills/$name"
    echo "  ✓ skill: $name"
  done
fi

# Agents
if [[ -d "$SCRIPT_DIR/agents" ]]; then
  for agent in "$SCRIPT_DIR/agents"/*.md; do
    [[ -f "$agent" ]] || continue
    cp "$agent" "$CLAUDE_DIR/agents/"
    echo "  ✓ agent: $(basename "$agent")"
  done
fi

echo ""
echo "[install] Done. Restart Claude Code to activate."
INSTALL
  chmod +x "$dir/install.sh"
}

generate_readme() {
  local dir="$1"
  local skill_count=0
  [[ -d "$dir/skills" ]] && skill_count=$(ls "$dir/skills" | wc -l | tr -d ' ')

  cat > "$dir/README.md" <<README
# claude-code-config

My personal Claude Code configuration — skills, subagents, and settings.

**Last synced:** $(date '+%Y-%m-%d %H:%M')
**Skills:** $skill_count

## Install on a new machine

\`\`\`bash
git clone $(git -C "$dir" remote get-url origin 2>/dev/null || echo "<repo-url>") ~/.claude-code-config
bash ~/.claude-code-config/install.sh
\`\`\`

## Skills included

$(ls "$dir/skills" 2>/dev/null | sed 's/^/- /' || echo "_(none yet)_")

## Agents included

$(ls "$dir/agents" 2>/dev/null | grep '\.md$' | sed 's/^/- /' || echo "_(none yet)_")
README
}

# ── entrypoint ────────────────────────────────────────────────────────────────

CMD="${1:-help}"
shift || true

case "$CMD" in
  init)   cmd_init "$@" ;;
  push)   cmd_push ;;
  pull)   cmd_pull ;;
  status) cmd_status ;;
  *)
    echo "Usage: sync.sh <init|push|pull|status>"
    echo "  init <url>  — configure remote repo and do first push"
    echo "  push        — package local config and push to GitHub"
    echo "  pull        — pull from GitHub, auto-install new skills/agents"
    echo "  status      — show diff between local and remote"
    ;;
esac
