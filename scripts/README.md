# Development Scripts

This directory contains scripts for code quality checks, formatting, and testing.

**For complete development workflow documentation, see [DEVELOPMENT.md](../DEVELOPMENT.md).**

## Quick Usage

```bash
# Fast checks during development
./scripts/check-quick.sh

# Auto-format code
./scripts/format.sh

# Full quality checks
./scripts/lint.sh

# Run everything (lint + tests)
./scripts/test-all.sh
```

## Individual Scripts

### check-quick.sh
Fast feedback loop for active development.

Runs: Black (format check), Flake8 (PEP 8 style), Mypy (type checking)

```bash
./scripts/check-quick.sh                    # Check everything
./scripts/check-quick.sh src/mqtt           # Check specific directory
./scripts/check-quick.sh src/config.py      # Check specific file
```

### format.sh
Automatically fixes formatting issues.

Runs: isort (sorts imports), black (formats code to PEP 8)

```bash
./scripts/format.sh
```

**Tip:** Run this before committing to auto-fix most issues!

### lint.sh
Comprehensive code quality checks.

Runs all linters in order:
1. Black - Code formatting (--check mode)
2. isort - Import sorting (--check mode)
3. Flake8 - PEP 8 style compliance
4. Mypy - Static type checking
5. Pylint - Advanced code analysis

```bash
./scripts/lint.sh
```

Exit codes:
- `0` - All checks passed
- `1` - One or more checks failed

### test-all.sh
Full test suite (lint + tests).

Runs everything:
1. All linting checks (lint.sh)
2. Full pytest suite with coverage

```bash
./scripts/test-all.sh
```

**Recommended:** Run this before pushing to ensure CI will pass.

## Tool Configuration

All tools are configured in the project root:
- `pyproject.toml` - Black, isort, mypy, pylint config
- `.flake8` - Flake8 config
- `pytest.ini` - Test config

See [DEVELOPMENT.md](../DEVELOPMENT.md) for detailed configuration information.

## CI/CD Integration

These scripts are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
- name: Install dependencies
  run: make install

- name: Run linting
  run: make lint

- name: Run tests
  run: make test
```

## Best Practices

1. ✅ Run `./scripts/format.sh` before committing
2. ✅ Run `./scripts/check-quick.sh` frequently during development
3. ✅ Run `./scripts/test-all.sh` before pushing
4. ✅ Fix issues as they appear (don't accumulate tech debt)
