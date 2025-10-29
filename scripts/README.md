# Development Scripts

This directory contains scripts for code quality checks, formatting, and testing.

## Quick Reference

```bash
# Fast checks during development
make check-quick          # Black, Flake8, Mypy only (fastest)

# Auto-fix formatting issues
make format              # Run black + isort

# Full quality checks
make lint                # All linters (includes pylint)

# Run tests
make test                # Run pytest with coverage

# Run everything before commit
make test-all            # Lint + Test (recommended before push)
```

## Individual Scripts

### 🚀 check-quick.sh
**Fast feedback loop for active development**

Runs the three fastest checks:
- Black (format check)
- Flake8 (PEP 8 style)
- Mypy (type checking)

```bash
./scripts/check-quick.sh
./scripts/check-quick.sh src/mqtt  # Check specific directory
```

### ✨ format.sh
**Auto-format your code**

Automatically fixes formatting issues:
- isort: Sorts imports
- black: Formats code to PEP 8

```bash
./scripts/format.sh
```

**Tip:** Run this before committing to auto-fix most issues!

### 🔍 lint.sh
**Comprehensive code quality checks**

Runs all linters in order:
1. **Black** - Code formatting (--check mode)
2. **isort** - Import sorting (--check mode)
3. **Flake8** - PEP 8 style compliance
4. **Mypy** - Static type checking
5. **Pylint** - Advanced code analysis

```bash
./scripts/lint.sh
```

Exit codes:
- `0` - All checks passed
- `1` - One or more checks failed

### 🧪 test-all.sh
**Full test suite (lint + tests)**

Runs everything:
1. All linting checks (lint.sh)
2. Full pytest suite with coverage

```bash
./scripts/test-all.sh
```

**Recommended:** Run this before pushing to ensure CI will pass.

## Tool Configuration

### Black
- Config: `pyproject.toml` → `[tool.black]`
- Line length: 100
- Target: Python 3.11+

### isort
- Config: `pyproject.toml` → `[tool.isort]`
- Profile: black (compatible with black)
- Line length: 100

### Flake8
- Config: `.flake8`
- Max line length: 100
- Ignores: E203, W503, E501 (conflicts with black)

### Mypy
- Config: `pyproject.toml` → `[tool.mypy]`
- Checks: return types, unused configs, redundant casts
- Ignores: paho.mqtt (missing stubs)

### Pylint
- Config: `pyproject.toml` → `[tool.pylint]`
- Max line length: 100
- Disabled: C0103, R0903, R0913, W0212

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml (example)
- name: Install dependencies
  run: make install

- name: Run linting
  run: make lint

- name: Run tests
  run: make test
```

## Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
make check-quick
```

## Troubleshooting

### "Module not found" errors
```bash
make install  # Reinstall dependencies
```

### Black/isort conflicts
Format should always be run after isort:
```bash
make format  # Runs isort then black in correct order
```

### Mypy type errors
1. Check if type stubs are installed: `pip list | grep types-`
2. Add type: ignore comments for external libraries
3. Configure in `pyproject.toml` → `[[tool.mypy.overrides]]`

### Pylint too strict
Disable specific rules in `pyproject.toml`:
```toml
[tool.pylint.main]
disable = [
    "C0103",  # invalid-name
]
```

## Best Practices

1. **During development:** Run `make check-quick` frequently
2. **Before committing:** Run `make format` to auto-fix issues
3. **Before pushing:** Run `make test-all` to ensure everything passes
4. **CI failures:** Check the specific tool output and fix locally

## Performance

Typical execution times (on modern MacBook):
- `check-quick`: ~5-10 seconds
- `format`: ~2-3 seconds
- `lint`: ~15-20 seconds (includes pylint)
- `test`: ~1-2 seconds (271 tests)
- `test-all`: ~20-25 seconds (lint + test)
