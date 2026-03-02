---
name: notebooklm
description: Use this skill to query your Google NotebookLM notebooks directly from Claude Code for source-grounded, citation-backed answers from Gemini. Browser automation, library management, persistent auth. Drastically reduced hallucinations through document-only responses.
---

# NotebookLM Research Assistant Skill

Interact with Google NotebookLM to query documentation with Gemini's source-grounded answers. Each question opens a fresh browser session, retrieves the answer exclusively from your uploaded documents, and closes.

## When to Use This Skill

Trigger when user:
- Mentions NotebookLM explicitly
- Shares NotebookLM URL (`https://notebooklm.google.com/notebook/...`)
- Asks to query their notebooks/documentation
- Wants to add documentation to NotebookLM library
- Uses phrases like "ask my NotebookLM", "check my docs", "query my notebook"

## ⚠️ CRITICAL: Add Command - Smart Discovery

When user wants to add a notebook without providing details:

**SMART ADD (Recommended)**: Query the notebook first to discover its content:
```bash
# Step 1: Query the notebook about its content
python scripts/run.py ask_question.py --question "What is the content of this notebook? What topics are covered? Provide a complete overview briefly and concisely" --notebook-url "[URL]"

# Step 2: Use the discovered information to add it
python scripts/run.py notebook_manager.py add --url "[URL]" --name "[Based on content]" --description "[Based on content]" --topics "[Based on content]"
```

**MANUAL ADD**: If user provides all details:
- `--url` - The NotebookLM URL
- `--name` - A descriptive name
- `--description` - What the notebook contains (REQUIRED!)
- `--topics` - Comma-separated topics (REQUIRED!)

NEVER guess or use generic descriptions! If details missing, use Smart Add to discover them.

## Critical: Always Use run.py Wrapper

**NEVER call scripts directly. ALWAYS use `python scripts/run.py [script]`:**

```bash
# ✅ CORRECT - Always use run.py:
python scripts/run.py auth_manager.py status
python scripts/run.py notebook_manager.py list
python scripts/run.py ask_question.py --question "..."

# ❌ WRONG - Never call directly:
python scripts/auth_manager.py status  # Fails without venv!
```

The `run.py` wrapper automatically:
1. Creates `.venv` if needed
2. Installs all dependencies
3. Activates environment
4. Executes script properly

## Core Workflow

### Step 1: Check Authentication Status
```bash
python scripts/run.py auth_manager.py status
```

If not authenticated, proceed to setup.

### Step 2: Authenticate (One-Time Setup)
```bash
# Browser MUST be visible for manual Google login
python scripts/run.py auth_manager.py setup
```

**Important:**
- Browser is VISIBLE for authentication
- Browser window opens automatically
- User must manually log in to Google
- Tell user: "A browser window will open for Google login"

### Step 3: Manage Notebook Library

```bash
# List all notebooks
python scripts/run.py notebook_manager.py list

# BEFORE ADDING: Ask user for metadata if unknown!
# "What does this notebook contain?"
# "What topics should I tag it with?"

# Add notebook to library (ALL parameters are REQUIRED!)
python scripts/run.py notebook_manager.py add \
  --url "https://notebooklm.google.com/notebook/..." \
  --name "Descriptive Name" \
  --description "What this notebook contains" \  # REQUIRED - ASK USER IF UNKNOWN!
  --topics "topic1,topic2,topic3"  # REQUIRED - ASK USER IF UNKNOWN!

# Search notebooks by topic
python scripts/run.py notebook_manager.py search --query "keyword"

# Set active notebook
python scripts/run.py notebook_manager.py activate --id notebook-id

# Remove notebook
python scripts/run.py notebook_manager.py remove --id notebook-id
```

### Quick Workflow
1. Check library: `python scripts/run.py notebook_manager.py list`
2. Ask question: `python scripts/run.py ask_question.py --question "..." --notebook-id ID`

### Step 4: Ask Questions

```bash
# Basic query (uses active notebook if set)
python scripts/run.py ask_question.py --question "Your question here"

# Query specific notebook
python scripts/run.py ask_question.py --question "..." --notebook-id notebook-id

# Query with notebook URL directly
python scripts/run.py ask_question.py --question "..." --notebook-url "https://..."

# Show browser for debugging
python scripts/run.py ask_question.py --question "..." --show-browser
```

