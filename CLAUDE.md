# Claude Code Global Notes

## Installing Skills from GitHub

Use `git clone` instead of WebFetch to install skills. WebFetch summarizes content with AI and cannot return raw file content.

```bash
git clone <repo-url> ~/.claude/skills/<skill-name>
```

Example:

```bash
git clone https://github.com/FrancyJGLisboa/agent-skill-creator.git ~/.claude/skills/agent-skill-creator
```

Restart Claude Code after installation to load the new skill.
