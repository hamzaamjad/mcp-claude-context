#!/usr/bin/env python3
"""Install Playwright browsers after poetry install."""

import subprocess
import sys

def install_playwright_browsers():
    """Install Playwright browsers."""
    print("Installing Playwright browsers...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("Playwright browsers installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Playwright browsers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_playwright_browsers()