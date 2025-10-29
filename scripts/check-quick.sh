#!/bin/bash
# Quick checks - fastest feedback loop for development

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Quick Code Checks${NC}"
echo ""

# Just the fastest checks
echo -e "${YELLOW}► Black format check...${NC}"
./venv/bin/python -m black --check $@ || (echo "Run: ./scripts/format.sh" && exit 1)

echo -e "${YELLOW}► Flake8 style check...${NC}"
./venv/bin/python -m flake8 $@

echo -e "${YELLOW}► Mypy type check...${NC}"
./venv/bin/python -m mypy $@

echo -e "${GREEN}✓ Quick checks passed!${NC}"
