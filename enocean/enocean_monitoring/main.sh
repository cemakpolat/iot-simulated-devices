#!/bin/bash

set -e

# ────────────────────────────────────────────────────────────────
# EnOcean Gateway Management Script
# Supports Docker services + Python gateway
# ────────────────────────────────────────────────────────────────

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PID_FILE="$SCRIPT_DIR/.gateway.pid"
MAIN_PY="$SCRIPT_DIR/enocean_gateway/main.py"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
LOGS_DIR="$SCRIPT_DIR/logs"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE_FILE="$SCRIPT_DIR/.env.example"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_header() {
    echo ""
    echo "=============================================="
    echo "🏠 EnOcean Gateway Management"
    echo "=============================================="
    echo ""
}

# Check if Python 3.8+ is available
check_python() {
    for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
        if command -v "$cmd" &> /dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        log_error "Python is not installed or not in PATH"
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

# Check Docker
check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    if ! docker info &>/dev/null; then
        log_error "Docker is not running"
        exit 1
    fi
    if ! command -v docker-compose &>/dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
}

# Setup environment file
setup_env() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE_FILE" ]; then
            log_info "Copying .env.example to .env..."
            cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
            log_info "✅ .env file created from .env.example"
            log_warn "Please review and update .env file with your settings"
        else
            log_error ".env file not found and no .env.example to copy from"
            log_error "Please create .env file with required configuration"
            exit 1
        fi
    else
        log_debug ".env file already exists"
    fi
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
        log_error "Virtual environment not found"
        exit 1
    fi
}

# Install requirements
install_requirements() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        log_info "Installing Python requirements..."
        pip install --upgrade pip
        pip install -r "$REQUIREMENTS_FILE"
        if [ $? -ne 0 ]; then
            log_error "Failed to install requirements"
            exit 1
        fi
    else
        log_warn "requirements.txt not found. Skipping dependency installation."
    fi
}

# Check if gateway is running
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

# Get gateway PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# Start Docker services
start_docker_services() {
    log_info "Starting Docker services..."
    
    # Start the monitoring stack
    docker-compose up -d emqx influxdb grafana telegraf
    
    # Wait for services to be ready
    sleep 5
    
    log_info "✅ Docker services started"
    log_info "Access URLs:"
    log_info "  EMQX:     http://localhost:18083"
    log_info "  Grafana:  http://localhost:3000"
    log_info "  InfluxDB: http://localhost:8086"
}

# Stop Docker services
stop_docker_services() {
    log_info "Stopping Docker services..."
    docker-compose down
    log_info "✅ Docker services stopped"
}

