#!/bin/bash
# Run the MCP Claude Context server

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Run the server with Poetry
echo "Starting MCP Claude Context Server..."
poetry run python -m src.server