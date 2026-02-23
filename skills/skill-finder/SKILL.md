---
name: skill-finder
description: Search for Claude Code skills and subagent templates across multiple sources. Use when the user wants to find, discover, or install a skill or subagent for a specific purpose — e.g. "find a skill for code review", "search for a subagent that does X", "find me a template for Y", "是否有现成的 skill/subagent 做 X".
---

# Skill Finder

Search multiple sources in parallel, score and rank all candidates, then present the top 5 for user selection.

## Workflow

### Step 1: Clarify the Need

If the request is vague, ask one focused question:
- What task should the skill/subagent perform?
- Any preference: skill (auto-triggered) vs subagent (explicitly invoked)?

### Step 2: Search All Sources in Parallel

Run WebSearch queries simultaneously across all sources. See `references/sources.md` for full source list and search patterns.

**Search queries to run (adapt `<topic>` to user's need):**

```
site:subagents.app <topic>
site:claude-plugins.dev <topic>
site:buildwithclaude.com <topic> skill OR subagent
site:claudemarketplaces.com <topic>
github.com "SKILL.md" claude code <topic>
github.com claude subagent <topic>
site:github.com/VoltAgent/awesome-agent-skills <topic>
```

For each GitHub result found, fetch the repo page to collect: star count, fork count, last updated date, and any download/usage stats mentioned.

### Step 3: Score and Rank All Candidates

For every candidate found, compute a composite score (0–100):

| Signal | Weight | How to score |
|--------|--------|--------------|
| GitHub stars | 35% | log10(stars+1) / log10(10000) × 35 — cap at 10k stars |
| Downloads / installs | 25% | If available from marketplace metadata; else 0 |
| Recency | 20% | Updated within 1 month = 20, 3 months = 15, 6 months = 10, 1 year = 5, older = 0 |
| Source authority | 10% | buildwithclaude.com = 10, claude-plugins.dev = 8, subagents.app = 7, GitHub direct = 6, other = 4 |
| Relevance | 10% | How closely name/description matches user's need (your judgment: 0–10) |

If a signal is unavailable, omit it and re-weight the remaining signals proportionally.

Rank all candidates by score descending. Select the top 5.

### Step 4: Present Top 5 Candidates

Display as a numbered list for the user to choose from:

```
## Top 5 Results for: <user need>

| # | Name | Type | Score | Stars | Downloads | Updated | Source |
|---|------|------|-------|-------|-----------|---------|--------|
| 1 | ... | skill/subagent | 87 | 1.2k | 340 | 2w ago | claude-plugins.dev |
| 2 | ... | subagent | 74 | 890 | — | 1mo ago | subagents.app |
| 3 | ... | skill | 68 | 430 | — | 2mo ago | GitHub |
| 4 | ... | subagent | 61 | 210 | 120 | 3mo ago | buildwithclaude.com |
| 5 | ... | skill | 52 | 95 | — | 5mo ago | awesome-agent-skills |

---
1. **<name>** `score: 87`
   <one-line description>
   Repo: <url>
   Install: `git clone <url> ~/.claude/skills/<name>`

2. **<name>** `score: 74`
   ...

> Which one would you like to install? (1–5, or "none")
```

If fewer than 5 candidates found across all sources, show all found and note: "Only N results found."

### Step 5: Install on Selection

When user picks a number:
1. Use `git clone` for GitHub-hosted skills/subagents (never WebFetch — it summarizes content)
2. Use `curl` for single-file subagents with a direct raw URL
3. Verify the installed file exists with `ls`
4. Confirm: "Installed ✓ Restart Claude Code to activate."

If nothing found at all: suggest using `agent-skill-creator` skill to build a custom one.

## Key Rules

- Always search at least 4 sources before concluding nothing exists
- Score every candidate before presenting — never show an unranked list
- Prefer `git clone` over WebFetch for installation
- Note model requirements if known (e.g. tool search requires Sonnet 4+, not Haiku)
- Reference `references/sources.md` for full source URLs and install patterns
