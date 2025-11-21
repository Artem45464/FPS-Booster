#!/bin/bash

# Universal FPS Booster Launcher v2.5
# Cross-platform script with improved error handling

set -e  # Exit on error

# Colors (if supported)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' BOLD='' RESET=''
fi

clear
echo -e "${BLUE}${BOLD}🚀 Universal FPS Booster v2.5 🚀${RESET}"
echo "======================================"
echo

# Check if script exists
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Error: main.py not found in current directory${RESET}"
    echo "Please run this script from the same folder as main.py"
    exit 1
fi

# Check platform
OS_TYPE=$(uname -s)
echo -e "${BOLD}Platform:${RESET} $OS_TYPE"

# Check if running as root/admin
if [ "$EUID" -eq 0 ]; then
    echo -e "${GREEN}✅ Running with admin privileges${RESET}"
else
    echo -e "${YELLOW}⚠️  NOT running as admin${RESET}"
    echo "   For best results: sudo ./run_fps_booster.sh"
    echo
    read -p "   Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Cancelled by user${RESET}"
        exit 0
    fi
fi

echo
echo -e "${BOLD}Detecting Python...${RESET}"

# Find Python with version check
PYTHON_CMD=""
MIN_VERSION="3.8"

for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        echo "  Found: $cmd (v$VERSION)"
        
        # Simple version check (comparing major.minor)
        if [ "$(printf '%s\n' "$MIN_VERSION" "$VERSION" | sort -V | head -n1)" = "$MIN_VERSION" ]; then
            PYTHON_CMD=$cmd
            echo -e "${GREEN}  ✓ Using: $cmd${RESET}"
            break
        else
            echo -e "${YELLOW}  ⚠️  Version too old (need $MIN_VERSION+)${RESET}"
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo
    echo -e "${RED}❌ No suitable Python found!${RESET}"
    echo
    echo "Please install Python $MIN_VERSION or higher:"
    case "$OS_TYPE" in
        Darwin*)
            echo "  • brew install python3"
            ;;
        Linux*)
            echo "  • Ubuntu/Debian: sudo apt install python3"
            echo "  • RHEL/CentOS: sudo yum install python3"
            ;;
    esac
    echo "  • Or download from: https://www.python.org/downloads/"
    echo
    exit 1
fi

# Check for psutil
echo
echo -e "${BOLD}Checking dependencies...${RESET}"
if ! $PYTHON_CMD -c "import psutil" 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  psutil not found (will be auto-installed)${RESET}"
else
    echo -e "${GREEN}  ✓ psutil is installed${RESET}"
fi

# Final confirmation
echo
echo -e "${BOLD}======================================"
echo "Ready to optimize!"
echo "======================================${RESET}"
echo
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Run script with error handling
echo
echo -e "${BOLD}Starting FPS optimization...${RESET}"
echo

set +e  # Don't exit on error from Python script
$PYTHON_CMD main.py 2>&1 | tee fps_booster.log
exit_code=$?
set -e

# Show results
echo
echo "======================================"
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ Optimization completed successfully!${RESET}"
    echo
    echo "Your system is now optimized for gaming!"
elif [ $exit_code -eq 130 ]; then
    echo -e "${YELLOW}⚠️  Cancelled by user (Ctrl+C)${RESET}"
else
    echo -e "${RED}❌ Optimization failed (exit code: $exit_code)${RESET}"
    echo
    echo "Check fps_booster.log for details"
    echo
    echo "Common issues:"
    echo "  • Missing admin privileges"
    echo "  • Python dependencies"
    echo "  • Unsupported OS/configuration"
fi
echo "======================================"
echo
echo "Press any key to exit..."
read -n 1 -s
