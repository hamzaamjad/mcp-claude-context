#!/bin/bash
# One-click installation script for MCP Claude Context Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/hamzaamjad/mcp-claude-context"
INSTALL_DIR="$HOME/.mcp/claude-context"
DESKTOP_ENTRY="$HOME/.local/share/applications/mcp-claude-context.desktop"

echo -e "${GREEN}MCP Claude Context Server - One Click Installer${NC}"
echo "================================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install dependencies
install_dependencies() {
    local os=$1
    
    echo -e "${YELLOW}Installing dependencies...${NC}"
    
    case $os in
        "linux")
            if command_exists apt; then
                sudo apt update
                sudo apt install -y python3 python3-pip python3-venv git
            elif command_exists yum; then
                sudo yum install -y python3 python3-pip git
            fi
            ;;
        "macos")
            if ! command_exists brew; then
                echo "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python3 git
            ;;
        "windows")
            echo "Please install Python 3.9+ and Git manually from:"
            echo "- Python: https://www.python.org/downloads/"
            echo "- Git: https://git-scm.com/download/win"
            exit 1
            ;;
    esac
}

# Function to setup Python environment
setup_python_env() {
    echo -e "${YELLOW}Setting up Python environment...${NC}"
    
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install poetry
    poetry install --no-dev
}

# Function to configure Claude Desktop
configure_claude_desktop() {
    echo -e "${YELLOW}Configuring Claude Desktop...${NC}"
    
    local claude_config_dir
    case $(detect_os) in
        "macos")
            claude_config_dir="$HOME/Library/Application Support/Claude"
            ;;
        "linux")
            claude_config_dir="$HOME/.config/Claude"
            ;;
        "windows")
            claude_config_dir="$APPDATA/Claude"
            ;;
    esac
    
    mkdir -p "$claude_config_dir"
    
    # Create MCP config
    cat > "$claude_config_dir/mcp.json" << EOF
{
  "servers": {
    "claude-context": {
      "command": "$INSTALL_DIR/venv/bin/python",
      "args": ["-m", "src.direct_api_server"],
      "cwd": "$INSTALL_DIR",
      "env": {
        "PYTHONPATH": "$INSTALL_DIR"
      }
    }
  }
}
EOF
    
    echo -e "${GREEN}✓ Claude Desktop configured${NC}"
}

# Function to install Chrome extension
install_chrome_extension() {
    echo -e "${YELLOW}Setting up Chrome extension...${NC}"
    
    local extension_dir="$INSTALL_DIR/extension"
    
    # Create Chrome extension loader
    cat > "$HOME/Desktop/Install_Claude_Context_Extension.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Install Claude Context Extension</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            line-height: 1.6;
        }
        .step {
            background: #f4f4f4;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
        code {
            background: #e9ecef;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: monospace;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <h1>📦 Install Claude Context Chrome Extension</h1>
    
    <p>Follow these steps to install the Chrome extension:</p>
    
    <div class="step">
        <h3>Step 1: Open Chrome Extensions</h3>
        <p>Click the button below or navigate to <code>chrome://extensions</code></p>
        <button onclick="alert('Copy this URL: chrome://extensions')">Open Extensions Page</button>
    </div>
    
    <div class="step">
        <h3>Step 2: Enable Developer Mode</h3>
        <p>Toggle the "Developer mode" switch in the top right corner</p>
    </div>
    
    <div class="step">
        <h3>Step 3: Load Extension</h3>
        <p>Click "Load unpacked" and select this folder:</p>
        <code>$extension_dir</code>
        <button onclick="navigator.clipboard.writeText('$extension_dir')">Copy Path</button>
    </div>
    
    <div class="step">
        <h3>Step 4: Start Using</h3>
        <p>Visit <a href="https://claude.ai" target="_blank">Claude.ai</a> and look for the extension icon!</p>
    </div>
    
    <hr>
    <p><small>Extension location: <code>$extension_dir</code></small></p>
</body>
</html>
EOF
    
    echo -e "${GREEN}✓ Chrome extension installer created on Desktop${NC}"
}

# Function to create desktop shortcuts
create_shortcuts() {
    echo -e "${YELLOW}Creating shortcuts...${NC}"
    
    case $(detect_os) in
        "linux")
            mkdir -p "$HOME/.local/share/applications"
            cat > "$DESKTOP_ENTRY" << EOF
[Desktop Entry]
Name=MCP Claude Context
Comment=Extract and analyze Claude.ai conversations
Exec=$INSTALL_DIR/venv/bin/python -m src.direct_api_server
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;
EOF
            chmod +x "$DESKTOP_ENTRY"
            ;;
        "macos")
            # Create macOS app bundle
            local app_dir="/Applications/MCP Claude Context.app"
            mkdir -p "$app_dir/Contents/MacOS"
            mkdir -p "$app_dir/Contents/Resources"
            
            cat > "$app_dir/Contents/MacOS/mcp-claude-context" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python -m src.direct_api_server
