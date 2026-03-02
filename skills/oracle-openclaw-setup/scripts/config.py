"""
Configuration constants for oracle-openclaw-setup skill
"""
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_state"

# Ensure dirs exist
DATA_DIR.mkdir(exist_ok=True)
BROWSER_PROFILE_DIR.mkdir(exist_ok=True)

# Oracle Cloud URLs
OCI_URL = "https://cloud.oracle.com"
OCI_INSTANCES_URL = "https://cloud.oracle.com/compute/instances"

# Browser settings (same as notebooklm for consistency)
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# LLM providers: key → (env var name, display label)
LLM_PROVIDERS = {
    "google":      ("GOOGLE_API_KEY",      "Gemini Flash-Lite  — Free tier available"),
    "openrouter":  ("OPENROUTER_API_KEY",  "OpenRouter         — 300+ models, pay-per-use"),
    "anthropic":   ("ANTHROPIC_API_KEY",   "Claude Haiku 3     — ~$3/mo"),
    "openai":      ("OPENAI_API_KEY",      "GPT-4o-mini        — ~$5/mo"),
}

# Messaging platforms: key → env var name
MESSAGING_PLATFORMS = {
    "telegram":  "TELEGRAM_BOT_TOKEN",
    "whatsapp":  "WHATSAPP_TOKEN",
    "slack":     "SLACK_BOT_TOKEN",
    "discord":   "DISCORD_BOT_TOKEN",
    "webchat":   "",   # no token needed — served on port 3000
}

# SSH defaults
DEFAULT_SSH_USER = "ubuntu"
SSH_CONNECT_RETRIES = 30
SSH_RETRY_INTERVAL = 15   # seconds between retries