# Start Python gateway
start_python_gateway() {
    if is_running; then
        PID=$(get_pid)
        log_warn "Gateway is already running (PID: $PID)"
        return 0
    fi

    # Check if enocean_gateway directory exists
    if [ ! -d "$SCRIPT_DIR/enocean_gateway" ]; then
        log_error "enocean_gateway directory not found at $SCRIPT_DIR/enocean_gateway"
        exit 1
    fi

    # Check if main.py exists in enocean_gateway
    if [ ! -f "$MAIN_PY" ]; then
        log_error "main.py not found at $MAIN_PY"
        exit 1
    fi

    # Setup Python environment
    check_python
    create_venv
    activate_venv
    install_requirements

    # Create logs directory
    mkdir -p "$LOGS_DIR"
    
    # Clear previous log file
    > "$LOGS_DIR/gateway_output.log"

    log_info "Starting Python EnOcean Gateway..."
    
    # Start gateway in background with unbuffered output using module execution
    # This ensures proper Python path and module resolution
    nohup "$PYTHON_CMD" -u -m enocean_gateway.main > "$LOGS_DIR/gateway_output.log" 2>&1 &
    PID=$!

    # Save PID
    echo $PID > "$PID_FILE"

    # Wait and check if it started successfully
    sleep 3

    if ps -p "$PID" > /dev/null 2>&1; then
        log_info "✅ Python Gateway started successfully (PID: $PID)"
        log_info "Output logged to: $LOGS_DIR/gateway_output.log"

        # Show startup output and extract serial interface
        sleep 2
        if [ -f "$LOGS_DIR/gateway_output.log" ]; then
            echo ""
            log_info "Gateway startup output:"
            echo "=========================================="
            cat "$LOGS_DIR/gateway_output.log"
            echo "=========================================="
            
            # Extract and highlight serial interface
            SERIAL_INTERFACE=$(grep -o "/dev/ttys[0-9]*\|/dev/ttyUSB[0-9]*\|/dev/cu\.[^[:space:]]*" "$LOGS_DIR/gateway_output.log" | head -1)
            if [ -n "$SERIAL_INTERFACE" ]; then
                echo ""
                log_info "Serial Interface: $SERIAL_INTERFACE"
                echo -e "${YELLOW}Device: $SERIAL_INTERFACE${NC}"
                echo ""
            fi
        fi
    else
        log_error "Failed to start Python gateway"
        
        # Show error output
        if [ -f "$LOGS_DIR/gateway_output.log" ]; then
            echo ""
            log_error "Error output:"
            cat "$LOGS_DIR/gateway_output.log" | sed 's/^/    /'
        fi
        
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Stop Python gateway
stop_python_gateway() {
    if ! is_running; then
        log_info "Gateway is not running"
        return 0
    fi

    PID=$(get_pid)
    log_info "Stopping Python Gateway (PID: $PID)..."

    # Try graceful shutdown first
    kill -TERM "$PID" 2>/dev/null

    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            log_info "✅ Gateway stopped gracefully"
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
            log_info "✅ Gateway terminated"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done

    log_error "Failed to stop gateway"
    exit 1
}

start_docker_services(){
    # Check Docker
    check_docker   
    # Start Docker services first
    start_docker_services
}

# Start all services
start_services() {
    print_header
    
    # Setup environment
    setup_env
    
    # Check Docker
    #check_docker
    
    # Start Docker services first
    #start_docker_services
    
    # Start Python gateway
    start_python_gateway
    
    log_info "🎉 All services started successfully!"
    echo ""
}

# Stop all services
stop_services() {
    print_header
    
    log_info "Stopping all services..."
    
    # Stop Python gateway first
    stop_python_gateway
    
    # Stop Docker services
    stop_docker_services
    
    log_info "🛑 All services stopped"
    echo ""
}

# Restart all services
restart_services() {
    print_header
    
    log_info "Restarting all services..."
    stop_services
    sleep 2
    start_services
}

# Show status
show_status() {
    print_header
    
    log_info "Service Status:"
    echo ""
    
    # Docker services status
    echo "Docker Services:"
    docker-compose ps
    echo ""
    
    # Python gateway status
    if is_running; then
        PID=$(get_pid)
        log_info "✅ Python Gateway is running (PID: $PID)"
        
        # Show process info
        if command -v ps &> /dev/null; then
            echo "Process info:"
            ps -p "$PID" -o pid,ppid,etime,cmd 2>/dev/null || true
        fi
        
        # Show serial interface if available in logs
        if [ -f "$LOGS_DIR/gateway_output.log" ]; then
            SERIAL_INTERFACE=$(grep -o "/dev/ttys[0-9]*\|/dev/ttyUSB[0-9]*\|/dev/cu\.[^[:space:]]*" "$LOGS_DIR/gateway_output.log" | head -1)
            if [ -n "$SERIAL_INTERFACE" ]; then
                echo ""
                log_info "Serial Interface: $SERIAL_INTERFACE"
            fi
        fi
    else
        log_warn "❌ Python Gateway is not running"
    fi
    echo ""
}

# Show logs
show_logs() {
    SERVICE=${1:-"gateway"}
    
    case "$SERVICE" in
        gateway|python)
            if [ -f "$LOGS_DIR/gateway_output.log" ]; then
                log_info "Python Gateway logs:"
                echo "=========================================="
                cat "$LOGS_DIR/gateway_output.log"
                echo "=========================================="
                
                # Extract and show serial interface
                SERIAL_INTERFACE=$(grep -o "/dev/ttys[0-9]*\|/dev/ttyUSB[0-9]*\|/dev/cu\.[^[:space:]]*" "$LOGS_DIR/gateway_output.log" | head -1)
                if [ -n "$SERIAL_INTERFACE" ]; then
                    echo ""
                    log_info "Serial Interface: $SERIAL_INTERFACE"
                fi
            else
                log_warn "No gateway logs found"
            fi
            ;;
        docker|emqx|influxdb|grafana|telegraf)
            log_info "Docker service logs for: $SERVICE"
            docker-compose logs "$SERVICE"
            ;;
        *)
            log_info "Available log targets: gateway, docker, emqx, influxdb, grafana, telegraf"
            ;;
    esac
}

# Tail logs
tail_logs() {
    SERVICE=${1:-"gateway"}
    
    case "$SERVICE" in
        gateway|python)
            if [ -f "$LOGS_DIR/gateway_output.log" ]; then
                log_info "Following Python Gateway logs (Press Ctrl+C to exit)..."
                echo "File: $LOGS_DIR/gateway_output.log"
                echo "=========================================="
                tail -F "$LOGS_DIR/gateway_output.log" 2>/dev/null
            else
                log_warn "No gateway logs found. Starting gateway first..."
                if is_running; then
                    log_info "Gateway is running, waiting for logs..."
                    while [ ! -f "$LOGS_DIR/gateway_output.log" ]; do
                        sleep 1
                        echo -n "."
                    done
                    echo ""
                    tail -F "$LOGS_DIR/gateway_output.log" 2>/dev/null
                else
                    log_info "Gateway is not running. Start it with: ./main.sh start"
                fi
            fi
            ;;
        docker|emqx|influxdb|grafana|telegraf)
            log_info "Following Docker service logs for: $SERVICE"
            docker-compose logs -f "$SERVICE"
            ;;
        *)
            log_info "Available log targets: gateway, docker, emqx, influxdb, grafana, telegraf"
            ;;
    esac
}

# Show usage
show_usage() {
    print_header
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start       Start all services (Docker + Python Gateway)"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  status      Show status of all services"
    echo "  logs [svc]  Show logs (gateway, emqx, influxdb, grafana, telegraf)"
    echo "  tail [svc]  Follow live logs"
    echo "  help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start everything"
    echo "  $0 status                   # Check status"
    echo "  $0 logs gateway             # Show gateway logs"
    echo "  $0 tail emqx                # Follow EMQX logs"
    echo "  $0 stop                     # Stop everything"
    echo ""
}

# Main script logic
main() {
    case "${1:-help}" in
        start)
            start_services
            ;;
        start_dockers)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            shift
            show_logs "$1"
            ;;
        tail)
            shift
            tail_logs "$1"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            if [ -n "$1" ]; then
                log_error "Unknown command: $1"
            fi
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"