# MCP Claude Context Server - Windows Installation Script
# Run as Administrator for best results

$ErrorActionPreference = "Stop"

# Configuration
$REPO_URL = "https://github.com/hamzaamjad/mcp-claude-context"
$INSTALL_DIR = "$env:USERPROFILE\.mcp\claude-context"
$CLAUDE_CONFIG_DIR = "$env:APPDATA\Claude"

Write-Host "MCP Claude Context Server - Windows Installer" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Function to check if running as admin
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to install Python if needed
function Install-Python {
    Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
    
    if (Test-Command "python") {
        $version = python --version 2>&1
        Write-Host "Found: $version" -ForegroundColor Green
        
        # Check version
        $versionNumber = [version]($version -replace 'Python ', '')
        if ($versionNumber -lt [version]"3.11.0") {
            Write-Host "Python 3.11+ required. Please upgrade." -ForegroundColor Red
            return $false
        }
        return $true
    }
    
    Write-Host "Python not found. Installing Python 3.12..." -ForegroundColor Yellow
    
    # Download Python installer
    $pythonUrl = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    
    Write-Host "Downloading Python..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath
    
    # Install Python
    Write-Host "Installing Python (this may take a few minutes)..." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1" -Wait
    
    Remove-Item $installerPath
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    return (Test-Command "python")
}

# Function to install Git if needed
function Install-Git {
    Write-Host "`nChecking Git installation..." -ForegroundColor Yellow
    
    if (Test-Command "git") {
        Write-Host "Git is installed" -ForegroundColor Green
        return $true
    }
    
    Write-Host "Git not found. Installing Git..." -ForegroundColor Yellow
    
    # Download Git installer
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe"
    $installerPath = "$env:TEMP\git-installer.exe"
    
    Write-Host "Downloading Git..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $gitUrl -OutFile $installerPath
    
    # Install Git
    Write-Host "Installing Git..." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -ArgumentList "/VERYSILENT", "/NORESTART" -Wait
    
    Remove-Item $installerPath
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    return (Test-Command "git")
}

# Function to setup Python environment
function Setup-PythonEnvironment {
    Write-Host "`nSetting up Python environment..." -ForegroundColor Yellow
    
    Set-Location $INSTALL_DIR
    
    # Create virtual environment
    python -m venv venv
    
    # Activate virtual environment
    & "$INSTALL_DIR\venv\Scripts\Activate.ps1"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install uv for uvx support
    pip install uv
    
    # Install poetry
    pip install poetry
    
    # Install dependencies
    poetry install --no-dev
    
    Write-Host "Python environment setup complete" -ForegroundColor Green
}

# Function to configure Claude Desktop
function Configure-ClaudeDesktop {
    Write-Host "`nConfiguring Claude Desktop..." -ForegroundColor Yellow
    
    # Create config directory if it doesn't exist
    if (!(Test-Path $CLAUDE_CONFIG_DIR)) {
        New-Item -ItemType Directory -Path $CLAUDE_CONFIG_DIR -Force | Out-Null
    }
    
    $configPath = "$CLAUDE_CONFIG_DIR\claude_desktop_config.json"
    
    # Create or update config
    $config = @{
        mcpServers = @{
            "claude-context" = @{
                command = "uvx"
                args = @("mcp-claude-context")
                env = @{
                    CLAUDE_SESSION_KEY = "REPLACE_WITH_YOUR_SESSION_KEY"
                    CLAUDE_ORG_ID = "REPLACE_WITH_YOUR_ORG_ID"
                }
            }
        }
    }
    
    # If config exists, merge it
    if (Test-Path $configPath) {
        try {
            $existingConfig = Get-Content $configPath | ConvertFrom-Json
            if ($existingConfig.mcpServers) {
                $existingConfig.mcpServers | Get-Member -MemberType NoteProperty | ForEach-Object {
                    if ($_.Name -ne "claude-context") {
                        $config.mcpServers[$_.Name] = $existingConfig.mcpServers.$($_.Name)
                    }
                }
            }
        } catch {
            Write-Host "Warning: Could not parse existing config, creating new one" -ForegroundColor Yellow
        }
    }
    
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath
    Write-Host "Claude Desktop configured successfully" -ForegroundColor Green
    Write-Host "Config location: $configPath" -ForegroundColor Cyan
}

