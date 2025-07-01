# src/__init__.py
"""MCP Claude Context Server - Extract conversations from Claude.ai"""

__version__ = "0.5.0"
__author__ = "Hamza Amjad"

from .direct_api_server import DirectAPIClaudeContextServer, main

__all__ = ["DirectAPIClaudeContextServer", "main", "__version__"]