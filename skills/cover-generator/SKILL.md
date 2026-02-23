---
name: cover-generator
description: Generate a new unified-style blog cover image for the 码农 AI Infra 行动指南 series. Interactively asks user for article title, AI brand logos, and background scene, then uses Gemini image generation to create a cover that matches the existing series visual style. Use when user wants to create, generate, or make a new cover image for a blog post.
---

# Cover Generator

## Overview

Generates Xiaohongshu-format (2:3 portrait) cover images for the 「码农 AI Infra 行动指南」blog series using Gemini image generation. Follows the series visual DNA: warm cream background, flat vector illustration, olive-green bold title, burnt-orange squiggle underline.

## Workflow

### Step 1 — Gather content info (interactive)

Ask the user for:
- **Article title** (中文标题)
- **Article file path** (if available) — read it to understand the theme and main illustration concept
- **Brand/tech logos** to feature (e.g. OpenAI, Anthropic, NVIDIA)

### Step 2 — Choose model (interactive)

Run `--list-models` to fetch available models, then ask the user which one to use:

```bash
python3 /Users/liuzhe/.claude/skills/cover-generator/scripts/generate_cover.py --list-models
```

Present the list to the user and let them pick. Default recommendation: `gemini-3-pro-image-preview`.

### Step 3 — Confirm layout & theme (interactive)

Discuss with the user:
- **Main illustration** concept (what flat-vector scene/diagram fits the article?)
- **Title text** and **subtitle/tag line**
- **Layout style** (top blue zone with logos, OR full-cream no blue zone)

### Step 4 — Generate

Call the script with the agreed parameters:

```bash
python3 /Users/liuzhe/.claude/skills/cover-generator/scripts/generate_cover.py \
  --prompt "..." \
  --model "gemini-3-pro-image-preview" \
  --output "码农AIInfra指南之XXX_1_JayAI"
```

Display the generated image and offer to iterate.

---

## Style DNA (series visual identity)

| Element | Value |
|---|---|
| Format | Portrait 2:3 (Xiaohongshu) |
| Background | Cream/off-white `#F5EDD6` |
| Title font color | Dark olive-green `#3D4A2E`, bold, large |
| Accent line | Hand-drawn wavy squiggle `#E8650A` below title |
| Illustration style | Flat vector, NOT photorealistic or 3D |
| Color palette | Sky blue, cream, olive green, burnt orange, muted earth tones |
| Top blue zone (optional) | `#A8D8EA` with brand logos, wavy bottom edge |

## Script Reference

**Script:** `scripts/generate_cover.py`

**Key flags:**
- `--list-models` — list available image-capable Gemini models
- `--model MODEL` — override model (default: `gemini-3-pro-image-preview`)
- `--title`, `--brand`, `--scene` — use the default STYLE_PROMPT template
- `--prompt` — fully custom prompt (bypasses STYLE_PROMPT)
- `--output` — filename without extension, saved to `/Users/liuzhe/Desktop/blogPost/covers/`

**Covers directory:** `/Users/liuzhe/Desktop/blogPost/covers/`
