---
name: rss-feed-fallback
description: |
  When adding RSS feeds for websites that have no native RSS support (e.g. anthropic.com/research,
  openai.com/news), fall back to third-party sources. Use when: (1) `rss-agent-viewer discover <url>`
  returns "No feeds found", (2) common RSS paths (/rss.xml, /feed.xml, /index.xml) all return 404,
  (3) the site is a JavaScript-rendered SPA with no feed link in HTML. Covers fallback strategy using
  GitHub-hosted auto-generated feeds and RSSHub routes.
author: Claude Code
version: 1.0.0
date: 2026-03-15
---

# RSS Feed Fallback for Sites Without Native RSS

## Problem

Some major tech blogs (e.g. Anthropic, some OpenAI pages) don't expose native RSS/Atom feeds.
`rss-agent-viewer discover` returns "No feeds found", and common paths all 404.

## Context / Trigger Conditions

- `npx -y rss-agent-viewer discover <url>` → `○ No feeds found`
- `curl -sI https://example.com/rss.xml` → `HTTP/2 404`
- Site is a Next.js / React SPA (no `<link rel="alternate">` in HTML)
- User wants to subscribe to: Anthropic research/news, OpenAI blog, or similar

## Solution

### Step 1: Try native discovery first

```bash
npx -y rss-agent-viewer discover <url>
```

If feeds found → add them and done.

### Step 2: Try common RSS paths manually

```bash
curl -sI https://example.com/rss.xml
curl -sI https://example.com/feed.xml
curl -sI https://example.com/index.xml
curl -sI https://example.com/atom.xml
```

### Step 3: Check Olshansk/rss-feeds (GitHub auto-generated feeds)

Repository: https://github.com/Olshansk/rss-feeds

Hosts auto-generated RSS feeds for tech blogs that lack native RSS. Feed URL pattern:

```
https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_<name>.xml
```

Known feeds available:
- `feed_anthropic_news.xml` — Anthropic news
- `feed_anthropic_research.xml` — Anthropic research
- `feed_anthropic_engineering.xml` — Anthropic engineering
- `feed_anthropic_frontier_red_team.xml` — Anthropic frontier red team

Add example:
```bash
npx -y rss-agent-viewer add https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml
```

### Step 4: Check RSSHub

RSSHub generates feeds for many sites. Try:
```
https://rsshub.app/<platform>/<route>
```

⚠️ Note: Some routes may still be in proposal stage (e.g. Anthropic Engineering was an open Issue as of 2026-03).
Check the RSSHub docs or issues before relying on a route.

## Verification

```bash
npx -y rss-agent-viewer feeds   # confirm feed was added
npx -y rss-agent-viewer read --limit 5  # confirm articles are fetched
```

## Example

Adding Anthropic research feed (no native RSS):

```bash
# Step 1 - discover returns nothing
npx -y rss-agent-viewer discover https://www.anthropic.com/research
# → ○ No feeds found

# Step 3 - use GitHub fallback
npx -y rss-agent-viewer add https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml
# → ✓ Added feed: ...
```

## Notes

- OpenAI's main news page DOES have a native RSS: `https://openai.com/news/rss.xml`
  and Chinese version: `https://openai.com/zh-Hans-CN/news/rss.xml`
- Olshansk/rss-feeds feeds are community-maintained and updated via GitHub Actions — may lag behind
- Always prefer native RSS over third-party generated feeds when available

## References

- [Olshansk/rss-feeds on GitHub](https://github.com/Olshansk/rss-feeds)
- [RSSHub documentation](https://docs.rsshub.app)
- [RSSHub Anthropic Engineering proposal #18943](https://github.com/DIYgod/RSSHub/issues/18943)
