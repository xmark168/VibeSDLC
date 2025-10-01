#!/usr/bin/env bash

# Exit in case of error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="vibe-ai-agent-service"
CONTAINER_NAME="vibe-ai-agent-service"
PORT=8001
SERVICE_PATH="/home/xmark/Desktop/VibeSDLC/services/ai-agent-service"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if container is running
is_container_running() {
    docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to check if container exists (running or stopped)
container_exists() {
    docker ps -a --filter "name=${CONTAINER_NAME}" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to stop and remove container
cleanup_container() {
    if container_exists; then
        print_info "Stopping and removing existing container..."
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
    fi
}

# Function to build image
build_image() {
    print_info "Building AI Agent Service Docker image..."

    # Check if .env file exists
    if [ ! -f "${SERVICE_PATH}/.env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f "${SERVICE_PATH}/.env.example" ]; then
            cp "${SERVICE_PATH}/.env.example" "${SERVICE_PATH}/.env"
            print_warning "Please update ${SERVICE_PATH}/.env with your API keys"
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi

    docker build -t ${IMAGE_NAME} -f ${SERVICE_PATH}/Dockerfile ${SERVICE_PATH}

    if [ $? -eq 0 ]; then
        print_info "Build completed successfully!"
    else
        print_error "Build failed!"
        exit 1
    fi
}

# Function to run container
run_container() {
    print_info "Starting AI Agent Service container..."
    docker run -d \
        -p ${PORT}:8001 \
        --name ${CONTAINER_NAME} \
        --env-file ${SERVICE_PATH}/.env \
        --restart unless-stopped \
        ${IMAGE_NAME}

    if [ $? -eq 0 ]; then
        print_info "Container started successfully!"
        print_info "AI Agent Service is running at: http://localhost:${PORT}"
        print_info "API docs available at: http://localhost:${PORT}/docs"
    else
        print_error "Failed to start container!"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    print_info "Showing container logs (Ctrl+C to exit)..."
    docker logs -f ${CONTAINER_NAME}
}

# Function to show status
show_status() {
    if is_container_running; then
        print_info "AI Agent Service container is running"
        docker ps --filter "name=${CONTAINER_NAME}"
    else
        print_warning "AI Agent Service container is not running"
    fi
}

# Main script
case "${1:-run}" in
    build)
        build_image
        ;;

    run)
        cleanup_container
        build_image
        run_container
        ;;

    start)
        if is_container_running; then
            print_warning "Container is already running"
            show_status
        elif container_exists; then
            print_info "Starting existing container..."
            docker start ${CONTAINER_NAME}
            print_info "AI Agent Service is running at: http://localhost:${PORT}"
        else
            print_error "Container does not exist. Use 'run' command first."
            exit 1
        fi
        ;;

    stop)
        if is_container_running; then
            print_info "Stopping container..."
            docker stop ${CONTAINER_NAME}
            print_info "Container stopped"
        else
            print_warning "Container is not running"
        fi
        ;;

    restart)
        cleanup_container
        run_container
        ;;

    logs)
        if container_exists; then
            show_logs
        else
            print_error "Container does not exist"
            exit 1
        fi
        ;;

    status)
        show_status
        ;;

    clean)
        cleanup_container
        print_info "Removing Docker image..."
        docker rmi ${IMAGE_NAME} 2>/dev/null || true
        print_info "Cleanup completed"
        ;;

    shell)
        if is_container_running; then
            print_info "Opening shell in container..."
            docker exec -it ${CONTAINER_NAME} /bin/bash
        else
            print_error "Container is not running"
            exit 1
        fi
        ;;

    *)
        echo "Usage: $0 {build|run|start|stop|restart|logs|status|clean|shell}"
        echo ""
        echo "Commands:"
        echo "  build   - Build the Docker image only"
        echo "  run     - Build and run the container (default)"
        echo "  start   - Start existing container"
        echo "  stop    - Stop running container"
        echo "  restart - Restart container (rebuild)"
        echo "  logs    - Show container logs"
        echo "  status  - Show container status"
        echo "  clean   - Stop container and remove image"
        echo "  shell   - Open shell in running container"
        echo ""
        echo "Environment variables:"
        echo "  PORT - Host port (default: 8001)"
        exit 1
        ;;
esac
