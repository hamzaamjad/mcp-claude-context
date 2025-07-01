# bootstrap.sh
#!/bin/bash
set -euo pipefail

echo "🚀 Setting up MCP Claude Context Server..."

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
poetry install

# Install Playwright browsers
poetry run playwright install chromium

# Create necessary directories
mkdir -p src/{extractors,models} extension tests/fixtures

echo "✅ Setup complete! Run 'poetry run pytest' to verify."