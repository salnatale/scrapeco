#!/bin/bash
# Master script to run the entire platform

echo "=== ScrapeCo Data Analytics Platform ==="
echo "Setting up and launching the platform..."

# Determine the OS
case "$(uname -s)" in
    Darwin*)    OS="Mac";;
    Linux*)     OS="Linux";;
    CYGWIN*)    OS="Windows";;
    MINGW*)     OS="Windows";;
    *)          OS="Unknown";;
esac

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Navigate to project root directory
PROJECT_ROOT="$(pwd)"
echo "Project root: $PROJECT_ROOT"

# Function to check if the backend is already running
check_backend() {
    if command_exists lsof; then
        if lsof -i:8000 > /dev/null; then
            echo "Backend is already running on port 8000"
            return 0
        fi
    elif command_exists netstat; then
        if netstat -atn | grep 8000 > /dev/null; then
            echo "Backend is already running on port 8000"
            return 0
        fi
    fi
    return 1
}

# Function to run backend
run_backend() {
    echo "=== Setting up and starting backend ==="
    cd "$PROJECT_ROOT/py_interfaces" || exit 1
    
    # Run setup if needed
    if [ ! -d "venv" ]; then
        echo "Setting up Python environment..."
        bash scripts/setup.sh --generate-data
    fi
    
    # Start the API server
    echo "Starting API server..."
    bash scripts/run_api.sh
}

# Function to run frontend
run_frontend() {
    echo "=== Setting up and starting frontend ==="
    cd "$PROJECT_ROOT/frontend/client" || exit 1
    
    # Check if node_modules exists, if not run npm install
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    
    # Start the frontend
    echo "Starting frontend server..."
    npm start
}

# Start backend and frontend based on OS
if check_backend; then
    echo "Backend already running, skipping backend start"
else
    if [ "$OS" = "Mac" ] && command_exists osascript; then
        # On Mac, use osascript to open a new terminal
        echo "Starting backend in a new terminal window..."
        osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_ROOT/py_interfaces' && bash scripts/setup.sh && bash scripts/run_api.sh\""
    elif [ "$OS" = "Linux" ] && command_exists gnome-terminal; then
        # On Linux with Gnome Terminal
        echo "Starting backend in a new terminal window..."
        gnome-terminal -- bash -c "cd '$PROJECT_ROOT/py_interfaces' && bash scripts/setup.sh && bash scripts/run_api.sh; exec bash"
    elif [ "$OS" = "Linux" ] && command_exists xterm; then
        # On Linux with xterm
        echo "Starting backend in a new terminal window..."
        xterm -e "cd '$PROJECT_ROOT/py_interfaces' && bash scripts/setup.sh && bash scripts/run_api.sh" &
    else
        # Fall back to running in the background
        echo "Starting backend in the background..."
        (cd "$PROJECT_ROOT/py_interfaces" && bash scripts/setup.sh && bash scripts/run_api.sh) &
        BACKEND_PID=$!
        echo "Backend started with PID: $BACKEND_PID"
        sleep 5  # Give the backend time to start
    fi
fi

# Wait a bit for the backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Start the frontend
if [ "$OS" = "Mac" ] && command_exists osascript; then
    # On Mac, use osascript to open a new terminal
    echo "Starting frontend in a new terminal window..."
    osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_ROOT/frontend/client' && npm install && npm start\""
elif [ "$OS" = "Linux" ] && command_exists gnome-terminal; then
    # On Linux with Gnome Terminal
    echo "Starting frontend in a new terminal window..."
    gnome-terminal -- bash -c "cd '$PROJECT_ROOT/frontend/client' && npm install && npm start; exec bash"
elif [ "$OS" = "Linux" ] && command_exists xterm; then
    # On Linux with xterm
    echo "Starting frontend in a new terminal window..."
    xterm -e "cd '$PROJECT_ROOT/frontend/client' && npm install && npm start" &
else
    # Give the user instructions
    echo ""
    echo "=== MANUAL STEP REQUIRED ==="
    echo "Please open a new terminal window and run:"
    echo "cd '$PROJECT_ROOT/frontend/client' && npm install && npm start"
    echo ""
fi

echo ""
echo "=== PLATFORM LAUNCH INITIATED ==="
echo "Backend API will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:3000"
echo "API documentation: http://localhost:8000/docs"
echo ""
echo "To stop the platform, press Ctrl+C in each terminal window" 