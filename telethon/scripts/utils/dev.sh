#!/bin/bash

# Helper script for telethon development
# Usage: ./dev.sh [command]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TELETHON_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
PROJECT_ROOT="$( cd "$TELETHON_DIR/.." && pwd )"

cd "$TELETHON_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Commands
run_local() {
    log_info "Starting telethon locally (outside Docker)..."
    
    # Check if venv exists
    if [ ! -d "venv" ]; then
        log_warn "Virtual environment not found. Creating..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    log_info "Virtual environment activated"
    log_info "Starting run_system.py..."
    python run_system.py
}

run_api() {
    log_info "Starting only FastAPI server..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    python main.py
}

run_bot() {
    log_info "Starting only Telegram bot..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    python bot_standalone.py
}

rebuild_docker() {
    log_info "Rebuilding telethon Docker containers..."
    cd "$PROJECT_ROOT"
    docker compose -f docker-compose.override.yml build telethon telethon-bot
    log_info "Restarting containers..."
    docker compose -f docker-compose.override.yml up -d telethon telethon-bot
    log_info "Done! Use './scripts/utils/dev.sh logs' to view logs"
}

restart_docker() {
    log_info "Restarting telethon Docker containers..."
    cd "$PROJECT_ROOT"
    docker compose -f docker-compose.override.yml restart telethon telethon-bot
    log_info "Done!"
}

stop_docker() {
    log_info "Stopping telethon Docker containers..."
    cd "$PROJECT_ROOT"
    docker compose -f docker-compose.override.yml stop telethon telethon-bot
    log_info "Stopped!"
}

logs_docker() {
    log_info "Showing telethon logs (Ctrl+C to exit)..."
    # Используем прямой docker logs вместо docker compose для совместимости
    docker logs -f telethon 2>&1 &
    TELETHON_PID=$!
    docker logs -f telethon-bot 2>&1 &
    BOT_PID=$!
    
    # Ждем Ctrl+C
    trap "kill $TELETHON_PID $BOT_PID 2>/dev/null; exit" INT
    wait
}

shell_docker() {
    log_info "Opening shell in telethon container..."
    docker exec -it telethon /bin/bash
}

test() {
    log_info "Running tests..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    pytest tests/ -v
}

setup() {
    log_info "Setting up development environment..."
    
    # Create venv
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    log_info "Installing dependencies..."
    pip install -r requirements.txt
    
    # Create directories
    mkdir -p sessions data logs
    
    # Copy .env.example if .env doesn't exist
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        log_warn ".env not found, copying from .env.example"
        cp .env.example .env
        log_warn "⚠ Please edit .env and add your credentials!"
    fi
    
    log_info "Setup complete!"
    log_info "Next steps:"
    echo "  1. Edit .env file with your credentials"
    echo "  2. Run: ./dev.sh local"
}

show_help() {
    cat << EOF
${GREEN}Telethon Development Helper${NC}

Usage: ./dev.sh [command]

${YELLOW}Local Development (recommended):${NC}
  local       - Run telethon locally (API + Bot + Parser)
  api         - Run only FastAPI server (port 8010)
  bot         - Run only Telegram bot
  test        - Run tests
  setup       - Setup development environment

${YELLOW}Docker Development:${NC}
  rebuild     - Rebuild and restart Docker containers
  restart     - Restart Docker containers (no rebuild)
  stop        - Stop Docker containers
  logs        - Show Docker logs (live)
  shell       - Open bash shell in telethon container

${YELLOW}Examples:${NC}
  ./dev.sh setup      # First time setup
  ./dev.sh local      # Start developing locally
  ./dev.sh rebuild    # After changing Dockerfile
  ./dev.sh logs       # View container logs

EOF
}

# Main
case "${1:-help}" in
    local)
        run_local
        ;;
    api)
        run_api
        ;;
    bot)
        run_bot
        ;;
    rebuild)
        rebuild_docker
        ;;
    restart)
        restart_docker
        ;;
    stop)
        stop_docker
        ;;
    logs)
        logs_docker
        ;;
    shell)
        shell_docker
        ;;
    test)
        test
        ;;
    setup)
        setup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

