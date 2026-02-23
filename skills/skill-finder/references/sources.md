# Skill & Subagent Sources

## Primary Sources

### 0. skills.sh (Official CLI Registry) ⭐ Search First
- URL: https://skills.sh
- Official open agent skills ecosystem, backed by Vercel Labs
- Cross-platform: Claude Code, Codex, Cursor, OpenCode, and 37+ agents
- **Search:** `npx skills find <query>` — interactive, returns ranked results with install commands
- **List skills in a repo:** `npx skills add <owner/repo> --list`
- **Install:** `npx skills add <owner/repo> --skill <name> -g -a claude-code -y`
- Install format: `npx skills add vercel-labs/agent-skills@<skill-name>`
- Skills installed to: `~/.agents/skills/` (symlinked to `~/.claude/skills/`)
- Notable registries: `vercel-labs/agent-skills`, `ComposioHQ/awesome-claude-skills`

### 1. subagents.app
- URL: https://subagents.app
- Category browse: https://subagents.app/category/<category>
- Common categories: templates-generators, coding, productivity, research, writing
- Search: https://subagents.app/search?q=<query>
- Format: Subagent markdown files (.md with YAML frontmatter)
- Install: Download and copy to `~/.claude/agents/` or `.claude/agents/`

### 2. VoltAgent awesome-agent-skills (GitHub)
- URL: https://github.com/VoltAgent/awesome-agent-skills
- 380+ community skills, compatible with Claude Code, Codex, Cursor, Gemini CLI
- Search: Browse README or use GitHub search within repo
- Install: `git clone` individual skill directories to `~/.claude/skills/<name>`

### 3. Build with Claude Marketplace
- URL: https://www.buildwithclaude.com
- Official Anthropic-endorsed marketplace
- Contains: plugins, subagents, skills, commands, hooks
- Search: Use site search or browse categories

### 4. claude-plugins.dev
- URL: https://claude-plugins.dev
- Skills registry with structured metadata
- Skill URL pattern: https://claude-plugins.dev/skills/@<author>/<registry>/<skill-name>
- Install: `git clone` from linked GitHub repo

### 5. claudemarketplaces.com
- URL: https://claudemarketplaces.com/skills
- Community aggregator for Claude Code extensions
- Contains: skills, subagents, commands

### 6. GitHub (general)
- Search query: `"SKILL.md" claude code skill <topic>`
- Search query: `site:github.com claude agents <topic>`
- Search query: `claude code subagent <topic> .md`
- Install: `git clone <repo> ~/.claude/skills/<name>`

## Search Strategy by Need

| Need | Best Source |
|------|-------------|
| Any skill (start here) | skills.sh → `npx skills find <query>` |
| Subagent templates | subagents.app |
| Production-ready skills | claude-plugins.dev |
| Community/niche skills | awesome-agent-skills, GitHub |
| Official integrations | buildwithclaude.com |
| Browsing by category | claudemarketplaces.com |

## Installation Commands

```bash
# Install a skill from GitHub
git clone <repo-url> ~/.claude/skills/<skill-name>

# Install a subagent (copy single .md file)
curl -o ~/.claude/agents/<name>.md <raw-url>

# Install from local clone
cp -r /tmp/<repo>/<skill-dir> ~/.claude/skills/<skill-name>
```

Always restart Claude Code after installation.
