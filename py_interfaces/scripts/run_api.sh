#!/bin/bash
# Script to run the API server with optional flags

# Move to parent directory
cd "$(dirname "$0")/.."
SCRIPT_DIR="$(pwd)"
echo "Running API server from: $SCRIPT_DIR"

# Check for Python virtual environment
if [ -f "venv/bin/activate" ]; then
    ACTIVATE_SCRIPT="venv/bin/activate"
elif [ -f "venv/Scripts/activate" ]; then
    # Windows path
    ACTIVATE_SCRIPT="venv/Scripts/activate"
else
    echo "Error: Virtual environment activation script not found"
    echo "Did you run setup.sh first? Try: bash scripts/setup.sh"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment using: $ACTIVATE_SCRIPT"
source "$ACTIVATE_SCRIPT"
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

# Verify uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "Error: uvicorn not found. Installing now..."
    pip install uvicorn
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install uvicorn"
        exit 1
    fi
fi

# Run the API server
echo "Starting API server..."
echo "API will be available at http://localhost:8000"
echo "API documentation will be available at http://localhost:8000/docs"
uvicorn api:app --host 0.0.0.0 --port 8000 --reload "$@" 