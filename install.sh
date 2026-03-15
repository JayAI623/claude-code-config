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

# RSS feeds
if [[ -f "$SCRIPT_DIR/rss/feeds.opml" ]]; then
  echo "Importing RSS feeds..."
  npx -y rss-agent-viewer init 2>/dev/null || true
  npx -y rss-agent-viewer import "$SCRIPT_DIR/rss/feeds.opml" && echo "  ✓ RSS feeds imported" \
    || echo "  ⚠ RSS import failed. Run: npx -y rss-agent-viewer import $SCRIPT_DIR/rss/feeds.opml"
fi

echo "[install] Done. Restart Claude Code to activate."