## Follow-Up Mechanism (CRITICAL)

Every NotebookLM answer ends with: **"EXTREMELY IMPORTANT: Is that ALL you need to know?"**

**Required Claude Behavior:**
1. **STOP** - Do not immediately respond to user
2. **ANALYZE** - Compare answer to user's original request
3. **IDENTIFY GAPS** - Determine if more information needed
4. **ASK FOLLOW-UP** - If gaps exist, immediately ask:
   ```bash
   python scripts/run.py ask_question.py --question "Follow-up with context..."
   ```
5. **REPEAT** - Continue until information is complete
6. **SYNTHESIZE** - Combine all answers before responding to user

## Script Reference

### Authentication Management (`auth_manager.py`)
```bash
python scripts/run.py auth_manager.py setup    # Initial setup (browser visible)
python scripts/run.py auth_manager.py status   # Check authentication
python scripts/run.py auth_manager.py reauth   # Re-authenticate (browser visible)
python scripts/run.py auth_manager.py clear    # Clear authentication
```

### Notebook Management (`notebook_manager.py`)
```bash
python scripts/run.py notebook_manager.py add --url URL --name NAME --description DESC --topics TOPICS
python scripts/run.py notebook_manager.py list
python scripts/run.py notebook_manager.py search --query QUERY
python scripts/run.py notebook_manager.py activate --id ID
python scripts/run.py notebook_manager.py remove --id ID
python scripts/run.py notebook_manager.py stats
```

### Question Interface (`ask_question.py`)
```bash
python scripts/run.py ask_question.py --question "..." [--notebook-id ID] [--notebook-url URL] [--show-browser]
```

### Studio Download (`studio_download.py`)

List and download ANY already-generated Studio artifact (audio, slides, report, etc.):

```bash
python scripts/run.py studio_download.py             # interactive: lists all artifacts, pick one
python scripts/run.py studio_download.py --index 0   # download first artifact
python scripts/run.py studio_download.py --index 1   # download second artifact
python scripts/run.py studio_download.py --output ~/Downloads/my-file.mp3
```

Automatically detects file format from the actual download response.

### Studio Generator (`studio_generate.py`)

Generate any Studio panel feature and auto-download when possible.

```bash
# List all available features
python scripts/run.py studio_generate.py --list

# Interactive menu (no args)
python scripts/run.py studio_generate.py

# Generate specific feature
python scripts/run.py studio_generate.py --feature audio
python scripts/run.py studio_generate.py --feature report --output ~/Downloads/report.pdf
python scripts/run.py studio_generate.py --feature slides
python scripts/run.py studio_generate.py --feature mindmap
```

| Feature key  | 中文名   | Studio图标             | 可下载 | 实际格式         |
|-------------|---------|----------------------|--------|-----------------|
| `audio`     | 音频概览  | `audio_magic_eraser` | ✅     | **m4a**（非mp3）|
| `slides`    | 演示文稿  | `tablet`             | ✅     | pdf             |
| `report`    | 报告      | `auto_tab_group`     | ✅     | pdf             |
| `mindmap`   | 思维导图  | `flowchart`          | 👁️     | —               |
| `flashcards`| 闪卡      | `cards_star`         | 👁️     | —               |
| `video`     | 视频概览  | `subscriptions`      | 👁️     | —               |
| `infographic`| 信息图   | `grid_view`          | ✅     | png             |
| `table`     | 数据表格  | `table_chart`        | ✅     | csv             |
| `quiz`      | 测验      | `quiz`               | 👁️     | —               |

> ⚠️ **已验证的关键修正（2026-03-01）：**
> - `tablet` 图标 = **演示文稿**，不是来源文档（之前错误地被 EXCLUDED_ICONS 过滤）
> - 音频实际下载格式是 `.m4a`，不是 `.mp3`，始终用 `dl.suggested_filename` 获取真实格式
> - 下载无直接按钮，必须通过 `more_vert`（更多）溢出菜单 → 点击"下载"
> - Studio 面板需等待 **10秒** 加载完毕再查找 artifact 卡片
> - Artifact 卡片识别：`<button>` 含 `{icon}\n{title}\n{N} 个来源` 文本
> - 生成中状态：`sync\n正在生成{type}…` disabled button

