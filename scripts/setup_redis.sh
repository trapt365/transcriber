#!/bin/bash

# Redis Setup Script for KazRu-STT Pro
# Intelligent Redis installation with environment detection and fallback strategies
# Version: 1.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_PORT=6379
REDIS_HOST="127.0.0.1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Utility functions
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

redis_running() {
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1
}

wait_for_redis() {
    local attempts=0
    local max_attempts=30
    
    log_info "Waiting for Redis to start..."
    while [ $attempts -lt $max_attempts ]; do
        if redis_running; then
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    return 1
}

# Environment detection
detect_environment() {
    if [ -f /.dockerenv ] || [ -n "$REMOTE_CONTAINERS_IPC" ] || [ -n "$CODESPACES" ]; then
        echo "container"
    elif command_exists systemctl && systemctl is-system-running >/dev/null 2>&1; then
        echo "systemd"
    elif command_exists brew && [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "basic"
    fi
}

# Redis installation strategies
install_redis_systemd() {
    log_info "Installing Redis via system package manager (systemd environment)"
    
    if command_exists apt-get; then
        sudo apt update
        sudo apt install -y redis-server
    elif command_exists yum; then
        sudo yum install -y redis
    elif command_exists dnf; then
        sudo dnf install -y redis
    else
        log_error "Unsupported package manager for systemd environment"
        return 1
    fi
    
    # Start and enable Redis service
    sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis
    sudo systemctl enable redis-server 2>/dev/null || sudo systemctl enable redis
    
    log_success "Redis installed and started via systemd"
    return 0
}

install_redis_container() {
    log_info "Setting up Redis for container environment"
    
    # Option 1: Try Docker if available
    if command_exists docker; then
        log_info "Docker detected - starting Redis container"
        
        # Stop existing Redis container if running
        docker stop redis-transcriber 2>/dev/null || true
        docker rm redis-transcriber 2>/dev/null || true
        
        # Start new Redis container
        if docker run -d \
            --name redis-transcriber \
            --network host \
            -p $REDIS_PORT:6379 \
            redis:7-alpine; then
            
            log_success "Redis container started successfully"
            return 0
        else
            log_warning "Docker Redis setup failed, trying direct execution"
        fi
    fi
    
    # Option 2: Try direct Redis execution
    if command_exists redis-server; then
        log_info "Starting Redis directly"
        redis-server --daemonize yes --port $REDIS_PORT --bind $REDIS_HOST
        
        if wait_for_redis; then
            log_success "Redis started directly"
            return 0
        else
            log_warning "Direct Redis start failed"
        fi
    fi
    
    # Option 3: Install Redis if possible
    if command_exists apt-get && [ -w /var/lib/apt/lists ]; then
        log_info "Attempting Redis installation in container"
        apt update && apt install -y redis-server
        redis-server --daemonize yes --port $REDIS_PORT --bind $REDIS_HOST
        
        if wait_for_redis; then
            log_success "Redis installed and started in container"
            return 0
        fi
    fi
    
    # Option 4: Fall back to FakeRedis
    log_warning "Redis installation failed - setting up FakeRedis fallback"
    setup_fakeredis_fallback
    return 0
}

install_redis_macos() {
    log_info "Installing Redis on macOS via Homebrew"
    
    if ! command_exists brew; then
        log_error "Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        return 1
    fi
    
    # Install Redis
    brew install redis
    
    # Start Redis service
    brew services start redis
    
    log_success "Redis installed and started via Homebrew"
    return 0
}

install_redis_windows() {
    log_info "Setting up Redis for Windows environment"
    
    if command_exists docker; then
        log_info "Using Docker for Redis on Windows"
        
        # Start Redis container
        docker run -d \
            --name redis-transcriber \
            -p $REDIS_PORT:6379 \
            redis:7-alpine
            
        log_success "Redis container started on Windows"
        return 0
    else
        log_warning "Docker not available on Windows"
        log_info "Please install Docker Desktop or use WSL2 with Linux Redis"
        
        # Fall back to FakeRedis
        setup_fakeredis_fallback
        return 0
    fi
}

install_redis_basic() {
    log_info "Setting up Redis for basic environment"
    
    # Try direct execution if Redis is installed
    if command_exists redis-server; then
        log_info "Starting Redis directly"
        redis-server --daemonize yes --port $REDIS_PORT --bind $REDIS_HOST
        
        if wait_for_redis; then
            log_success "Redis started directly"
            return 0
        fi
    fi
    
    # Try package installation if possible
    if command_exists apt-get; then
        log_info "Attempting Redis installation"
        if sudo apt update && sudo apt install -y redis-server; then
            # Try service start (may not work without systemd)
            service redis-server start 2>/dev/null || \
            redis-server --daemonize yes --port $REDIS_PORT --bind $REDIS_HOST
            
            if wait_for_redis; then
                log_success "Redis installed and started"
                return 0
            fi
        fi
    fi
    
    # Fall back to FakeRedis
    log_warning "Redis installation not possible - setting up FakeRedis fallback"
    setup_fakeredis_fallback
    return 0
}

# Fallback setup
setup_fakeredis_fallback() {
    log_info "Setting up FakeRedis development fallback"
    
    # Install fakeredis via pip
    if command_exists pip; then
        pip install fakeredis
    elif command_exists pip3; then
        pip3 install fakeredis
    else
        log_error "pip not found - cannot install fakeredis"
        return 1
    fi
    
    # Update .env file
    update_env_file "USE_FAKE_REDIS" "true"
    update_env_file "DEVELOPMENT_MODE" "true"
    
    log_success "FakeRedis fallback configured"
    log_warning "Note: FakeRedis is suitable for development only - data will not persist"
    
    return 0
}

# Configuration management
update_env_file() {
    local key="$1"
    local value="$2"
    
    if [ -f "$ENV_FILE" ]; then
        # Update existing entry or add new one
        if grep -q "^${key}=" "$ENV_FILE"; then
            # Update existing
            sed -i "s/^${key}=.*/${key}=${value}/" "$ENV_FILE"
        else
            # Add new
            echo "${key}=${value}" >> "$ENV_FILE"
        fi
    else
        # Create new .env file
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
    
    log_info "Updated ${ENV_FILE}: ${key}=${value}"
}

# Validation functions
validate_redis_connection() {
    log_info "Validating Redis connection..."
    
    if redis_running; then
        local redis_version
        redis_version=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server | grep redis_version | cut -d: -f2 | tr -d '\r')
        log_success "Redis connection successful - Version: $redis_version"
        
        # Test basic operations
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" set test_key "test_value" >/dev/null && \
           redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" get test_key >/dev/null && \
           redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" del test_key >/dev/null; then
            log_success "Redis basic operations test passed"
        else
            log_warning "Redis basic operations test failed"
        fi
        
        return 0
    else
        log_error "Redis connection validation failed"
        return 1
    fi
}

