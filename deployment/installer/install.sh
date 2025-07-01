#!/bin/bash

# MCP Claude Context Server - One-Click Installer for Mac/Linux
# v0.5.0

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}MCP Claude Context Server v0.5.0${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

check_requirements() {
    print_info "Checking system requirements..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.11"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_error "Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
    print_success "Python $PYTHON_VERSION found"
    
    # Check for Git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    print_success "Git found"
    
    # Check for Chrome/Chromium
    if command -v google-chrome &> /dev/null || command -v chromium &> /dev/null || command -v chromium-browser &> /dev/null; then
        print_success "Chrome/Chromium found"
    else
        print_error "Chrome or Chromium is required but not found"
        print_info "Please install Chrome from https://www.google.com/chrome/"
        exit 1
    fi
}

install_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_info "Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
        print_success "Poetry installed"
    else
        print_success "Poetry already installed"
    fi
}

setup_project() {
    print_info "Setting up project..."
    
    # Create necessary directories
    mkdir -p extracted_messages data/db exports
    print_success "Created data directories"
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    poetry install --no-dev
    print_success "Dependencies installed"
    
    # Install playwright browsers
    print_info "Installing Playwright browsers..."
    poetry run playwright install chromium
    print_success "Playwright browsers installed"
}

setup_chrome_extension() {
    print_info "Setting up Chrome extension..."
    
    EXTENSION_PATH=$(pwd)/extension
    
    echo ""
    echo -e "${YELLOW}Chrome Extension Setup Instructions:${NC}"
    echo "1. Open Chrome and navigate to: chrome://extensions"
    echo "2. Enable 'Developer mode' (toggle in top right)"
    echo "3. Click 'Load unpacked'"
    echo "4. Select this directory: $EXTENSION_PATH"
    echo "5. The extension icon should appear in your toolbar"
    echo ""
    
    # Create a desktop shortcut for the extension directory
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e "tell application \"Finder\" to make alias file to POSIX file \"$EXTENSION_PATH\" at POSIX file \"$HOME/Desktop\"" 2>/dev/null || true
        print_info "Created desktop shortcut to extension folder (macOS)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        ln -sf "$EXTENSION_PATH" "$HOME/Desktop/MCP-Claude-Extension" 2>/dev/null || true
        print_info "Created desktop shortcut to extension folder (Linux)"
    fi
}

migrate_existing_data() {
    if [ -d "extracted_messages" ] && [ "$(ls -A extracted_messages/*.json 2>/dev/null | wc -l)" -gt 0 ]; then
        print_info "Found existing conversation data..."
        read -p "Migrate existing JSON data to database? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Migrating data to SQLite database..."
            poetry run python scripts/migrate_data.py
            print_success "Data migration complete"
        fi
    fi
}

create_start_script() {
    print_info "Creating start script..."
    
    cat > start.sh << 'EOF'
#!/bin/bash
# Start MCP Claude Context Server

export PATH="$HOME/.local/bin:$PATH"

echo "Starting MCP Claude Context Server..."
echo "Press Ctrl+C to stop"
echo ""

# Start the server
poetry run python -m src.direct_api_server

EOF
    
    chmod +x start.sh
    print_success "Created start.sh script"
}

create_desktop_entry() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_info "Creating desktop entry..."
        
        DESKTOP_FILE="$HOME/.local/share/applications/mcp-claude-context.desktop"
        mkdir -p "$HOME/.local/share/applications"
        
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MCP Claude Context
Comment=Extract and analyze Claude.ai conversations
Exec=$(pwd)/start.sh
Icon=$(pwd)/docs/icon.png
Terminal=true
Categories=Development;Utility;
EOF
        
        chmod +x "$DESKTOP_FILE"
        print_success "Created desktop entry"
    fi
}

print_completion() {
    echo ""
    print_header
    print_success "Installation complete!"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Install the Chrome extension (see instructions above)"
    echo "2. Run './start.sh' to start the server"
    echo "3. The MCP server will be available at http://localhost:8000"
    echo ""
    echo -e "${BLUE}For more information, see README.md${NC}"
}

# Main installation flow
main() {
    print_header
    check_requirements
    install_poetry
    setup_project
    setup_chrome_extension
    migrate_existing_data
    create_start_script
    create_desktop_entry
    print_completion
}

# Run main function
main
