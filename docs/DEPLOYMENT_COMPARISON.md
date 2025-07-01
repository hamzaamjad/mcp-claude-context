# MCP Server Deployment Methods Comparison

## Official Anthropic Servers

### filesystem server
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
    }
  }
}
```
- ✅ Zero installation with npx
- ✅ Simple one-line command
- ✅ No configuration needed

### github server
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<token>"
      }
    }
  }
}
```
- ✅ Zero installation
- ✅ Environment variable for auth
- ✅ Cross-platform

## Our MCP Claude Context Server

### Using uvx (Recommended)
```json
{
  "mcpServers": {
    "claude-context": {
      "command": "uvx",
      "args": ["mcp-claude-context"],
      "env": {
        "CLAUDE_SESSION_KEY": "sk-ant-...",
        "CLAUDE_ORG_ID": "org-..."
      }
    }
  }
}
```
- ✅ Zero installation like npx
- ✅ Python ecosystem (uvx = npx for Python)
- ✅ Environment variables for auth
- ✅ Auto-updates with `uvx mcp-claude-context@latest`

### Alternative Methods We Support

#### Direct from GitHub
```json
{
  "command": "uvx",
  "args": ["git+https://github.com/hamzaamjad/mcp-claude-context"]
}
```

#### Docker
```json
{
  "command": "docker",
  "args": ["run", "-i", "--rm", "hamzaamjad/mcp-claude-context:latest"]
}
```

#### Local Development
```json
{
  "command": "python",
  "args": ["-m", "src.direct_api_server"],
  "cwd": "/path/to/mcp-claude-context"
}
```

## Comparison Table

| Feature | Official Servers | MCP Claude Context |
|---------|-----------------|-------------------|
| Zero Install | ✅ npx | ✅ uvx |
| Package Registry | npm | PyPI |
| Language | TypeScript | Python |
| Auth Method | Env vars | Env vars |
| Auto Updates | npx @latest | uvx @latest |
| Docker Support | ❌ | ✅ |
| GUI Config | ❌ | ✅ |
| Chrome Extension | ❌ | ✅ |

## Why uvx?

1. **Python Equivalent of npx**
   - No global installation needed
   - Automatic dependency management
   - Isolated environments

2. **Cross-Platform**
   - Works on Windows, macOS, Linux
   - Better than pip for MCP servers
   - Handles Python version requirements

3. **Simple Updates**
   ```bash
   # Just restart Claude Desktop, uvx handles updates
   uvx mcp-claude-context@latest
   ```

4. **Development Friendly**
   ```bash
   # Test local changes
   uvx --from . mcp-claude-context
   
   # Test from branch
   uvx --from git+https://github.com/user/repo@branch mcp-claude-context
   ```

## Best Practices We Follow

1. **Environment Variables for Secrets**
   - Never put API keys in args
   - Use env section for credentials

2. **Simple Command Structure**
   - Single command: `uvx mcp-claude-context`
   - No complex arguments needed

3. **Helpful Error Messages**
   - Clear instructions when auth fails
   - Guidance for getting credentials

4. **Progressive Enhancement**
   - Works with just uvx
   - Optional Docker for production
   - Optional GUI for configuration

## Migration from Other Deployment Methods

### From Manual Installation
```bash
# Before (complex)
cd /path/to/mcp-claude-context
poetry install
poetry run python -m src.direct_api_server

# After (simple)
uvx mcp-claude-context
```

### From Docker
```bash
# Before
docker run -d -p 8000:8000 -v ... hamzaamjad/mcp-claude-context

# After (in Claude Desktop config)
"command": "uvx",
"args": ["mcp-claude-context"]
```

## Publishing to PyPI

To enable uvx deployment:

1. **Prepare package**
   ```bash
   poetry build
   ```

2. **Publish to PyPI**
   ```bash
   poetry publish
   ```

3. **Users can then run**
   ```bash
   uvx mcp-claude-context
   ```

This makes our server as easy to use as the official Anthropic servers!