validate_fallback_setup() {
    log_info "Validating FakeRedis fallback setup..."
    
    if python3 -c "import fakeredis; print('FakeRedis import successful')" 2>/dev/null || \
       python -c "import fakeredis; print('FakeRedis import successful')" 2>/dev/null; then
        log_success "FakeRedis fallback validation successful"
        return 0
    else
        log_error "FakeRedis validation failed"
        return 1
    fi
}

# Main installation logic
main() {
    echo "🔍 KazRu-STT Pro Redis Setup Script"
    echo "=================================="
    
    # Check if Redis is already running
    if redis_running; then
        log_success "Redis is already running on ${REDIS_HOST}:${REDIS_PORT}"
        validate_redis_connection
        exit 0
    fi
    
    # Detect environment
    local environment
    environment=$(detect_environment)
    log_info "Detected environment: $environment"
    
    # Install based on environment
    case $environment in
        "systemd")
            install_redis_systemd
            ;;
        "container")
            install_redis_container
            ;;
        "macos")
            install_redis_macos
            ;;
        "windows")
            install_redis_windows
            ;;
        "basic")
            install_redis_basic
            ;;
        *)
            log_error "Unknown environment: $environment"
            exit 1
            ;;
    esac
    
    # Wait for Redis to start
    if wait_for_redis; then
        validate_redis_connection
    else
        # Check if we're using FakeRedis fallback
        if grep -q "USE_FAKE_REDIS=true" "$ENV_FILE" 2>/dev/null; then
            validate_fallback_setup
            log_info "Application will use FakeRedis when started"
        else
            log_error "Redis setup failed and no fallback configured"
            log_info "You can manually enable FakeRedis fallback with:"
            echo "  echo 'USE_FAKE_REDIS=true' >> .env"
            echo "  echo 'DEVELOPMENT_MODE=true' >> .env"
            echo "  pip install fakeredis"
            exit 1
        fi
    fi
    
    # Final summary
    echo ""
    echo "🎉 Redis Setup Complete!"
    echo "======================="
    
    if redis_running; then
        echo "✅ Redis server is running on ${REDIS_HOST}:${REDIS_PORT}"
        echo "🔗 Connection URL: redis://${REDIS_HOST}:${REDIS_PORT}/0"
    else
        echo "✅ FakeRedis fallback is configured"
        echo "⚠️  Development mode only - data will not persist between restarts"
    fi
    
    echo ""
    echo "Next steps:"
    echo "1. Continue with the application setup"
    echo "2. Run: python -m flask run --debug"
    echo "3. Check Redis status: curl http://localhost:5000/api/v1/health/redis"
    echo ""
    echo "For troubleshooting, see: docs/REDIS_SETUP.md"
}

# Handle script arguments
case "${1:-}" in
    "--help"|"-h")
        echo "Redis Setup Script for KazRu-STT Pro"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  -h, --help     Show this help message"
        echo "  --validate     Only validate existing Redis setup"
        echo "  --fallback     Force FakeRedis fallback setup"
        echo ""
        echo "The script automatically detects your environment and installs Redis"
        echo "using the most appropriate method for your system."
        exit 0
        ;;
    "--validate")
        if redis_running; then
            validate_redis_connection
        elif grep -q "USE_FAKE_REDIS=true" "$ENV_FILE" 2>/dev/null; then
            validate_fallback_setup
        else
            log_error "No Redis setup found"
            exit 1
        fi
        exit 0
        ;;
    "--fallback")
        setup_fakeredis_fallback
        exit 0
        ;;
esac

# Run main installation
main "$@"