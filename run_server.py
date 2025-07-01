#!/usr/bin/env python3
"""Run the MCP Claude Context server."""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())