# 🚀 MCP Claude Context Server - Deployment Guide

## Overview

This guide covers multiple deployment options for the MCP Claude Context Server, from simple one-click installation to advanced configurations.

## Table of Contents

1. [Quick Start (One-Click)](#quick-start-one-click)
2. [Docker Deployment](#docker-deployment)
3. [Desktop Extension](#desktop-extension)
4. [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Quick Start (One-Click)

### macOS/Linux

```bash
curl -sSL https://raw.githubusercontent.com/hamzaamjad/mcp-claude-context/main/deployment/one-click-install.sh | bash
```

### Windows

```powershell
iwr -useb https://raw.githubusercontent.com/hamzaamjad/mcp-claude-context/main/deployment/install.ps1 | iex
```

This will:
- ✅ Install all dependencies
- ✅ Configure Claude Desktop
- ✅ Set up the Chrome extension
- ✅ Start all services
- ✅ Open the configuration UI

---

## 🐳 Docker Deployment

### Simple Docker Compose

```bash
# Download the simple compose file
curl -O https://raw.githubusercontent.com/hamzaamjad/mcp-claude-context/main/docker-compose.simple.yml

# Start services
docker-compose -f docker-compose.simple.yml up -d

# View logs
docker-compose -f docker-compose.simple.yml logs -f
```

### Using Pre-built Image

```bash
# Pull the latest image
docker pull hamzaamjad/mcp-claude-context:latest

# Run with volumes
docker run -d \
  --name mcp-claude-context \
  -p 8000:8000 \
  -p 8765:8765 \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/extracted_messages:/app/extracted_messages \
  hamzaamjad/mcp-claude-context:latest
```

### Docker with Auto-updates

```bash
# Deploy with Watchtower for automatic updates
docker-compose -f docker-compose.simple.yml --profile auto-update up -d
```

---

## 📦 Desktop Extension

### Installing the Desktop Extension

1. **Download the Extension**
   ```bash
   curl -LO https://github.com/hamzaamjad/mcp-claude-context/releases/latest/download/mcp-claude-context.dxt
   ```

2. **Install in Claude Desktop**
   - Open Claude Desktop
   - Go to Settings → Extensions
   - Click "Install from file"
   - Select the downloaded .dxt file

3. **Configure**
   - The configuration UI will open automatically
   - Enter your Claude session key and org ID
   - Click "Save & Test Connection"

### Building from Source

```bash
# Clone repository
git clone https://github.com/hamzaamjad/mcp-claude-context.git
cd mcp-claude-context

# Build desktop extension
npm run build:desktop

# Output will be in dist/mcp-claude-context.dxt
```

---

## 🔧 Manual Installation

### Prerequisites

- Python 3.9 or higher
- Node.js 16+ (for Chrome extension)
- Git

### Step-by-Step

1. **Clone Repository**
   ```bash
   git clone https://github.com/hamzaamjad/mcp-claude-context.git
   cd mcp-claude-context
   ```

2. **Install Dependencies**
   ```bash
   # Using Poetry (recommended)
   poetry install
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Initialize Database**
   ```bash
   poetry run python -c "from src.models.conversation import init_database; init_database()"
   ```

4. **Configure Claude Desktop**
   
   Edit `~/.config/Claude/mcp.json` (Linux) or `~/Library/Application Support/Claude/mcp.json` (macOS):
   
   ```json
   {
     "servers": {
       "claude-context": {
         "command": "/path/to/python",
         "args": ["-m", "src.direct_api_server"],
         "cwd": "/path/to/mcp-claude-context",
         "env": {
           "PYTHONPATH": "/path/to/mcp-claude-context"
         }
       }
     }
   }
   ```

5. **Install Chrome Extension**
   - Open Chrome and go to `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `extension` folder

6. **Start Services**
   ```bash
   # Terminal 1 - Bridge Server
   poetry run python extension/bridge_server.py
   
   # Terminal 2 - MCP Server
   poetry run python -m src.direct_api_server
   ```

---

## ⚙️ Configuration

### Using the Web UI

1. Open http://localhost:8001
2. Navigate through the sections:
   - **Authentication**: Enter Claude credentials
   - **Sync Settings**: Configure auto-sync
   - **Export Settings**: Set export preferences
   - **Rate Limits**: Adjust API rate limits

### Using Environment Variables

```bash
# .env file
CLAUDE_SESSION_KEY=sk-ant-sid01-...
CLAUDE_ORG_ID=28a16e5b-...
LOG_LEVEL=INFO
MCP_DB_PATH=/custom/path/conversations.db
MCP_EXPORT_DIR=/custom/path/exports
```

### Using Configuration File

```yaml
# config.yml
authentication:
  session_key: ${CLAUDE_SESSION_KEY}
  org_id: ${CLAUDE_ORG_ID}

sync:
  auto_sync: true
  interval: 3600  # seconds
  
export:
  formats:
    - markdown
    - json
    - pdf
  default_path: ~/Documents/Claude-Exports

rate_limiting:
  requests_per_second: 3
  burst_size: 10
```

---

## 🛠️ Advanced Configuration

### Custom SSL Certificates

```nginx
# nginx.conf for HTTPS
server {
    listen 443 ssl;
    server_name mcp.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Systemd Service (Linux)

```ini
# /etc/systemd/system/mcp-claude-context.service
[Unit]
Description=MCP Claude Context Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/opt/mcp-claude-context
ExecStart=/opt/mcp-claude-context/venv/bin/python -m src.direct_api_server
Restart=always
Environment="PYTHONPATH=/opt/mcp-claude-context"

[Install]
WantedBy=multi-user.target
```

### LaunchAgent (macOS)

```xml
<!-- ~/Library/LaunchAgents/com.hamzaamjad.mcp-claude-context.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hamzaamjad.mcp-claude-context</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>src.direct_api_server</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/youruser/.mcp/claude-context</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

---

## 🐛 Troubleshooting

### Common Issues

#### Bridge Server Not Starting
```bash
# Check if port is in use
lsof -i :8765

# Kill existing process
kill -9 $(lsof -t -i :8765)

# Restart with debug logging
LOG_LEVEL=DEBUG poetry run python extension/bridge_server.py
```

#### Chrome Extension Not Connecting
1. Check bridge server is running: http://localhost:8765/api/status
2. Verify CORS is enabled in bridge server
3. Check browser console for errors
4. Try reloading the extension

#### Rate Limiting Issues
```bash
# Check current rate limit status
curl http://localhost:8765/api/rate-limit-status

# Reset rate limits
curl -X POST http://localhost:8000/api/rate-limit/reset
```

#### Database Issues
```bash
# Backup database
cp data/db/conversations.db data/db/conversations.backup.db

# Rebuild database
poetry run python deployment/scripts/rebuild_db.py

# Verify integrity
sqlite3 data/db/conversations.db "PRAGMA integrity_check;"
```

### Debug Mode

Enable comprehensive debugging:

```bash
# Set all debug flags
export LOG_LEVEL=DEBUG
export MCP_DEBUG=true
export SQLALCHEMY_ECHO=true

# Run with full debugging
poetry run python -m src.direct_api_server
```

### Health Checks

```bash
# Check all services
curl http://localhost:8000/api/health

# Response should include:
{
  "status": "healthy",
  "services": {
    "mcp_server": "running",
    "bridge_server": "running",
    "database": "connected",
    "chrome_extension": "connected"
  }
}
```

---

## 📚 Additional Resources

- [API Documentation](./API.md)
- [Chrome Extension Guide](./CHROME_EXTENSION.md)
- [Rate Limiting Guide](./bulk_export_rate_limiting.md)
- [Migration Guide](./migration_rate_limiting.md)

## 🤝 Support

- GitHub Issues: [Report bugs](https://github.com/hamzaamjad/mcp-claude-context/issues)
- Discussions: [Ask questions](https://github.com/hamzaamjad/mcp-claude-context/discussions)
- Email: support@example.com

---

**Remember**: Always keep your session keys secure and never commit them to version control!