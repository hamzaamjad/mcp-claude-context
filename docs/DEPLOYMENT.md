# Deployment Guide

This guide covers various deployment methods for the MCP Claude Context Server v0.5.0.

## Quick Start

### Option 1: Docker (Recommended)

The easiest way to deploy the server is using Docker:

```bash
cd deployment/docker
docker-compose up -d
```

This will:
- Start the MCP server on port 8000
- Start the bridge server on port 9222
- Create persistent volumes for data
- Set up the database automatically

### Option 2: One-Click Installer

#### Mac/Linux:
```bash
cd deployment/installer
chmod +x install.sh
./install.sh
```

#### Windows:
```powershell
cd deployment\installer
.\install.ps1
```

The installer will:
- Check system requirements
- Install Python dependencies
- Set up the database
- Create start scripts
- Guide you through Chrome extension setup

## Detailed Deployment Options

### Docker Deployment

#### Prerequisites
- Docker and Docker Compose installed
- At least 2GB free disk space

#### Configuration

Edit `docker-compose.yml` to customize:
- Port mappings
- Volume locations
- Environment variables

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_DB_PATH` | Database location | `/app/data/db/conversations.db` |
| `MCP_EXPORT_DIR` | Export directory | `/app/exports` |
| `MCP_PORT` | MCP server port | `8000` |
| `BRIDGE_PORT` | Bridge server port | `9222` |
| `LOG_LEVEL` | Logging level | `INFO` |

#### Managing the Container

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Update to latest version
docker-compose pull
docker-compose up -d
```

### Manual Installation

#### Prerequisites
- Python 3.11 or higher
- Chrome or Chromium browser
- Git

#### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/mcp-claude-context.git
   cd mcp-claude-context
   ```

2. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies:**
   ```bash
   poetry install
   ```

4. **Initialize database:**
   ```bash
   poetry run python -c "from src.models.conversation import init_database; init_database()"
   ```

5. **Install Chrome extension:**
   - Open Chrome and go to `chrome://extensions`
   - Enable Developer mode
   - Click "Load unpacked"
   - Select the `extension` directory

6. **Start the server:**
   ```bash
   poetry run python -m src.direct_api_server
   ```

### Production Deployment

For production environments, consider:

#### 1. Using a Process Manager

**systemd (Linux):**

Create `/etc/systemd/system/mcp-claude-context.service`:

```ini
[Unit]
Description=MCP Claude Context Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/mcp-claude-context
ExecStart=/usr/bin/poetry run python -m src.direct_api_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mcp-claude-context
sudo systemctl start mcp-claude-context
```

**PM2 (Node.js):**

```bash
pm2 start "poetry run python -m src.direct_api_server" --name mcp-claude-context
pm2 save
pm2 startup
```

#### 2. Reverse Proxy Setup

**Nginx configuration:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### 3. SSL/TLS

Use Let's Encrypt for free SSL certificates:

```bash
sudo certbot --nginx -d your-domain.com
```

### Database Backup

#### Automated Backups

Create a cron job for regular backups:

```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

`backup-script.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/backups/mcp-claude-context"
DB_PATH="/path/to/data/db/conversations.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_PATH "$BACKUP_DIR/conversations_$TIMESTAMP.db"

# Keep only last 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
```

### Migration from v0.4.0

If upgrading from v0.4.0:

1. **Backup existing data:**
   ```bash
   cp -r extracted_messages extracted_messages_backup
   ```

2. **Run migration:**
   ```bash
   poetry run python deployment/scripts/migrate_data.py
   ```

3. **Verify migration:**
   ```bash
   poetry run python deployment/scripts/migrate_data.py --verify
   ```

### Troubleshooting

#### Common Issues

1. **Port already in use:**
   ```bash
   # Find process using port
   lsof -i :8000
   # Kill process
   kill -9 <PID>
   ```

2. **Database locked:**
   - Ensure only one instance is running
   - Check file permissions
   - Try: `chmod 644 data/db/conversations.db`

3. **Chrome extension not connecting:**
   - Check bridge server is running (port 9222)
   - Verify extension permissions
   - Check browser console for errors

4. **Memory issues with large datasets:**
   - Increase Docker memory limit
   - Use batch processing for exports
   - Consider database optimization

#### Logs

Check logs in these locations:
- Docker: `docker-compose logs`
- Manual: Check terminal output
- Extension: Chrome Developer Tools console

### Performance Tuning

1. **Database optimization:**
   ```sql
   -- Run these in SQLite
   VACUUM;
   ANALYZE;
   ```

2. **Search index optimization:**
   ```bash
   # Rebuild search indexes
   curl -X POST http://localhost:8000/rebuild_search_index
   ```

3. **Memory settings (Docker):**
   ```yaml
   services:
     mcp-claude-context:
       mem_limit: 2g
       memswap_limit: 2g
   ```

## Security Considerations

1. **API Keys:**
   - Never commit session keys to git
   - Use environment variables
   - Rotate keys regularly

2. **Network Security:**
   - Use firewall rules to restrict access
   - Enable HTTPS in production
   - Consider VPN for sensitive data

3. **Data Privacy:**
   - Encrypt database at rest
   - Regular security audits
   - GDPR compliance for exports

## Support

For issues or questions:
1. Check the [GitHub Issues](https://github.com/yourusername/mcp-claude-context/issues)
2. Review logs for error messages
3. Join our Discord community

## Next Steps

After deployment:
1. Configure Claude Desktop to use the MCP server
2. Install and configure the Chrome extension
3. Run initial data extraction
4. Set up regular backups
5. Monitor performance and logs
