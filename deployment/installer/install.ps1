# MCP Claude Context Server - One-Click Installer for Windows
# v0.5.0

$ErrorActionPreference = "Stop"

# Color functions
function Write-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param($Message)
    Write-Host "→ $Message" -ForegroundColor Yellow
}

function Write-Header {
    Write-Host "================================" -ForegroundColor Blue
    Write-Host "MCP Claude Context Server v0.5.0" -ForegroundColor Blue
    Write-Host "================================" -ForegroundColor Blue
    Write-Host ""
}

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check system requirements
function Test-Requirements {
    Write-Info "Checking system requirements..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 11) {
                Write-Success "Python $major.$minor found"
            } else {
                throw "Python 3.11 or higher required (found $major.$minor)"
            }
        }
    } catch {
        Write-Error "Python 3.11+ is not installed or not in PATH"
        Write-Info "Download from: https://www.python.org/downloads/"
        exit 1
    }
    
    # Check Git
    try {
        git --version | Out-Null
        Write-Success "Git found"
    } catch {
        Write-Error "Git is not installed"
        Write-Info "Download from: https://git-scm.com/download/win"
        exit 1
    }
    
    # Check Chrome
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LocalAppData}\Google\Chrome\Application\chrome.exe"
    )
    
    $chromeFound = $false
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            $chromeFound = $true
            break
        }
    }
    
    if ($chromeFound) {
        Write-Success "Chrome found"
    } else {
        Write-Error "Chrome is not installed"
        Write-Info "Download from: https://www.google.com/chrome/"
        exit 1
    }
}

# Install Poetry
function Install-Poetry {
    try {
        poetry --version | Out-Null
        Write-Success "Poetry already installed"
    } catch {
        Write-Info "Installing Poetry..."
        (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
        $env:Path += ";$env:APPDATA\Python\Scripts"
        Write-Success "Poetry installed"
    }
}

# Setup project
function Setup-Project {
    Write-Info "Setting up project..."
    
    # Create directories
    $directories = @("extracted_messages", "data\db", "exports")
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    Write-Success "Created data directories"
    
    # Install dependencies
    Write-Info "Installing Python dependencies..."
    poetry install --no-dev
    Write-Success "Dependencies installed"
    
    # Install playwright browsers
    Write-Info "Installing Playwright browsers..."
    poetry run playwright install chromium
    Write-Success "Playwright browsers installed"
}

# Setup Chrome extension
function Setup-ChromeExtension {
    Write-Info "Setting up Chrome extension..."
    
    $extensionPath = Join-Path $PWD "extension"
    
    Write-Host ""
    Write-Host "Chrome Extension Setup Instructions:" -ForegroundColor Yellow
    Write-Host "1. Open Chrome and navigate to: chrome://extensions"
    Write-Host "2. Enable 'Developer mode' (toggle in top right)"
    Write-Host "3. Click 'Load unpacked'"
    Write-Host "4. Select this directory: $extensionPath"
    Write-Host "5. The extension icon should appear in your toolbar"
    Write-Host ""
    
    # Create desktop shortcut
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\MCP Claude Extension.lnk")
    $shortcut.TargetPath = $extensionPath
    $shortcut.Save()
    Write-Info "Created desktop shortcut to extension folder"
}

# Migrate existing data
function Migrate-ExistingData {
    $jsonFiles = Get-ChildItem -Path "extracted_messages" -Filter "*.json" -ErrorAction SilentlyContinue
    if ($jsonFiles.Count -gt 0) {
        Write-Info "Found existing conversation data..."
        $response = Read-Host "Migrate existing JSON data to database? (y/n)"
        if ($response -eq 'y') {
            Write-Info "Migrating data to SQLite database..."
            poetry run python scripts/migrate_data.py
            Write-Success "Data migration complete"
        }
    }
}

# Create start script
function Create-StartScript {
    Write-Info "Creating start script..."
    
    $startScript = @'
@echo off
echo Starting MCP Claude Context Server...
echo Press Ctrl+C to stop
echo.

poetry run python -m src.direct_api_server
pause
'@
    
    $startScript | Out-File -FilePath "start.bat" -Encoding ASCII
    Write-Success "Created start.bat script"
}

# Create desktop shortcut
function Create-DesktopShortcut {
    Write-Info "Creating desktop shortcut..."
    
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\MCP Claude Context Server.lnk")
    $shortcut.TargetPath = "cmd.exe"
    $shortcut.Arguments = "/k cd /d `"$PWD`" && start.bat"
    $shortcut.WorkingDirectory = $PWD
    $shortcut.IconLocation = "cmd.exe"
    $shortcut.Save()
    
    Write-Success "Created desktop shortcut"
}

# Print completion message
function Write-Completion {
    Write-Host ""
    Write-Header
    Write-Success "Installation complete!"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "1. Install the Chrome extension (see instructions above)"
    Write-Host "2. Double-click 'start.bat' or the desktop shortcut to start the server"
    Write-Host "3. The MCP server will be available at http://localhost:8000"
    Write-Host ""
    Write-Host "For more information, see README.md" -ForegroundColor Blue
}

# Main installation flow
function Main {
    Write-Header
    
    if (!(Test-Administrator)) {
        Write-Info "Note: Running without administrator privileges"
        Write-Info "Some features may require manual configuration"
    }
    
    Test-Requirements
    Install-Poetry
    Setup-Project
    Setup-ChromeExtension
    Migrate-ExistingData
    Create-StartScript
    Create-DesktopShortcut
    Write-Completion
}

# Run main function
Main
