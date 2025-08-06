# Redis Setup Guide for KazRu-STT Pro

This comprehensive guide covers Redis installation and configuration across all supported environments for native installation of KazRu-STT Pro.

## Quick Start (Recommended)

For most users, our automated setup script handles environment detection and Redis configuration:

```bash
# Make script executable and run
chmod +x scripts/setup_redis.sh
./scripts/setup_redis.sh
```

The script will:
1. 🔍 **Detect your environment** (systemd, container, macOS, Windows)
2. ⚙️ **Install Redis** using the appropriate method for your system
3. 🚀 **Start Redis service** with proper configuration
4. ✅ **Verify connection** and provide status feedback

---

## Environment-Specific Manual Setup

### 🐧 Ubuntu/Debian Systems (with systemd)

**Standard Installation:**
```bash
# Update package list and install Redis
sudo apt update
sudo apt install redis-server

# Start and enable Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify installation
redis-cli ping  # Should return "PONG"
systemctl status redis-server  # Check service status
```

**Configuration:**
```bash
# Optional: Configure Redis for production use
sudo nano /etc/redis/redis.conf

# Key settings to consider:
# bind 127.0.0.1  # Limit connections to localhost
# requirepass yourpassword  # Set password (optional)
# save 900 1  # Enable persistence

# Restart after configuration changes
sudo systemctl restart redis-server
```

### 🐳 Development Containers (VS Code, Codespaces)

Development containers typically don't support systemd. Choose from these options:

**Option 1: Docker Redis (Recommended if Docker available)**
```bash
# Check if Docker is available
docker --version

# Run Redis in a container
docker run -d \
  --name redis-transcriber \
  --network host \
  -p 6379:6379 \
  redis:7-alpine

# Test connection
redis-cli -h localhost -p 6379 ping

# To stop: docker stop redis-transcriber
# To remove: docker rm redis-transcriber
```

**Option 2: Direct Redis Execution**
```bash
# If Redis is installed but systemd unavailable
redis-server --daemonize yes --port 6379 --bind 127.0.0.1

# Check if running
ps aux | grep redis-server
redis-cli ping
```

**Option 3: Development Fallback (No Redis Installation)**
```bash
# Install Python Redis alternative
pip install fakeredis

# Configure application to use FakeRedis
echo "USE_FAKE_REDIS=true" >> .env
echo "DEVELOPMENT_MODE=true" >> .env

# Application will automatically use FakeRedis
echo "✅ FakeRedis configured - suitable for development only"
```

### 🍎 macOS Systems

**Using Homebrew (Recommended):**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify installation
redis-cli ping  # Should return "PONG"
brew services list | grep redis  # Check service status
```

**Manual macOS Installation:**
```bash
# Download and compile Redis (if Homebrew unavailable)
curl -O http://download.redis.io/redis-stable.tar.gz
tar xzf redis-stable.tar.gz
cd redis-stable
make
make install

# Start Redis manually
redis-server --daemonize yes --port 6379
```

### 🪟 Windows Systems

**Option 1: Docker Desktop (Recommended)**
```powershell
# Ensure Docker Desktop is installed and running
docker --version

# Run Redis container
docker run -d --name redis-transcriber -p 6379:6379 redis:7-alpine

# Test connection (install redis-cli via chocolatey or use Docker exec)
docker exec -it redis-transcriber redis-cli ping
```

**Option 2: WSL2 with Linux Redis**
```bash
# Inside WSL2 Ubuntu/Debian environment
sudo apt update && sudo apt install redis-server

# Start Redis (WSL2 doesn't use systemd by default)
sudo service redis-server start

# Test connection
redis-cli ping
```

**Option 3: Native Windows Redis**
```powershell
# Install via Chocolatey
choco install redis-64

# Or download pre-compiled binaries from:
# https://github.com/tporadowski/redis/releases

# Start Redis
redis-server.exe

# Test in another terminal
redis-cli.exe ping
```

---

## Advanced Configuration

### Production Redis Configuration

For production deployments, consider these Redis optimizations:

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Security
bind 127.0.0.1
requirepass your_secure_password_here
rename-command FLUSHDB ""
rename-command FLUSHALL ""

# Persistence
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Performance
tcp-keepalive 60
timeout 0
```

### Redis for Development vs Production

