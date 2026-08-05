#!/bin/bash
# AI Image-to-Bill Setup Script
# Run this script to set up the project

set -e

echo "========================================="
echo "  AI Image-to-Bill Module Setup"
echo "========================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
echo "[1/5] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "[2/5] Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "[3/5] Installing Python dependencies..."
pip install -r requirements.txt

# Create .env if not exists
echo "[4/5] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it and add your GEMINI_API_KEY."
else
    echo ".env already exists, skipping."
fi

# Create necessary directories
echo "[5/5] Creating directories..."
mkdir -p uploads outputs

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env and set your GEMINI_API_KEY"
echo "  2. Run: uvicorn app.main:app --reload"
echo "  3. Visit: http://localhost:8000/docs"
echo ""
