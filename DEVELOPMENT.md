# Development Guide

## Quick Start

```bash
# Install dependencies (including dev tools)
make install

# Run fast checks during development
make check-quick

# Auto-format code before committing
make format

# Run full test suite
make test-all
```

## Quick Reference

### Daily Development Workflow

```bash
# 1. Make changes to code
vim src/mqtt/bridge.py

# 2. Run fast checks (5-10 seconds)
make check-quick

# 3. Fix any issues automatically
make format

# 4. Before committing, run everything
make test-all
```

### Common Commands

| Command | Duration | Use when |
|---------|----------|----------|
| `make check-quick` | 5-10s | During active development |
| `make format` | 2-3s | Auto-fix formatting |
| `make lint` | 15-20s | Before committing |
| `make test` | 1-2s | Testing code changes |
| `make test-all` | 20-25s | Before pushing |

### What Each Tool Does

| Tool | What it checks | Auto-fixable |
|------|----------------|--------------|
| **Black** | Code formatting | ✅ Yes (`make format`) |
| **isort** | Import order | ✅ Yes (`make format`) |
| **Flake8** | PEP 8 style, unused imports | ❌ Manual fixes |
| **Mypy** | Type hints, type safety | ❌ Manual fixes |
| **Pylint** | Code quality, bugs, complexity | ❌ Manual fixes |

## Available Commands

### Make Commands

| Command | Description | Time |
|---------|-------------|------|
| `make help` | Show all available commands | instant |
| `make install` | Install all dependencies | ~30s |
| `make test` | Run pytest with coverage | ~1-2s |
| `make lint` | Run all linters | ~15-20s |
| `make format` | Auto-format code | ~2-3s |
| `make check-quick` | Fast checks (black, flake8, mypy) | ~5-10s |
| `make test-all` | Full suite (lint + test) | ~20-25s |
| `make clean` | Remove cache files | instant |

### Direct Script Execution

```bash
# Individual scripts
./scripts/format.sh          # Auto-format with black + isort
./scripts/lint.sh            # All linters
./scripts/check-quick.sh     # Fast checks
./scripts/test-all.sh        # Everything

# Check specific files/directories
./scripts/check-quick.sh src/mqtt
./scripts/check-quick.sh src/vestaboard/client.py
```

## Tools Included

### 1. Black - Code Formatter ✨
**Auto-fixes:** Code formatting
**Config:** `pyproject.toml` → `[tool.black]`

```bash
# Check formatting
./venv/bin/python -m black --check src tests

# Auto-format
./venv/bin/python -m black src tests
```

### 2. isort - Import Sorter 📦
**Auto-fixes:** Import order
**Config:** `pyproject.toml` → `[tool.isort]`

```bash
# Check imports
./venv/bin/python -m isort --check-only src tests

# Auto-sort
./venv/bin/python -m isort src tests
```

### 3. Flake8 - PEP 8 Linter 📏
**Checks:** Style violations, unused imports, complexity
**Config:** `.flake8`

```bash
./venv/bin/python -m flake8 src tests
```

Common issues:
- E501: Line too long (handled by black)
- F401: Unused import
- W503: Line break before binary operator

### 4. Mypy - Type Checker 🔍
**Checks:** Type hints, type safety
**Config:** `pyproject.toml` → `[tool.mypy]`

```bash
# Check types
./venv/bin/python -m mypy src

# Check specific file
./venv/bin/python -m mypy src/vestaboard/client.py
```

Common fixes:
```python
# Add type hints
def process_message(msg: str) -> bool:
    return True

# Use Optional for nullable values
from typing import Optional
def get_value() -> Optional[str]:
    return None
```

### 5. Pylint - Advanced Linter 🔬
**Checks:** Code quality, potential bugs, design issues
**Config:** `pyproject.toml` → `[tool.pylint]`

```bash
./venv/bin/python -m pylint src
```

## Recommended Workflow

### During Development
```bash
# Make changes
vim src/mqtt/bridge.py

# Quick check (fast feedback)
make check-quick

# Auto-fix formatting
make format

# Continue coding...
```

### Before Committing
```bash
# Format code
make format

# Run all checks
make test-all

# If everything passes, commit!
git add .
git commit -m "Your message"
```

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
make check-quick
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## IDE Integration

### VS Code

Install extensions:
- Python
- Pylance
- Black Formatter
- isort

Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

### PyCharm

1. Settings → Tools → Black
2. Settings → Tools → External Tools → Add isort
3. Settings → Editor → Inspections → Enable Pylint
4. Settings → Languages & Frameworks → Python → Type Checking → Enable Mypy

## Configuration Files

- `pyproject.toml` - Black, isort, mypy, pylint config
- `.flake8` - Flake8 config
- `pytest.ini` - Pytest config
- `requirements-dev.txt` - Development dependencies

## Troubleshooting

### "Module not found" errors
```bash
make install  # Reinstall all dependencies
```

### Black and isort conflicts
Always run isort before black:
```bash
make format  # Runs in correct order
```

### Mypy errors in external libraries
Add to `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = ["problematic_module.*"]
ignore_missing_imports = true
```

### Pylint too strict
Disable specific checks in `pyproject.toml`:
```toml
[tool.pylint.main]
disable = [
    "C0103",  # invalid-name
]
```

### Tests failing after formatting
This shouldn't happen, but if it does:
```bash
# Check what changed
git diff

# Revert if needed
git checkout -- .

# Report the issue
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements-dev.txt
      - name: Run linting
        run: make lint
      - name: Run tests
        run: make test
```

### GitLab CI

```yaml
test:
  image: python:3.11
  before_script:
    - python -m venv venv
    - source venv/bin/activate
    - pip install -r requirements-dev.txt
  script:
    - make lint
    - make test
```

## Performance Tips

**Fastest feedback:** `make check-quick` (5-10s)
- Only runs black, flake8, mypy
- Skip during rapid iteration

**Full checks:** `make lint` (15-20s)
- Includes pylint (slower but catches more issues)
- Run before committing

**Everything:** `make test-all` (20-25s)
- Lint + tests
- Run before pushing

## Best Practices

1. ✅ Run `make format` before committing
2. ✅ Run `make check-quick` frequently during development
3. ✅ Run `make test-all` before pushing
4. ✅ Fix issues as they appear (don't accumulate tech debt)
5. ✅ Use type hints for new code
6. ✅ Keep functions under 50 lines
7. ✅ Keep modules under 500 lines

## Getting Help

- Script documentation: `./scripts/README.md`
- Tool configs: Check `pyproject.toml` and `.flake8`
- Make help: `make help`