| Aspect | Development | Production |
|--------|------------|------------|
| **Persistence** | Optional (FakeRedis OK) | Required |
| **Security** | Localhost only | Password protected |
| **Memory** | Unlimited | Configured limits |
| **Backup** | Not needed | Regular snapshots |
| **Monitoring** | Basic | Comprehensive |

---

## Troubleshooting Common Issues

### Redis Connection Refused
```bash
# Check if Redis is running
ps aux | grep redis-server

# Check Redis logs
sudo journalctl -u redis-server  # systemd systems
tail -f /var/log/redis/redis-server.log  # manual installations

# Common solutions:
# 1. Start Redis service
sudo systemctl start redis-server  # or appropriate start command

# 2. Check port binding
netstat -tulpn | grep :6379

# 3. Verify configuration
redis-cli config get bind
```

### Permission Denied Errors
```bash
# Fix Redis directory permissions
sudo chown -R redis:redis /var/lib/redis
sudo chmod 755 /var/lib/redis

# Fix log file permissions
sudo chown redis:redis /var/log/redis/redis-server.log
sudo chmod 644 /var/log/redis/redis-server.log
```

### Memory Issues
```bash
# Check Redis memory usage
redis-cli info memory

# Set memory limit
redis-cli config set maxmemory 256mb
redis-cli config set maxmemory-policy allkeys-lru

# Make changes persistent
redis-cli config rewrite
```

### Container-Specific Issues

**Docker Redis Won't Start:**
```bash
# Check Docker daemon
docker ps
docker logs redis-transcriber

# Restart container
docker restart redis-transcriber

# Use different port if 6379 is occupied
docker run -d --name redis-transcriber -p 6380:6379 redis:7-alpine
# Update .env: REDIS_URL=redis://localhost:6380/0
```

**VS Code Container Issues:**
```bash
# Check if running in container
env | grep -i container
env | grep -i vscode

# Use service command instead of systemctl
sudo service redis-server start
sudo service redis-server status

# If sudo unavailable, use direct execution
redis-server --daemonize yes --port 6379 --bind 127.0.0.1
```

---

## Application Integration

### Environment Variables

Add these to your `.env` file:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Development Options
DEVELOPMENT_MODE=true  # Enables automatic fallbacks
USE_FAKE_REDIS=false   # Set to true for FakeRedis mode

# Production Options
REDIS_PASSWORD=your_password_here  # If password required
REDIS_MAX_CONNECTIONS=10  # Connection pool size
```

### Health Check Commands

Verify your Redis setup:

```bash
# Test basic connection
redis-cli ping

# Check Redis info
redis-cli info server

# Test application connection (after app setup)
curl http://localhost:5000/api/v1/health/redis

# Validate full setup
python -c "
import redis
import os
from dotenv import load_dotenv
load_dotenv()

try:
    r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    r.ping()
    print('✅ Redis connection successful')
    print(f'Redis version: {r.info()[\"redis_version\"]}')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"
```

### Application Fallback Modes

The KazRu-STT Pro application supports automatic fallback when Redis is unavailable:

1. **Primary**: Real Redis server (production)
2. **Fallback 1**: FakeRedis (development)
3. **Fallback 2**: In-memory storage (emergency)

The application will automatically choose the best available option and log which backend is being used.

---

## Migration and Backup

### Backing Up Redis Data

```bash
# Manual backup
redis-cli save
cp /var/lib/redis/dump.rdb /backup/redis-backup-$(date +%Y%m%d).rdb

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backup/redis"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
redis-cli save
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis-backup-$DATE.rdb
find $BACKUP_DIR -name "redis-backup-*.rdb" -mtime +7 -delete
```

### Restoring Redis Data

```bash
# Stop Redis service
sudo systemctl stop redis-server

# Restore backup
cp /backup/redis-backup-20250806.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis service
sudo systemctl start redis-server
```

---

## Getting Help

If you continue to experience Redis setup issues:

1. **Check Application Logs**: Look for Redis connection messages
2. **Verify Environment**: Ensure you're following the correct environment-specific instructions  
3. **Test Fallback**: Try enabling `USE_FAKE_REDIS=true` for development
4. **Review Troubleshooting**: Follow the troubleshooting section systematically
5. **GitHub Issues**: Report persistent issues at the project repository

The application includes comprehensive Redis fallback mechanisms, so Redis setup issues should not prevent development work from proceeding.