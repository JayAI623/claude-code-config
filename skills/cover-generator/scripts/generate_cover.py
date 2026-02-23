#!/usr/bin/env python3
"""Generate a unified blog cover image using nanoBananaAPI (Gemini image generation).

Usage (default STYLE_PROMPT):
    python3 generate_cover.py \
        --title "码农AI Infra指南之CUDA编程" \
        --brand "NVIDIA CUDA logo (green gear icon), OpenAI logo" \
        --scene "futuristic GPU datacenter, neon green circuit board patterns" \
        --output "码农AIInfra指南之CUDA编程_1_JayAI"

Usage (fully custom prompt, bypass STYLE_PROMPT):
    python3 generate_cover.py \
        --prompt "Your full custom prompt here..." \
        --output "my_cover"

List available image-capable models:
    python3 generate_cover.py --list-models

API key is read from GEMINI_API_KEY environment variable.
"""

import argparse
import base64
import os
import sys
from pathlib import Path

COVERS_DIR = Path("/Users/liuzhe/Desktop/blogPost/covers")

# Style DNA: extracted from the 6 existing covers
STYLE_PROMPT = """Create a Chinese tech blog cover image (Xiaohongshu/小红书 format) in portrait orientation (2:3 ratio).

EXACT LAYOUT (top to bottom):
1. TOP ZONE (~30% height): Light sky-blue background (#A8D8EA). Contains flat-illustrated AI brand logos/icons floating in the blue area. Bottom edge is a gentle organic wavy curve (NOT a straight line).
2. MAIN ZONE (~70% height): Cream/off-white background (#F5EDD6). Contains:
   a. Chinese title text in dark olive-green (#3D4A2E), bold, positioned immediately below the wavy curve with minimal top padding — no large gap between wave and title
   b. An orange hand-drawn wavy squiggle line (~#E8650A) directly below the title
   c. Optional small subtitle text in muted gray directly below the squiggle
   d. A flat vector-art illustration occupying the CENTER of the remaining space — large, fully visible, NOT pushed to the bottom edge, with balanced padding on all sides

STYLE RULES (strictly follow):
- Flat vector illustration aesthetic — NOT photorealistic, NOT 3D render, NOT painterly
- Clean, minimal, modern Chinese social media cover style
- Muted/warm color palette: sky blue, cream, olive green, burnt orange, muted earth tones
- Smooth clean shapes, simple gradients, no heavy shadows or noise
- The AI brand logos must be clearly recognizable flat illustrations

TITLE TEXT to render: {title}
AI BRAND ICONS in top blue zone: {brand}
BACKGROUND SCENE in main zone (flat illustration): {scene}

Output: a single clean cover image with no borders, no photo frames, no extra UI elements."""


DEFAULT_MODEL = "gemini-3-pro-image-preview"


def get_client(api_key: str = None):
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Add it to ~/.zshenv or pass --api-key.", file=sys.stderr)
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def list_image_models(api_key: str = None) -> list[str]:
    """Return model names that support image generation."""
    client = get_client(api_key)
    image_keywords = ("image", "imagen", "vision")
    models = [
        m.name for m in client.models.list()
        if any(k in m.name.lower() for k in image_keywords)
    ]
    return sorted(models)


def generate_cover(output: str, title: str = None, brand: str = None, scene: str = None,
                   custom_prompt: str = None, model: str = DEFAULT_MODEL,
                   api_key: str = None) -> str:
    from google.genai import types
    client = get_client(api_key)

    if custom_prompt:
        prompt = custom_prompt
        print(f"Using custom prompt ({len(prompt)} chars)")
    else:
        prompt = STYLE_PROMPT.format(title=title, brand=brand, scene=scene)
        print(f"Generating cover for: {title}")
        print(f"Brand icons: {brand}")
        print(f"Scene: {scene}")
    print(f"Model: {model}")
    print("Calling Gemini image generation API...")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_data = part.inline_data.data  # already raw bytes, no base64 decode needed
            mime = part.inline_data.mime_type  # e.g. image/png or image/jpeg
            ext = "jpg" if "jpeg" in mime else mime.split("/")[-1]
            output_path = COVERS_DIR / f"{output}.{ext}"
            COVERS_DIR.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_data)
            print(f"\n✓ Saved: {output_path}")
            return str(output_path)

    print("ERROR: No image returned in response.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate blog cover via Gemini image generation")
    parser.add_argument("--output",       required=False, help="Output filename without extension (saved to covers/)")
    parser.add_argument("--prompt",       required=False, help="Full custom prompt (bypasses STYLE_PROMPT entirely)")
    parser.add_argument("--title",        required=False, help="Chinese article title — used with default STYLE_PROMPT")
    parser.add_argument("--brand",        required=False, help="Brand icons description — used with default STYLE_PROMPT")
    parser.add_argument("--scene",        required=False, help="Scene description — used with default STYLE_PROMPT")
    parser.add_argument("--model",        required=False, default=DEFAULT_MODEL,
                        help=f"Gemini model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--list-models",  action="store_true", help="List available image-capable models and exit")
    parser.add_argument("--api-key",      required=False, help="Gemini API key (defaults to GEMINI_API_KEY env var)")
    args = parser.parse_args()

    if args.list_models:
        models = list_image_models(api_key=args.api_key)
        print("Available image-capable models:")
        for m in models:
            marker = " (default)" if m.endswith(DEFAULT_MODEL.split("/")[-1]) else ""
            print(f"  {m}{marker}")
        sys.exit(0)

    if not args.output:
        parser.error("--output is required when generating a cover.")
    if not args.prompt and not all([args.title, args.brand, args.scene]):
        parser.error("Either --prompt, or all of --title / --brand / --scene are required.")

    generate_cover(
        output=args.output,
        title=args.title,
        brand=args.brand,
        scene=args.scene,
        custom_prompt=args.prompt,
        model=args.model,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    main()
