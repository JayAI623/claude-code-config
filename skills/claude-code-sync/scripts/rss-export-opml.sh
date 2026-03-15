#!/usr/bin/env bash
# rss-export-opml.sh — Export RSS feeds from rss-agent-viewer SQLite DB to OPML
# Usage: rss-export-opml.sh [output-path]
# Default output: stdout
set -euo pipefail

DB="$HOME/.config/rss-viewer/feeds.db"
OUTPUT="${1:-}"

if [[ ! -f "$DB" ]]; then
  echo "[rss-export] No feeds DB found at $DB — skipping export." >&2
  exit 0
fi

if ! command -v sqlite3 &>/dev/null; then
  echo "[rss-export] ERROR: sqlite3 not found. Install it to enable RSS export." >&2
  exit 1
fi

OPML=$(sqlite3 "$DB" <<'SQL'
.headers off
.mode list
SELECT
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<opml version="2.0">',
  '  <head><title>RSS Feeds</title></head>',
  '  <body>';
SELECT
  '    <outline type="rss" text="' || replace(COALESCE(title, url), '"', '&quot;') || '"' ||
  ' xmlUrl="' || replace(url, '"', '&quot;') || '"' ||
  CASE WHEN link IS NOT NULL AND link != '' THEN ' htmlUrl="' || replace(link, '"', '&quot;') || '"' ELSE '' END ||
  '/>'
FROM feeds
ORDER BY title;
SELECT
  '  </body>',
  '</opml>';
SQL
)

if [[ -z "$OUTPUT" ]]; then
  echo "$OPML"
else
  mkdir -p "$(dirname "$OUTPUT")"
  echo "$OPML" > "$OUTPUT"
  echo "[rss-export] Exported $(sqlite3 "$DB" 'SELECT COUNT(*) FROM feeds;') feeds → $OUTPUT" >&2
fi
