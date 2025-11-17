#!/bin/bash

# Universal FPS Booster Launcher
# This script runs the FPS booster with proper permissions

echo "🚀 Universal FPS Booster Launcher 🚀"
echo "======================================"

# Check if running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS - requesting admin privileges..."
    sudo python3 universal_fps_booster.py
else
    echo "Running FPS booster..."
    python3 universal_fps_booster.py
fi

echo ""
echo "Press any key to exit..."
read -n 1