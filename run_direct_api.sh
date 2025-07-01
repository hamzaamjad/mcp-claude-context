#!/bin/bash
# Run the Direct API MCP Claude Context server

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Set up environment
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Use Poetry's virtual environment Python directly
exec /Users/hamzaamjad/Library/Caches/pypoetry/virtualenvs/mcp-claude-context-JpC4BiUh-py3.13/bin/python -m src.direct_api_server