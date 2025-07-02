# PyPI Publishing Guide for MCP Claude Context Server

## Table of Contents
1. [PyPI Account Setup](#pypi-account-setup)
2. [API Token Configuration](#api-token-configuration)
3. [Test PyPI vs Production PyPI](#test-pypi-vs-production-pypi)
4. [Poetry Configuration](#poetry-configuration)
5. [Package Naming](#package-naming)
6. [Pre-Publication Checklist](#pre-publication-checklist)
7. [Publishing Process](#publishing-process)
8. [Common Errors & Solutions](#common-errors--solutions)
9. [Post-Publication](#post-publication)

## 1. PyPI Account Setup

### Create PyPI Account
1. Go to https://pypi.org/account/register/
2. Fill in:
   - Username (e.g., `hamzaamjad`)
   - Email address
   - Password (use a strong password)
3. Verify your email address
4. **Enable 2FA** (highly recommended):
   - Go to Account Settings → Enable 2FA
   - Use an authenticator app (Google Authenticator, Authy, etc.)

### Create Test PyPI Account (Optional but Recommended)
1. Go to https://test.pypi.org/account/register/
2. Use the same username as production PyPI
3. This is for testing before real publication

## 2. API Token Configuration

### Why Use API Tokens?
- More secure than username/password
- Can be scoped to specific projects
- Easy to revoke if compromised

### Creating an API Token

1. **Login to PyPI** → Account Settings → API Tokens
2. Click "Add API token"
3. Token name: `mcp-claude-context-publish`
4. Scope: "Entire account" (first time) or "Project: mcp-claude-context" (after first publish)
5. Copy the token (starts with `pypi-`)

### Configure Poetry with Token

**Method 1: Environment Variable (Recommended)**
```bash
export POETRY_PYPI_TOKEN_PYPI="pypi-AgEIcHlwaS5vcmcCJDU4ZjQ2ZjI5LTQzMT..."
```

**Method 2: Poetry Config**
```bash
poetry config pypi-token.pypi pypi-AgEIcHlwaS5vcmcCJDU4ZjQ2ZjI5LTQzMT...
```

**Method 3: Keyring (Most Secure)**
```bash
# Install keyring
pip install keyring

# Store token
keyring set https://upload.pypi.org/legacy/ __token__
# When prompted, paste your token
```

## 3. Test PyPI vs Production PyPI

| Aspect | Test PyPI | Production PyPI |
|--------|-----------|-----------------|
| URL | test.pypi.org | pypi.org |
| Purpose | Testing uploads | Real distribution |
| Persistence | Packages deleted periodically | Permanent |
| Dependencies | May not have all packages | All packages available |
| Users | Testing only | Real users |

### Configure Test PyPI in Poetry
```bash
# Add test repository
poetry config repositories.test-pypi https://test.pypi.org/legacy/

# Add test token
poetry config pypi-token.test-pypi pypi-TEST-TOKEN-HERE
```

## 4. Poetry Configuration

Your `pyproject.toml` should have all required metadata:

```toml
[tool.poetry]
name = "mcp-claude-context"
version = "0.5.0"
description = "MCP server for extracting and analyzing Claude.ai conversations"
authors = ["Hamza Amjad <your.email@example.com>"]
license = "MIT"
readme = "README.md"
homepage = "https://github.com/hamzaamjad/mcp-claude-context"
repository = "https://github.com/hamzaamjad/mcp-claude-context"
documentation = "https://github.com/hamzaamjad/mcp-claude-context/tree/main/docs"
keywords = ["mcp", "claude", "anthropic", "ai", "conversation", "export"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
packages = [{include = "src"}]
include = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
]

[tool.poetry.scripts]
mcp-claude-context = "src.direct_api_server:main"

[tool.poetry.dependencies]
python = "^3.11"
# ... rest of dependencies

[tool.poetry.urls]
"Bug Tracker" = "https://github.com/hamzaamjad/mcp-claude-context/issues"
"Changelog" = "https://github.com/hamzaamjad/mcp-claude-context/blob/main/CHANGELOG.md"
```

## 5. Package Naming

### PyPI Naming Rules
- Lowercase letters, numbers, hyphens, underscores, dots
- Must be unique on PyPI
- Case-insensitive (mcp-claude-context = MCP-Claude-Context)

### MCP Server Naming Convention
- Prefix with `mcp-` for discoverability
- Examples: `mcp-server-sqlite`, `mcp-filesystem`, `mcp-github`
- Your name `mcp-claude-context` follows the convention ✓

## 6. Pre-Publication Checklist

### Code Quality
- [ ] All tests pass: `poetry run pytest`
- [ ] Code is formatted: `poetry run black src/`
- [ ] No linting errors: `poetry run ruff check src/`
- [ ] No security issues: `poetry run pip-audit`

### Documentation
- [ ] README.md is complete and accurate
- [ ] CHANGELOG.md is up to date
- [ ] All doc links work
- [ ] Installation instructions are clear
- [ ] Usage examples are provided

### Package Structure
- [ ] `__init__.py` files exist in all packages
- [ ] Version number is correct in:
  - `pyproject.toml`
  - `src/__init__.py`
  - `CHANGELOG.md`
- [ ] LICENSE file exists
- [ ] No sensitive data in code (API keys, tokens)

### MCP Specific
- [ ] `main()` function works correctly
- [ ] Server starts with `uvx mcp-claude-context`
- [ ] Claude Desktop config example is correct
- [ ] All MCP tools are documented

### Build Test
```bash
# Clean previous builds
rm -rf dist/

# Build package
poetry build

# Check the contents
tar -tzf dist/mcp-claude-context-*.tar.gz | head -20

# Check wheel contents
unzip -l dist/mcp-claude-context-*.whl | head -20
```

## 7. Publishing Process

### Step 1: Test with Test PyPI
```bash
# Build fresh
poetry build

# Publish to test
poetry publish -r test-pypi

# Test installation
pip install --index-url https://test.pypi.org/simple/ mcp-claude-context

# Test it works
uvx --index-url https://test.pypi.org/simple/ mcp-claude-context
```

### Step 2: Publish to Production PyPI
```bash
# Build fresh (if not already)
poetry build

# Publish to production
poetry publish

# You'll see:
# Publishing mcp-claude-context (0.5.0) to PyPI
# - Uploading mcp_claude_context-0.5.0-py3-none-any.whl 100%
# - Uploading mcp-claude-context-0.5.0.tar.gz 100%
```

### Step 3: Verify Publication
1. Check https://pypi.org/project/mcp-claude-context/
2. Test installation:
   ```bash
   # In a new virtual environment
   pip install mcp-claude-context
   
   # Test with uvx
   uvx mcp-claude-context
   ```

## 8. Common Errors & Solutions

### Authentication Failed
```
Error: 403 Forbidden
```
**Solution**: Check your API token is correct and not expired

### Package Name Already Exists
```
Error: 400 Bad Request
The name 'mcp-claude-context' is already in use
```
**Solution**: The package already exists. To update, bump the version number

### Invalid Version
```
Error: 400 Bad Request
Invalid version: 0.5.0.dev1
```
**Solution**: Use proper version format (0.5.0, not 0.5.0.dev1)

### Missing Required Fields
```
Error: 400 Bad Request
Metadata is missing required fields: author_email
```
**Solution**: Add missing metadata to pyproject.toml

### Build Errors
```
Error: No module named 'src'
```
**Solution**: Ensure `packages = [{include = "src"}]` is in pyproject.toml

### MCP Specific Issues
```
Error: entry point mcp-claude-context not found
```
**Solution**: Verify the script entry in pyproject.toml points to correct function

## 9. Post-Publication

### Immediate Steps
1. **Test Installation**:
   ```bash
   # Create fresh environment
   python -m venv test-env
   source test-env/bin/activate  # or test-env\Scripts\activate on Windows
   
   # Install and test
   pip install mcp-claude-context
   uvx mcp-claude-context --version
   ```

2. **Update Documentation**:
   - Update README with PyPI badge
   - Add installation instructions: `pip install mcp-claude-context`
   - Update Claude Desktop config examples

3. **Create GitHub Release**:
   - Tag the version: `git tag v0.5.0`
   - Push tag: `git push origin v0.5.0`
   - Create release on GitHub with changelog

### Monitoring
- Check download stats: https://pypistats.org/packages/mcp-claude-context
- Monitor issues: GitHub Issues
- Check for security alerts: GitHub Security tab

### Future Updates
```bash
# Bump version in pyproject.toml
poetry version patch  # or minor/major

# Update CHANGELOG.md

# Build and publish
poetry build
poetry publish
```

## Best Practices

1. **Always test on Test PyPI first**
2. **Never publish credentials or API keys**
3. **Use semantic versioning** (MAJOR.MINOR.PATCH)
4. **Keep README up to date**
5. **Respond to user issues quickly**
6. **Use GitHub Actions for automated publishing** (optional)

## Example GitHub Action for Publishing

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install Poetry
      run: pip install poetry
    - name: Build and publish
      env:
        POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_TOKEN }}
      run: |
        poetry build
        poetry publish
```

---

## Ready to Publish?

Once you've completed the checklist and setup:

```bash
# Final commands
poetry build
poetry publish

# Your package will be live at:
# https://pypi.org/project/mcp-claude-context/

# Users can install with:
# uvx mcp-claude-context
```

Good luck with your first PyPI publication! 🚀