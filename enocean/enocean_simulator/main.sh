#!/bin/bash

# EnOcean Simulator Management Script
# Usage: ./main.sh [start|stop|restart|status|loganalyze|clean|setup]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PID_FILE="$SCRIPT_DIR/.simulator.pid"
MAIN_PY="$SCRIPT_DIR/main.py"
LOG_ANALYZER="$SCRIPT_DIR/tools/log_analyzer.py"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
LOGS_DIR="$SCRIPT_DIR/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Check if Python 3.8+ is available
check_python() {
    # Try different Python commands
    for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
        if command -v "$cmd" &> /dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        log_error "Python is not installed or not in PATH"
        log_error "Tried: python3, python, python3.11, python3.10, python3.9, python3.8"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 8 ]; then
        log_error "Python 3.8+ is required. Found: $PYTHON_VERSION"
        exit 1
    fi

    log_debug "Using Python: $PYTHON_CMD ($PYTHON_VERSION)"
}

# Create virtual environment
create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"

        if [ $? -ne 0 ]; then
            log_error "Failed to create virtual environment"
            exit 1
        fi
    fi
}

# Activate virtual environment
activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        log_debug "Virtual environment activated"
    else
        log_error "Virtual environment not found. Run setup first."
        exit 1
    fi
}

# Install requirements
install_requirements() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        log_info "Installing requirements..."
        pip install -r "$REQUIREMENTS_FILE"

        if [ $? -ne 0 ]; then
            log_error "Failed to install requirements"
            exit 1
        fi
    else
        log_warn "requirements.txt not found. Skipping dependency installation."
    fi
}

# Check if simulator is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is not running
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Get simulator PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# Setup environment
setup_environment() {
    log_info "Setting up EnOcean Simulator environment..."

    check_python
    create_venv
    activate_venv
    install_requirements

    # Create logs directory if it doesn't exist
    mkdir -p "$LOGS_DIR"

    log_info "Environment setup complete!"
}

# Start the simulator in foreground (live output)
start_simulator_foreground() {
    if is_running; then
        PID=$(get_pid)
        log_warn "Simulator is already running in background (PID: $PID)"
        log_info "Stop it first with: ./main.sh stop"
        return 1
    fi

    log_info "Starting EnOcean Simulator in FOREGROUND mode..."
    log_info "You will see all output live. Press Ctrl+C to stop."
    echo "=========================================="

    # Check if main.py exists
    if [ ! -f "$MAIN_PY" ]; then
        log_error "main.py not found at $MAIN_PY"
        exit 1
    fi

    # Setup environment if needed
    if [ ! -d "$VENV_DIR" ]; then
        setup_environment
    else
        activate_venv
    fi

    # Ensure Python command is set
    if [ -z "$PYTHON_CMD" ]; then
        check_python
    fi

    # Start in foreground - all output will be visible
    "$PYTHON_CMD" "$MAIN_PY" "$@"

    echo "=========================================="
    log_info "Simulator stopped."
}

# Start the simulator in background
start_simulator_background() {
    if is_running; then
        PID=$(get_pid)
        log_warn "Simulator is already running (PID: $PID)"
        return 0
    fi

    log_info "Starting EnOcean Simulator..."

    # Check if main.py exists
    if [ ! -f "$MAIN_PY" ]; then
        log_error "main.py not found at $MAIN_PY"
        exit 1
    fi

    # Setup environment if needed
    if [ ! -d "$VENV_DIR" ]; then
        setup_environment
    else
        activate_venv
    fi

    # Ensure Python command is set
    if [ -z "$PYTHON_CMD" ]; then
        check_python
    fi

    log_debug "Python command: '$PYTHON_CMD'"
    log_debug "Main script: '$MAIN_PY'"
    log_debug "Arguments: $*"

    # Create logs directory if it doesn't exist
    mkdir -p "$LOGS_DIR"
    
    # Clear previous log file
    > "$LOGS_DIR/simulator_output.log"

    log_info "Starting simulator in background..."
    # Use unbuffered output to ensure logs are written immediately
    nohup "$PYTHON_CMD" -u "$MAIN_PY" "$@" > "$LOGS_DIR/simulator_output.log" 2>&1 &
    PID=$!

    # Save PID
    echo $PID > "$PID_FILE"

    # Wait a moment to check if it started successfully
    sleep 3

    if ps -p "$PID" > /dev/null 2>&1; then
        log_info "Simulator started successfully (PID: $PID)"
        log_info "Output logged to: $LOGS_DIR/simulator_output.log"

        # Show startup output and look for serial interface
        sleep 2  # Give it more time to generate output
        if [ -f "$LOGS_DIR/simulator_output.log" ]; then
            echo ""
            log_info "Startup output:"
            echo "=========================================="
            cat "$LOGS_DIR/simulator_output.log"
            echo "=========================================="
            
            # Extract and highlight serial interface
            SERIAL_INTERFACE=$(grep -o "/dev/ttys[0-9]*" "$LOGS_DIR/simulator_output.log" | head -1)
            if [ -n "$SERIAL_INTERFACE" ]; then
                echo ""
                log_info "Serial Interface Created: $SERIAL_INTERFACE"
                echo -e "${YELLOW}Copy this: $SERIAL_INTERFACE${NC}"
                echo ""
            fi
        fi
    else
        log_error "Failed to start simulator"

        # Show error output
        if [ -f "$LOGS_DIR/simulator_output.log" ]; then
            echo ""
            log_error "Error output:"
            cat "$LOGS_DIR/simulator_output.log" | sed 's/^/    /'
        fi

        rm -f "$PID_FILE"
        exit 1
    fi
}

