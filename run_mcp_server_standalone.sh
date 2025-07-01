#!/bin/bash
# Run the MCP Claude Context server with proper environment setup

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Add common Poetry installation paths to PATH
export PATH="$HOME/.local/bin:$HOME/.poetry/bin:/usr/local/bin:$PATH"

# Check if poetry exists
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Trying to use Python directly..." >&2
    
    # Try to run with Python directly
    cd "$SCRIPT_DIR"
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
    
    # Check if we have a virtual environment
    if [ -d ".venv" ]; then
        echo "Using local .venv" >&2
        source .venv/bin/activate
    fi
    
    # Run the server directly with Python
    exec python -m src.server
else
    # Run with Poetry
    cd "$SCRIPT_DIR"
    exec poetry run python -m src.server
fi