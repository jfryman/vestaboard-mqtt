.PHONY: help install test lint format check-quick test-all clean

# Default target
help:
	@echo "Vestaboard MQTT Bridge - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install all dependencies including dev tools"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run pytest tests with coverage"
	@echo "  make test-all       Run ALL checks (lint + tests)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run all linters (black, isort, flake8, mypy, pylint)"
	@echo "  make format         Auto-format code (black + isort)"
	@echo "  make check-quick    Quick checks (black, flake8, mypy only)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove cache files and build artifacts"

# Install dependencies
install:
	./venv/bin/pip install -r requirements-dev.txt

# Run tests
test:
	./venv/bin/pytest tests/

# Run all linting
lint:
	./scripts/lint.sh

# Auto-format code
format:
	./scripts/format.sh

# Quick checks (fast feedback)
check-quick:
	./scripts/check-quick.sh src tests

# Run everything (lint + test)
test-all:
	./scripts/test-all.sh

# Clean up cache and build files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	@echo "Cleaned up cache and build files"