# Stop the simulator
stop_simulator() {
    if ! is_running; then
        log_warn "Simulator is not running"
        return 0
    fi

    PID=$(get_pid)
    log_info "Stopping EnOcean Simulator (PID: $PID)..."

    # Try graceful shutdown first
    kill -TERM "$PID" 2>/dev/null

    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            log_info "Simulator stopped gracefully"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done

    # Force kill if still running
    log_warn "Graceful shutdown failed, forcing termination..."
    kill -KILL "$PID" 2>/dev/null

    # Wait for force kill
    for i in {1..5}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            log_info "Simulator terminated"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done

    log_error "Failed to stop simulator"
    exit 1
}

# Restart the simulator
restart_simulator() {
    log_info "Restarting EnOcean Simulator..."
    stop_simulator
    sleep 2
    start_simulator_background "$@"
}

# Show simulator status
show_status() {
    if is_running; then
        PID=$(get_pid)
        log_info "Simulator is running (PID: $PID)"

        # Show some process info
        if command -v ps &> /dev/null; then
            echo "Process info:"
            ps -p "$PID" -o pid,ppid,etime,cmd 2>/dev/null || true
        fi
        
        # Show serial interface if available in logs
        if [ -f "$LOGS_DIR/simulator_output.log" ]; then
            SERIAL_INTERFACE=$(grep -o "/dev/ttys[0-9]*" "$LOGS_DIR/simulator_output.log" | head -1)
            if [ -n "$SERIAL_INTERFACE" ]; then
                echo ""
                log_info "Serial Interface: $SERIAL_INTERFACE"
            fi
        fi
    else
        log_info "Simulator is not running"
    fi
}

# Run log analyzer
run_log_analyzer() {
    log_info "Starting log analyzer..."

    # Check if log analyzer exists
    if [ ! -f "$LOG_ANALYZER" ]; then
        log_error "Log analyzer not found at $LOG_ANALYZER"
        exit 1
    fi

    # Setup environment if needed
    if [ ! -d "$VENV_DIR" ]; then
        setup_environment
    else
        activate_venv
    fi

    # Ensure Python command is set
    if [ -z "$PYTHON_CMD" ]; then
        check_python
    fi

    log_debug "Using Python: $PYTHON_CMD"
    log_debug "Log analyzer: $LOG_ANALYZER"

    "$PYTHON_CMD" "$LOG_ANALYZER" "$@"
}

