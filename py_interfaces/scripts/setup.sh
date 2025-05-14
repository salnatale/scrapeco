#!/bin/bash
# Setup script for the LinkedIn Data API

# Move to parent directory
cd "$(dirname "$0")/.."
SCRIPT_DIR="$(pwd)"
echo "Running setup from: $SCRIPT_DIR"

# Check for Python 3
if command -v python3 &> /dev/null
then
    PYTHON_CMD="python3"
    echo "Using python3 command"
elif command -v python &> /dev/null
then
    # Check if python is actually Python 3
    PYTHON_VERSION=$(python --version 2>&1)
    if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
        PYTHON_CMD="python"
        echo "Using python command (detected as Python 3)"
    else
        echo "Error: Python 3 is required but could not be found"
        exit 1
    fi
else
    echo "Error: Neither python3 nor python commands are available"
    exit 1
fi

# Delete virtual environment if it's corrupted or if --force flag is provided
if [ "$1" == "--force" ] || [ -d "venv" ] && [ ! -f "venv/bin/activate" ] && [ ! -f "venv/Scripts/activate" ]; then
    echo "Removing corrupted or existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        echo "Trying alternative method..."
        
        # Try using virtualenv if venv failed
        if command -v pip3 &> /dev/null; then
            pip3 install virtualenv
            $PYTHON_CMD -m virtualenv venv
        elif command -v pip &> /dev/null; then
            pip install virtualenv
            $PYTHON_CMD -m virtualenv venv
        else
            echo "Error: Could not install virtualenv"
            exit 1
        fi
        
        if [ $? -ne 0 ]; then
            echo "Error: All virtual environment creation methods failed"
            exit 1
        fi
    fi
fi

# Verify venv directory exists
if [ ! -d "venv" ]; then
    echo "Error: venv directory was not created successfully"
    exit 1
fi

# Check for activation script
if [ ! -f "venv/bin/activate" ]; then
    if [ -f "venv/Scripts/activate" ]; then
        # Windows path
        ACTIVATE_SCRIPT="venv/Scripts/activate"
    else
        echo "Error: Could not find activation script in venv directory"
        echo "Contents of venv directory:"
        ls -la venv
        echo "Attempting to recreate virtual environment..."
        rm -rf venv
        $PYTHON_CMD -m venv venv
        
        if [ ! -f "venv/bin/activate" ] && [ ! -f "venv/Scripts/activate" ]; then
            echo "Virtual environment recreation failed. Please check your Python installation."
            exit 1
        else
            echo "Virtual environment recreated successfully."
            if [ -f "venv/bin/activate" ]; then
                ACTIVATE_SCRIPT="venv/bin/activate"
            else
                ACTIVATE_SCRIPT="venv/Scripts/activate"
            fi
        fi
    fi
else
    ACTIVATE_SCRIPT="venv/bin/activate"
fi

# Activate virtual environment
echo "Activating virtual environment using: $ACTIVATE_SCRIPT"
source "$ACTIVATE_SCRIPT"
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

# Verify we're in the virtual environment
echo "Python interpreter: $(which python)"

# Update pip
echo "Updating pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Generate mock data if requested
if [ "$1" == "--generate-data" ] || [ "$2" == "--generate-data" ]; then
    echo "Generating mock data..."
    python scripts/test_api.py --generate 100 --company-count 20 --skip-tests
fi

echo "Setup complete! You can now run the API with:"
echo "bash scripts/run_api.sh" 