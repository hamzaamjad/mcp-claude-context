#!/usr/bin/env python3
"""Test installation and configuration of MCP Claude Context Server."""

import sys
import os
import json
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python {version.major}.{version.minor} detected. Python 3.11+ is required.")
        return False
    print(f"✅ Python {version.major}.{version.minor} detected")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    try:
        import mcp
        print("✅ mcp package found")
    except ImportError:
        print("❌ mcp package not found. Run: pip install mcp")
        return False
    
    try:
        import sqlalchemy
        print("✅ sqlalchemy found")
    except ImportError:
        print("❌ sqlalchemy not found. Run: pip install sqlalchemy")
        return False
    
    return True

def check_claude_desktop_config():
    """Check Claude Desktop configuration."""
    print("\n🔧 Checking Claude Desktop configuration...")
    
    config_paths = {
        "darwin": Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        "linux": Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
        "win32": Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    }
    
    platform = sys.platform
    config_path = config_paths.get(platform)
    
    if not config_path or not config_path.exists():
        print(f"❌ Claude Desktop config not found at: {config_path}")
        print("   Please ensure Claude Desktop is installed")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if "mcpServers" in config and "claude-context" in config["mcpServers"]:
            print("✅ MCP Claude Context server found in config")
            server_config = config["mcpServers"]["claude-context"]
            
            # Check for required environment variables
            env = server_config.get("env", {})
            if "CLAUDE_SESSION_KEY" in env and "CLAUDE_ORG_ID" in env:
                print("✅ Authentication credentials configured")
            else:
                print("⚠️  Authentication credentials not found in config")
                print("   Add CLAUDE_SESSION_KEY and CLAUDE_ORG_ID to the env section")
        else:
            print("❌ MCP Claude Context server not found in config")
            print("   Add the server configuration to claude_desktop_config.json")
            
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False
    
    return True

def check_database():
    """Check if database can be initialized."""
    print("\n💾 Checking database...")
    try:
        from src.models.conversation import init_database
        init_database()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def check_server_startup():
    """Check if server can start."""
    print("\n🚀 Testing server startup...")
    try:
        # Try to import and create server instance
        from src.direct_api_server import DirectAPIClaudeContextServer
        server = DirectAPIClaudeContextServer()
        print("✅ Server instance created successfully")
        return True
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        return False

def test_uvx():
    """Test if uvx is available and working."""
    print("\n🔨 Testing uvx installation...")
    try:
        result = subprocess.run(["uvx", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ uvx is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ uvx not found. Install with: pip install uv")
            return False
    except FileNotFoundError:
        print("❌ uvx not found. Install with: pip install uv")
        return False

def print_example_config():
    """Print example configuration."""
    print("\n📋 Example Claude Desktop configuration:")
    print("""
{
  "mcpServers": {
    "claude-context": {
      "command": "uvx",
      "args": ["mcp-claude-context"],
      "env": {
        "CLAUDE_SESSION_KEY": "sk-ant-sid01-...",
        "CLAUDE_ORG_ID": "28a16e5b-..."
      }
    }
  }
}
""")

def main():
    """Run all tests."""
    print("🔍 MCP Claude Context Server - Installation Test\n")
    
    results = {
        "Python": check_python_version(),
        "Dependencies": check_dependencies(),
        "Claude Desktop": check_claude_desktop_config(),
        "Database": check_database(),
        "Server": check_server_startup(),
        "uvx": test_uvx()
    }
    
    print("\n📊 Summary:")
    all_passed = True
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {test}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✨ All tests passed! Your installation is ready.")
        print("   Start Claude Desktop to begin using MCP Claude Context.")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print_example_config()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())