EOF
            chmod +x "$app_dir/Contents/MacOS/mcp-claude-context"
            
            # Create Info.plist
            cat > "$app_dir/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>mcp-claude-context</string>
    <key>CFBundleName</key>
    <string>MCP Claude Context</string>
    <key>CFBundleIdentifier</key>
    <string>com.hamzaamjad.mcp-claude-context</string>
    <key>CFBundleVersion</key>
    <string>0.6.0</string>
</dict>
</plist>
EOF
            ;;
    esac
    
    echo -e "${GREEN}✓ Shortcuts created${NC}"
}

# Function to start services
start_services() {
    echo -e "${YELLOW}Starting services...${NC}"
    
    # Start bridge server in background
    cd "$INSTALL_DIR"
    source venv/bin/activate
    nohup python extension/bridge_server.py > bridge_server.log 2>&1 &
    local bridge_pid=$!
    
    # Start MCP server
    nohup python -m src.direct_api_server > mcp_server.log 2>&1 &
    local mcp_pid=$!
    
    # Save PIDs
    echo "$bridge_pid" > "$INSTALL_DIR/.bridge_server.pid"
    echo "$mcp_pid" > "$INSTALL_DIR/.mcp_server.pid"
    
    sleep 3
    
    # Check if services started
    if kill -0 $bridge_pid 2>/dev/null && kill -0 $mcp_pid 2>/dev/null; then
        echo -e "${GREEN}✓ Services started successfully${NC}"
        echo "  - Bridge Server: http://localhost:8765"
        echo "  - MCP Server: http://localhost:8000"
    else
        echo -e "${RED}✗ Failed to start services${NC}"
        echo "Check logs at: $INSTALL_DIR/*.log"
        exit 1
    fi
}

# Main installation flow
main() {
    local os=$(detect_os)
    
    echo "Detected OS: $os"
    echo ""
    
    # Check for existing installation
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Existing installation found at $INSTALL_DIR${NC}"
        read -p "Reinstall? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            echo "Installation cancelled"
            exit 0
        fi
    fi
    
    # Install dependencies
    install_dependencies "$os"
    
    # Clone repository
    echo -e "${YELLOW}Downloading MCP Claude Context Server...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    
    # Setup Python environment
    setup_python_env
    
    # Configure Claude Desktop
    configure_claude_desktop
    
    # Install Chrome extension
    install_chrome_extension
    
    # Create shortcuts
    create_shortcuts
    
    # Initialize database
    echo -e "${YELLOW}Initializing database...${NC}"
    cd "$INSTALL_DIR"
    source venv/bin/activate
    python -c "from src.models.conversation import init_database; init_database()"
    
    # Start services
    start_services
    
    # Final instructions
    echo ""
    echo -e "${GREEN}✨ Installation Complete! ✨${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Install Chrome extension (see Desktop for instructions)"
    echo "2. Open Claude Desktop and verify MCP server appears"
    echo "3. Visit http://localhost:8001 for configuration"
    echo ""
    echo "Services are running at:"
    echo "  - Bridge Server: http://localhost:8765"
    echo "  - MCP Server: http://localhost:8000"
    echo "  - Config UI: http://localhost:8001"
    echo ""
    echo "To stop services:"
    echo "  $INSTALL_DIR/stop.sh"
    echo ""
    echo "To start services:"
    echo "  $INSTALL_DIR/start.sh"
    
    # Create stop script
    cat > "$INSTALL_DIR/stop.sh" << 'EOF'
#!/bin/bash
if [ -f .bridge_server.pid ]; then
    kill $(cat .bridge_server.pid) 2>/dev/null
    rm .bridge_server.pid
fi
if [ -f .mcp_server.pid ]; then
    kill $(cat .mcp_server.pid) 2>/dev/null
    rm .mcp_server.pid
fi
echo "Services stopped"
EOF
    chmod +x "$INSTALL_DIR/stop.sh"
    
    # Create start script
    cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
nohup python extension/bridge_server.py > bridge_server.log 2>&1 &
echo $! > .bridge_server.pid
nohup python -m src.direct_api_server > mcp_server.log 2>&1 &
echo $! > .mcp_server.pid
echo "Services started"
EOF
    chmod +x "$INSTALL_DIR/start.sh"
    
    # Open configuration UI
    if command_exists xdg-open; then
        xdg-open "http://localhost:8001" 2>/dev/null &
    elif command_exists open; then
        open "http://localhost:8001" 2>/dev/null &
    fi
}

# Run main installation
main