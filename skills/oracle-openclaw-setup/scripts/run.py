#!/usr/bin/env python3
"""
Universal runner for oracle-openclaw-setup skill scripts.
Ensures all scripts run with the correct virtual environment.
(Same pattern as notebooklm skill)

Usage:
  python scripts/run.py setup.py
  python scripts/run.py setup.py --ip 1.2.3.4
  python scripts/run.py setup.py --config
"""

import os
import sys
import subprocess
from pathlib import Path


def get_venv_python():
    skill_dir = Path(__file__).parent.parent
    venv_dir  = skill_dir / ".venv"
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_venv():
    skill_dir = Path(__file__).parent.parent
    venv_dir  = skill_dir / ".venv"
    setup_script = skill_dir / "scripts" / "setup_environment.py"

    if not venv_dir.exists():
        print("🔧 First-time setup: creating virtual environment...")
        print("   (This takes about a minute)")
        result = subprocess.run([sys.executable, str(setup_script)])
        if result.returncode != 0:
            print("❌ Environment setup failed")
            sys.exit(1)
        print("✅ Environment ready!\n")

    return get_venv_python()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run.py <script.py> [args...]")
        print("\nAvailable scripts:")
        print("  setup.py              — Full setup wizard (config + OCI + SSH)")
        print("  setup.py --config     — Edit config only")
        print("  setup.py --ip <ip>    — Skip OCI browser, install on existing instance")
        print("  setup.py --skip-ssh   — Create instance only, skip SSH install")
        sys.exit(1)

    script_name = sys.argv[1]
    script_args = sys.argv[2:]

    if script_name.startswith("scripts/"):
        script_name = script_name[8:]
    if not script_name.endswith(".py"):
        script_name += ".py"

    skill_dir   = Path(__file__).parent.parent
    script_path = skill_dir / "scripts" / script_name

    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        sys.exit(1)

    venv_python = ensure_venv()
    cmd = [str(venv_python), str(script_path)] + script_args

    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