# Clean environment
clean_environment() {
    log_info "Cleaning environment..."

    # Stop simulator if running
    if is_running; then
        log_info "Stopping simulator before cleaning..."
        stop_simulator
    fi

    # Remove virtual environment
    if [ -d "$VENV_DIR" ]; then
        log_info "Removing virtual environment..."
        rm -rf "$VENV_DIR"
    fi

    # Clean log files
    if [ -d "$LOGS_DIR" ]; then
        log_info "Cleaning log files..."
        rm -f "$LOGS_DIR"/*.log
        rm -f "$LOGS_DIR"/*.csv
        rm -f "$LOGS_DIR"/*.json
    fi

    # Remove PID file
    rm -f "$PID_FILE"

    log_info "Environment cleaned!"
}

# Test environment
test_environment() {
    log_info "Testing environment setup..."

    check_python
    log_info "✓ Python check passed: $PYTHON_CMD"

    log_info "✓ Script directory: $SCRIPT_DIR"
    log_info "✓ Main script: $MAIN_PY"
    log_info "✓ Log analyzer: $LOG_ANALYZER"
    log_info "✓ Logs directory: $LOGS_DIR"

    if [ -f "$MAIN_PY" ]; then
        log_info "✓ main.py exists"
    else
        log_error "✗ main.py not found"
    fi

    if [ -f "$LOG_ANALYZER" ]; then
        log_info "✓ log_analyzer.py exists"
    else
        log_error "✗ log_analyzer.py not found"
    fi

    # Test Python execution
    log_info "Testing Python execution..."
    if "$PYTHON_CMD" --version > /dev/null 2>&1; then
        log_info "✓ Python execution test passed"
        "$PYTHON_CMD" --version
    else
        log_error "✗ Python execution test failed"
    fi

    # Test if we can import basic modules
    log_info "Testing Python imports..."
    if "$PYTHON_CMD" -c "import sys, json, pathlib; print('✓ Basic imports work')" 2>/dev/null; then
        log_info "✓ Python imports test passed"
    else
        log_error "✗ Python imports test failed"
    fi

    log_info "Environment test complete!"
}

debug_simulator() {
    log_info "Running simulator in debug mode..."

    # Check if main.py exists
    if [ ! -f "$MAIN_PY" ]; then
        log_error "main.py not found at $MAIN_PY"
        exit 1
    fi

    # Setup environment if needed
    if [ ! -d "$VENV_DIR" ]; then
        setup_environment
    else
        activate_venv
    fi

    log_info "Running in foreground with full output..."
    "$PYTHON_CMD" "$MAIN_PY" "$@"
}

# Validate configuration
validate_config() {
    log_info "Validating simulator configuration..."

    if [ ! -d "$VENV_DIR" ]; then
        setup_environment
    else
        activate_venv
    fi

    # Ensure Python command is set
    if [ -z "$PYTHON_CMD" ]; then
        check_python
    fi

    "$PYTHON_CMD" "$MAIN_PY" --verify-config
}

# Show live logs with proper tail functionality
tail_logs() {
    # Check if log file exists or if simulator is running
    if [ ! -f "$LOGS_DIR/simulator_output.log" ] && ! is_running; then
        log_warn "No log file found and simulator is not running"
        log_info "Start the simulator first with: ./main.sh start"
        return 1
    fi

    log_info "Following live simulator logs (Press Ctrl+C to exit)..."
    
    if [ -f "$LOGS_DIR/simulator_output.log" ]; then
        echo "File: $LOGS_DIR/simulator_output.log"
        echo "=========================================="
        
        # Use tail -F to follow the file even if it gets recreated
        tail -F "$LOGS_DIR/simulator_output.log" 2>/dev/null
    else
        log_info "Waiting for log file to be created..."
        
        # Wait for the log file to appear
        while [ ! -f "$LOGS_DIR/simulator_output.log" ] && is_running; do
            sleep 1
            echo -n "."
        done
        
        if [ -f "$LOGS_DIR/simulator_output.log" ]; then
            echo ""
            log_info "Log file created! Following logs..."
            echo "=========================================="
            tail -F "$LOGS_DIR/simulator_output.log" 2>/dev/null
        else
            echo ""
            log_warn "Log file was not created and simulator is not running"
        fi
    fi
}

# Show recent logs
show_logs() {
    if [ -f "$LOGS_DIR/simulator_output.log" ]; then
        log_info "Recent simulator output:"
        echo "=========================================="
        cat "$LOGS_DIR/simulator_output.log"
        echo "=========================================="
        
        # Extract and show serial interface
        SERIAL_INTERFACE=$(grep -o "/dev/ttys[0-9]*" "$LOGS_DIR/simulator_output.log" | head -1)
        if [ -n "$SERIAL_INTERFACE" ]; then
            echo ""
            log_info "Serial Interface: $SERIAL_INTERFACE"
            echo -e "${YELLOW}Copy this: $SERIAL_INTERFACE${NC}"
        fi
        
        echo ""
        log_info "For live logs use: ./main.sh tail"
    else
        log_warn "No simulator output log found at: $LOGS_DIR/simulator_output.log"
        
        if is_running; then
            log_info "Simulator is running but no log file yet. Try again in a moment."
        else
            log_info "Simulator is not running. Start it with: ./main.sh start"
        fi
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start       Start the EnOcean Simulator in background"
    echo "  run         Start the EnOcean Simulator in foreground"
    echo "  stop        Stop the EnOcean Simulator"
    echo "  restart     Restart the EnOcean Simulator"
    echo "  status      Show simulator status and serial interface"
    echo "  debug       Run simulator in foreground with full output"
    echo "  validate    Validate configuration without starting"
    echo "  logs        Show all simulator logs and serial interface"
    echo "  tail        Show live simulator logs (real-time)"
    echo "  loganalyze  Run log analyzer"
    echo "  clean       Clean virtual environment and logs"
    echo "  setup       Setup environment (create venv, install deps)"
    echo "  test        Test environment setup and Python detection"
    echo ""
    echo "Examples:"
    echo "  $0 start                                  # Start in background"
    echo "  $0 run                                    # Start in foreground"
    echo "  $0 logs                                   # Show logs and serial interface"
    echo "  $0 tail                                   # Follow live logs"
    echo "  $0 status                                 # Show status and serial interface"
    echo "  $0 debug --list-devices                   # Debug mode with options"
    echo "  $0 loganalyze --report                    # Analyze logs"
    echo ""
}

# Main script logic
main() {
    case "${1:-}" in
        start)
            shift
            start_simulator_background "$@"
            ;;
        run)
            shift
            start_simulator_foreground "$@"
            ;;
        stop)
            stop_simulator
            ;;
        restart)
            shift
            restart_simulator "$@"
            ;;
        status)
            show_status
            ;;
        loganalyze)
            shift
            run_log_analyzer "$@"
            ;;
        clean)
            clean_environment
            ;;
        setup)
            setup_environment
            ;;
        tail)
            tail_logs
            ;;
        test)
            test_environment
            ;;
        debug)
            shift
            debug_simulator "$@"
            ;;
        validate)
            validate_config
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h)
            show_usage
            ;;
        "")
            log_error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"