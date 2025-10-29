#!/bin/bash
# Auto-format code with black and isort

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SRC_DIR="src"
TESTS_DIR="tests"
ALL_DIRS="$SRC_DIR $TESTS_DIR"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Auto-formatting Python Code         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 1. isort - Sort imports
echo -e "${BLUE}► Running isort...${NC}"
./venv/bin/python -m isort $ALL_DIRS
echo -e "${GREEN}✓ Imports sorted${NC}"
echo ""

# 2. Black - Format code
echo -e "${BLUE}► Running black...${NC}"
./venv/bin/python -m black $ALL_DIRS
echo -e "${GREEN}✓ Code formatted${NC}"
echo ""

echo -e "${GREEN}✓ All formatting complete!${NC}"