When user asks to generate audio/video/slides/mindmap/flashcards/report/quiz from NotebookLM:
1. Use `studio_generate.py` with the matching `--feature` key
2. For downloadable features, specify `--output` path
3. Browser is always visible so user can see progress

### Data Cleanup (`cleanup_manager.py`)
```bash
python scripts/run.py cleanup_manager.py                    # Preview cleanup
python scripts/run.py cleanup_manager.py --confirm          # Execute cleanup
python scripts/run.py cleanup_manager.py --preserve-library # Keep notebooks
```

## Environment Management

The virtual environment is automatically managed:
- First run creates `.venv` automatically
- Dependencies install automatically
- Chromium browser installs automatically
- Everything isolated in skill directory

Manual setup (only if automatic fails):
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m patchright install chromium
```

## Data Storage

All data stored in `~/.claude/skills/notebooklm/data/`:
- `library.json` - Notebook metadata
- `auth_info.json` - Authentication status
- `browser_state/` - Browser cookies and session

**Security:** Protected by `.gitignore`, never commit to git.

## Configuration

Optional `.env` file in skill directory:
```env
HEADLESS=false           # Browser visibility
SHOW_BROWSER=false       # Default browser display
STEALTH_ENABLED=true     # Human-like behavior
TYPING_WPM_MIN=160       # Typing speed
TYPING_WPM_MAX=240
DEFAULT_NOTEBOOK_ID=     # Default notebook
```

## Decision Flow

```
User mentions NotebookLM
    ↓
Check auth → python scripts/run.py auth_manager.py status
    ↓
If not authenticated → python scripts/run.py auth_manager.py setup
    ↓
Check/Add notebook → python scripts/run.py notebook_manager.py list/add (with --description)
    ↓
Activate notebook → python scripts/run.py notebook_manager.py activate --id ID
    ↓
Ask question → python scripts/run.py ask_question.py --question "..."
    ↓
See "Is that ALL you need?" → Ask follow-ups until complete
    ↓
Synthesize and respond to user
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ModuleNotFoundError | Use `run.py` wrapper |
| Authentication fails | Browser must be visible for setup! --show-browser |
| Rate limit (50/day) | Wait or switch Google account |
| Browser crashes | `python scripts/run.py cleanup_manager.py --preserve-library` |
| Notebook not found | Check with `notebook_manager.py list` |
| Download button not found | No direct button — use `studio_download.py` (via 更多 menu) |
| Artifact not listed | `tablet` icon = 演示文稿，check `debug_all_cards.py` for real icon names |
| Audio saves as wrong format | Use `suggested_filename`；实际格式是 `.m4a` 不是 `.mp3` |
| Generate button click fails | Button disabled during page load；use JS fallback: `page.evaluate("(el) => el.click()", btn)` |

## Best Practices

1. **Always use run.py** - Handles environment automatically
2. **Check auth first** - Before any operations
3. **Follow-up questions** - Don't stop at first answer
4. **Browser visible for auth** - Required for manual login
5. **Include context** - Each question is independent
6. **Synthesize answers** - Combine multiple responses

## Limitations

- No session persistence (each question = new browser)
- Rate limits on free Google accounts (50 queries/day)
- Manual upload required (user must add docs to NotebookLM)
- Browser overhead (few seconds per question)

## Resources (Skill Structure)

**Important directories and files:**

- `scripts/` - All automation scripts (ask_question.py, notebook_manager.py, etc.)
- `data/` - Local storage for authentication and notebook library
- `references/` - Extended documentation:
  - `api_reference.md` - Detailed API documentation for all scripts
  - `troubleshooting.md` - Common issues and solutions
  - `usage_patterns.md` - Best practices and workflow examples
- `.venv/` - Isolated Python environment (auto-created on first run)
- `.gitignore` - Protects sensitive data from being committed