# Function to create Chrome extension installer
function Create-ChromeExtensionInstaller {
    Write-Host "`nCreating Chrome extension installer..." -ForegroundColor Yellow
    
    $extensionPath = "$INSTALL_DIR\extension"
    $htmlPath = "$env:USERPROFILE\Desktop\Install_Claude_Context_Extension.html"
    
    $html = @"
<!DOCTYPE html>
<html>
<head>
    <title>Install Claude Context Extension</title>
    <style>
        body {
            font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
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
            font-family: 'Consolas', monospace;
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
        <p>Navigate to: <code>chrome://extensions</code></p>
    </div>
    
    <div class="step">
        <h3>Step 2: Enable Developer Mode</h3>
        <p>Toggle the "Developer mode" switch in the top right corner</p>
    </div>
    
    <div class="step">
        <h3>Step 3: Load Extension</h3>
        <p>Click "Load unpacked" and select this folder:</p>
        <code>$extensionPath</code>
        <button onclick="navigator.clipboard.writeText('$extensionPath')">Copy Path</button>
    </div>
    
    <div class="step">
        <h3>Step 4: Start Using</h3>
        <p>Visit <a href="https://claude.ai" target="_blank">Claude.ai</a> and look for the extension icon!</p>
    </div>
</body>
</html>
"@
    
    $html | Set-Content $htmlPath
    Write-Host "Chrome extension installer created on Desktop" -ForegroundColor Green
}

# Function to create start/stop scripts
function Create-Scripts {
    Write-Host "`nCreating management scripts..." -ForegroundColor Yellow
    
    # Start script
    $startScript = @"
@echo off
cd /d "$INSTALL_DIR"
echo Starting MCP Claude Context Server...
start /B cmd /c "venv\Scripts\python.exe extension\bridge_server.py > bridge_server.log 2>&1"
start /B cmd /c "venv\Scripts\python.exe -m src.direct_api_server > mcp_server.log 2>&1"
echo Services started!
echo Bridge Server: http://localhost:8765
echo MCP Server: http://localhost:8000
pause
"@
    $startScript | Set-Content "$INSTALL_DIR\start.bat"
    
    # Stop script
    $stopScript = @"
@echo off
echo Stopping MCP Claude Context Server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *bridge_server*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *direct_api_server*" 2>nul
echo Services stopped!
pause
"@
    $stopScript | Set-Content "$INSTALL_DIR\stop.bat"
    
    Write-Host "Management scripts created" -ForegroundColor Green
}

# Function to create desktop shortcut
function Create-DesktopShortcut {
    Write-Host "`nCreating desktop shortcut..." -ForegroundColor Yellow
    
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MCP Claude Context.lnk")
    $Shortcut.TargetPath = "$INSTALL_DIR\start.bat"
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.IconLocation = "shell32.dll,43"
    $Shortcut.Save()
    
    Write-Host "Desktop shortcut created" -ForegroundColor Green
}

# Main installation flow
try {
    Write-Host "`nStarting installation..." -ForegroundColor Yellow
    
    # Check for existing installation
    if (Test-Path $INSTALL_DIR) {
        $response = Read-Host "Existing installation found. Reinstall? (y/n)"
        if ($response -ne 'y') {
            Write-Host "Installation cancelled" -ForegroundColor Yellow
            exit 0
        }
        Remove-Item -Path $INSTALL_DIR -Recurse -Force
    }
    
    # Install dependencies
    if (!(Install-Python)) {
        throw "Failed to install Python"
    }
    
    if (!(Install-Git)) {
        throw "Failed to install Git"
    }
    
    # Clone repository
    Write-Host "`nCloning repository..." -ForegroundColor Yellow
    git clone $REPO_URL $INSTALL_DIR
    
    # Setup Python environment
    Setup-PythonEnvironment
    
    # Configure Claude Desktop
    Configure-ClaudeDesktop
    
    # Create Chrome extension installer
    Create-ChromeExtensionInstaller
    
    # Create scripts
    Create-Scripts
    
    # Create desktop shortcut
    Create-DesktopShortcut
    
    # Initialize database
    Write-Host "`nInitializing database..." -ForegroundColor Yellow
    & "$INSTALL_DIR\venv\Scripts\python.exe" -c "from src.models.conversation import init_database; init_database()"
    
    # Final instructions
    Write-Host "`n✨ Installation Complete! ✨" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Update credentials in: $CLAUDE_CONFIG_DIR\claude_desktop_config.json" -ForegroundColor White
    Write-Host "2. Install Chrome extension (see Desktop for instructions)" -ForegroundColor White
    Write-Host "3. Double-click 'MCP Claude Context' on Desktop to start" -ForegroundColor White
    Write-Host "4. Open Claude Desktop to use the MCP server" -ForegroundColor White
    
    Write-Host "`nPress any key to open the configuration file..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    # Open config file for editing
    notepad "$CLAUDE_CONFIG_DIR\claude_desktop_config.json"
    
} catch {
    Write-Host "`nError: $_" -ForegroundColor Red
    Write-Host "Installation failed. Please check the error above." -ForegroundColor Red
    exit 1
}