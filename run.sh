#!/bin/bash
# Run the MCP Claude Context server

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Set up environment
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Run with poetry
cd "$SCRIPT_DIR"
exec poetry run python -m src.direct_api_server