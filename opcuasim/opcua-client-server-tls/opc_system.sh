#!/bin/bash
# opc_system.sh - Industrial OPC UA System Management Script

set -e

SCRIPT_NAME=$(basename "$0")

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_dependencies() {
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("Docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("Docker Compose")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo "Please install the missing dependencies and try again."
        exit 1
    fi
}

generate_certificates() {
    print_info "Generating certificates..."
    if [ -f "./generate_certificates.sh" ]; then
        chmod +x ./generate_certificates.sh
        ./generate_certificates.sh
        print_success "Certificates generated successfully"
    else
        print_warning "generate_certificates.sh not found, skipping certificate generation"
    fi
}

setup_environment() {
    # Create directories if they don't exist
    mkdir -p certificates logs
    print_success "Created necessary directories"
    
    # Copy environment file if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            print_success "Environment file created from .env.example"
            print_warning "Please review and modify .env file as needed"
        else
            print_warning "No .env.example file found. Using default environment variables."
        fi
    else
        print_info ".env file already exists"
    fi
}

start_system() {
    print_info "Starting Industrial OPC UA System..."
    
    check_dependencies
    generate_certificates
    setup_environment
    
    # Build and start the services
    print_info "Building Docker images..."
    docker-compose build
    
    print_info "Starting OPC UA services in background..."
    docker-compose up -d
    
    # Wait for services to start
    print_info "Waiting for services to start..."
    sleep 10
    
    # Show status
    print_success "Services started successfully!"
    echo ""
    print_info "Service status:"
    docker-compose ps
    
    echo ""
    print_info "Use '$SCRIPT_NAME watch' to view logs"
    print_info "Use '$SCRIPT_NAME stop' to stop the system"
}

stop_system() {
    print_info "Stopping OPC UA System..."
    
    if docker-compose ps -q | grep -q .; then
        docker-compose down
        print_success "System stopped successfully"
    else
        print_warning "No running containers found"
    fi
}

watch_logs() {
    print_info "Watching container logs (Press Ctrl+C to exit)..."
    echo ""
    
    if docker-compose ps -q | grep -q .; then
        docker-compose logs -f
    else
        print_error "No running containers found. Start the system first with '$SCRIPT_NAME start'"
        exit 1
    fi
}

clean_system() {
    print_warning "This will remove all containers, volumes, and the .env file!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up system..."
        
        # Stop and remove containers, networks, volumes
        if docker-compose ps -a -q | grep -q .; then
            docker-compose down -v --remove-orphans
            print_success "Containers and volumes removed"
        fi
        
        # Remove unused Docker resources
        docker system prune -f > /dev/null 2>&1 || true
        
        # Remove .env file
        if [ -f .env ]; then
            rm .env
            print_success ".env file removed"
        fi
        
        # Remove generated certificates if they exist
        if [ -d certificates ]; then
            rm -rf certificates
            print_success "Certificates directory removed"
        fi
        
        # Remove logs directory
        if [ -d logs ]; then
            rm -rf logs
            print_success "Logs directory removed"
        fi
        
        print_success "System cleaned successfully"
    else
        print_info "Clean operation cancelled"
    fi
}

show_help() {
    echo "Industrial OPC UA System Management Script"
    echo ""
    echo "Usage: $SCRIPT_NAME [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start    Generate certificates, setup environment, and start system in background"
    echo "  stop     Stop all running containers"
    echo "  watch    Watch container logs in real-time"
    echo "  clean    Remove all containers, volumes, certificates, logs, and .env file"
    echo "  show     Show this help message"
    echo "  help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME start    # Start the complete system"
    echo "  $SCRIPT_NAME watch    # Monitor system logs"
    echo "  $SCRIPT_NAME stop     # Stop the system"
    echo "  $SCRIPT_NAME clean    # Clean everything"
    echo ""
    echo "The start command will:"
    echo "  1. Check Docker dependencies"
    echo "  2. Run generate_certificates.sh (if available)"
    echo "  3. Copy .env.example to .env (if .env doesn't exist)"
    echo "  4. Build and start Docker containers in background"
    echo ""
    echo "After starting, you can:"
    echo "  - Use 'watch' to monitor logs"
    echo "  - Use 'stop' to stop services"
    echo "  - Use 'clean' to remove everything and start fresh"
}

# Main script logic
case "${1:-help}" in
    start)
        start_system
        ;;
    stop)
        stop_system
        ;;
    watch)
        watch_logs
        ;;
    clean)
        clean_system
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac