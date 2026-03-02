#!/usr/bin/env python3
"""
Environment Setup for oracle-openclaw-setup skill
Manages virtual environment and dependencies automatically.
(Same pattern as notebooklm skill)
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


class SkillEnvironment:
    def __init__(self):
        self.skill_dir = Path(__file__).parent.parent
        self.venv_dir = self.skill_dir / ".venv"
        self.requirements_file = self.skill_dir / "requirements.txt"

        if os.name == "nt":
            self.venv_python = self.venv_dir / "Scripts" / "python.exe"
            self.venv_pip    = self.venv_dir / "Scripts" / "pip.exe"
        else:
            self.venv_python = self.venv_dir / "bin" / "python"
            self.venv_pip    = self.venv_dir / "bin" / "pip"

    def is_in_skill_venv(self) -> bool:
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            return Path(sys.prefix) == self.venv_dir
        return False

    def ensure_venv(self) -> bool:
        if self.is_in_skill_venv():
            return True

        if not self.venv_dir.exists():
            print("🔧 Creating virtual environment...")
            try:
                venv.create(self.venv_dir, with_pip=True)
                print("✅ Virtual environment created")
            except Exception as e:
                print(f"❌ Failed to create venv: {e}")
                return False

        if self.requirements_file.exists():
            print("📦 Installing dependencies...")
            try:
                subprocess.run(
                    [str(self.venv_pip), "install", "--upgrade", "pip"],
                    check=True, capture_output=True, text=True,
                )
                subprocess.run(
                    [str(self.venv_pip), "install", "-r", str(self.requirements_file)],
                    check=True, capture_output=True, text=True,
                )
                print("✅ Dependencies installed")

                print("🌐 Installing Chrome for Patchright...")
                try:
                    subprocess.run(
                        [str(self.venv_python), "-m", "patchright", "install", "chrome"],
                        check=True, capture_output=True, text=True,
                    )
                    print("✅ Chrome installed")
                except subprocess.CalledProcessError:
                    print("⚠️  Chrome install failed — run manually: python -m patchright install chrome")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Dependency install failed: {e}")
                return False
        return True

    def get_python_executable(self) -> str:
        return str(self.venv_python) if self.venv_python.exists() else sys.executable


def main():
    env = SkillEnvironment()
    if env.ensure_venv():
        print(f"\n✅ Environment ready!")
        print(f"   Python: {env.get_python_executable()}")
    else:
        print("\n❌ Environment setup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
