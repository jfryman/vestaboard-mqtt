#!/bin/bash
# Run all tests and quality checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILED=0

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Full Test & Quality Suite           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 1. Run linting
echo -e "${YELLOW}═══ Step 1: Code Quality Checks ═══${NC}"
if ./scripts/lint.sh; then
    echo -e "${GREEN}✓ Linting passed${NC}"
else
    echo -e "${RED}✗ Linting failed${NC}"
    FAILED=1
fi
echo ""

# 2. Run tests
echo -e "${YELLOW}═══ Step 2: Running Tests ═══${NC}"
if ./venv/bin/python -m pytest tests/; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    FAILED=1
fi
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ All checks and tests passed! ✓✓✓${NC}"
    echo -e "${GREEN}Your code is ready to commit!${NC}"
    exit 0
else
    echo -e "${RED}✗✗✗ Some checks or tests failed ✗✗✗${NC}"
    echo -e "${RED}Please fix the issues before committing.${NC}"
    exit 1
fi
