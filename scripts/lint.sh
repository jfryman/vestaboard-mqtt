#!/bin/bash
# Comprehensive linting and type checking script

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SRC_DIR="src"
TESTS_DIR="tests"
ALL_DIRS="$SRC_DIR $TESTS_DIR"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Python Code Quality Checks          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Track failures
FAILED=0

# Function to run a check
run_check() {
    local name=$1
    local cmd=$2

    echo -e "${YELLOW}► Running $name...${NC}"
    if eval "$cmd"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        echo ""
    else
        echo -e "${RED}✗ $name failed${NC}"
        echo ""
        FAILED=1
    fi
}

# 1. Black - Code formatting check
run_check "Black (format check)" \
    "./venv/bin/python -m black --check --diff $ALL_DIRS"

# 2. isort - Import sorting check
run_check "isort (import sorting)" \
    "./venv/bin/python -m isort --check-only --diff $ALL_DIRS"

# 3. Flake8 - PEP 8 style check
run_check "Flake8 (PEP 8 style)" \
    "./venv/bin/python -m flake8 $ALL_DIRS"

# 4. Mypy - Type checking
run_check "Mypy (type checking)" \
    "./venv/bin/python -m mypy $SRC_DIR"

# 5. Pylint - Advanced linting
run_check "Pylint (code analysis)" \
    "./venv/bin/python -m pylint $SRC_DIR"

# Summary
echo -e "${BLUE}═══════════════════════════════════════${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi
