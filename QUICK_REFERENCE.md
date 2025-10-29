# Quick Reference - Code Quality Commands

## Installation

```bash
make install    # Install all dev dependencies
```

## Daily Development

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

## All Available Commands

### Fast Development Cycle
```bash
make check-quick    # Black, Flake8, Mypy only (fastest)
make format         # Auto-fix formatting issues
```

### Before Committing
```bash
make test-all       # Everything (lint + tests)
make lint           # All linters without tests
make test           # Just tests with coverage
```

### Utilities
```bash
make clean          # Remove cache files
make help           # Show all commands
```

## What Each Tool Does

| Tool | What it checks | Auto-fixable |
|------|----------------|--------------|
| **Black** | Code formatting | ✅ Yes (`make format`) |
| **isort** | Import order | ✅ Yes (`make format`) |
| **Flake8** | PEP 8 style, unused imports | ❌ Manual fixes |
| **Mypy** | Type hints, type safety | ❌ Manual fixes |
| **Pylint** | Code quality, bugs, complexity | ❌ Manual fixes |

## Common Fixes

### Format code automatically
```bash
make format
```

### Check specific file
```bash
./scripts/check-quick.sh src/mqtt/bridge.py
```

### Run single tool
```bash
./venv/bin/python -m black src          # Format
./venv/bin/python -m flake8 src         # Style check
./venv/bin/python -m mypy src           # Type check
./venv/bin/python -m pylint src         # Advanced lint
```

## Exit Codes

- `0` = All checks passed ✅
- `1` = Some checks failed ❌

## Speed Comparison

| Command | Duration | Use when |
|---------|----------|----------|
| `make check-quick` | 5-10s | During active development |
| `make format` | 2-3s | Auto-fix formatting |
| `make lint` | 15-20s | Before committing |
| `make test` | 1-2s | Testing code changes |
| `make test-all` | 20-25s | Before pushing |

## Recommended Workflow

```bash
# 1. Start working
vim src/file.py

# 2. Check frequently during development
make check-quick

# 3. Before commit: auto-fix formatting
make format

# 4. Before commit: verify everything passes
make test-all

# 5. Commit if all green!
git commit -m "Your message"
```

## Configuration

All tools configured in:
- `pyproject.toml` - Black, isort, mypy, pylint
- `.flake8` - Flake8 config
- `pytest.ini` - Test config

## Getting Help

- Full guide: `DEVELOPMENT.md`
- Script details: `scripts/README.md`
- Make commands: `make help`
