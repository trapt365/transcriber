# Development Guide - KazRu-STT Pro

This comprehensive guide covers development setup, workflow, and best practices for contributing to KazRu-STT Pro.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Environment Setup](#development-environment-setup)
3. [Redis Configuration](#redis-configuration)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Code Quality](#code-quality)
7. [Debugging](#debugging)
8. [Contributing Guidelines](#contributing-guidelines)

---

## Quick Start

Get up and running in under 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/trapt365/transcriber.git
cd transcriber

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your Yandex API credentials

# 4. Set up Redis (automated)
chmod +x scripts/setup_redis.sh
./scripts/setup_redis.sh

# 5. Initialize database
export FLASK_APP=backend/app.py
flask db init && flask db migrate -m "Initial" && flask db upgrade

# 6. Start development server
flask run --debug --host=0.0.0.0 --port=5000
```

The application will be available at http://localhost:5000

---

## Development Environment Setup

### Supported Development Environments

- **Local Development**: Ubuntu/Debian, macOS, Windows (WSL2)
- **Containerized**: VS Code Dev Containers, GitHub Codespaces
- **Docker**: Docker Desktop on all platforms

### Environment-Specific Setup

#### VS Code Dev Container Setup
```bash
# If you're using VS Code Dev Container:
# 1. Open project in VS Code
# 2. Install Dev Containers extension
# 3. Cmd/Ctrl+Shift+P -> "Dev Containers: Reopen in Container"
# 4. Container will automatically setup dependencies

# Manual setup in container:
./scripts/setup_redis.sh  # Handles container environment automatically
```

#### GitHub Codespaces Setup
```bash
# Codespaces automatically installs dependencies
# Just run the Redis setup:
./scripts/setup_redis.sh

# Start development:
export FLASK_APP=backend/app.py
flask run --debug --host=0.0.0.0 --port=5000
```

### Essential Dependencies

The project requires these system dependencies:

```bash
# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv python3.11-dev
sudo apt install ffmpeg redis-server
sudo apt install build-essential pkg-config

# macOS
brew install python@3.11 ffmpeg redis
brew install pkg-config

# Windows (via WSL2 + Ubuntu)
# Follow Ubuntu instructions within WSL2
```

---

## Redis Configuration

### Development Redis Options

The application supports multiple Redis configurations for development:

#### Option 1: Real Redis (Production-like)
```bash
# Use setup script (recommended)
./scripts/setup_redis.sh

# Manual setup (Ubuntu/Debian)
sudo apt install redis-server
sudo systemctl start redis-server

# Manual setup (macOS)
brew install redis
brew services start redis
```

#### Option 2: FakeRedis (Development Fallback)
```bash
# Install FakeRedis
pip install fakeredis

# Configure application to use FakeRedis
echo "USE_FAKE_REDIS=true" >> .env
echo "DEVELOPMENT_MODE=true" >> .env

# Start application - it will automatically use FakeRedis
flask run --debug
```

#### Option 3: Docker Redis (Container Environments)
```bash
# Start Redis in Docker
docker run -d --name redis-dev -p 6379:6379 redis:7-alpine

# Or use docker-compose
docker-compose -f docker-compose.dev.yml up redis
```

### Redis Backend Detection

The application automatically detects and uses the best available Redis backend:

1. **Configured Redis** (REDIS_URL environment variable)
2. **Localhost Redis** (redis://localhost:6379)
3. **FakeRedis** (if USE_FAKE_REDIS=true or DEVELOPMENT_MODE=true)
4. **In-memory fallback** (emergency fallback)

Check which backend is active:
```bash
# Start the application and check:
curl http://localhost:5000/api/v1/health/redis

# Response will show backend_type: "redis", "fakeredis", or "memory"
```

---

## Development Workflow

### Project Structure

```
transcriber/
├── backend/                    # Flask application
│   ├── app/                   # Main app package
│   │   ├── models/           # Database models
│   │   ├── routes/           # API routes  
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities
│   ├── config.py             # Configuration
│   └── app.py                # Application factory
├── frontend/                  # Static assets & templates
│   ├── static/               # CSS, JS, images
│   └── templates/            # HTML templates
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── scripts/                   # Development scripts
├── docs/                      # Documentation
└── requirements.txt           # Dependencies
```

### Running the Application

#### Development Mode
```bash
# Set Flask environment
export FLASK_APP=backend/app.py
export FLASK_ENV=development

# Run with auto-reload and debugging
flask run --debug --host=0.0.0.0 --port=5000

# Or with custom configuration
python -m flask run --debug
```

#### Production Mode
```bash
# Set production environment
export FLASK_ENV=production

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 2 "backend.app:create_app()"
```

#### Background Tasks (Celery)
```bash
# Start Celery worker (separate terminal)
celery -A backend.celery_app worker --loglevel=info --pool=threads

# Start Celery beat scheduler (for periodic tasks)
celery -A backend.celery_app beat --loglevel=info
```

### Database Management

#### Initial Setup
```bash
# Initialize migration repository
flask db init

# Create initial migration
flask db migrate -m "Initial database schema"

# Apply migrations
flask db upgrade
```

#### Schema Changes
```bash
# After modifying models, create migration
flask db migrate -m "Description of changes"

# Review generated migration file in migrations/versions/
# Apply migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

---

## Testing

### Test Structure

```
tests/
├── unit/                      # Unit tests
│   ├── test_models.py        # Model tests
│   ├── test_services.py      # Service tests
│   └── test_utils.py         # Utility tests
├── integration/               # Integration tests
│   ├── test_api.py           # API endpoint tests
│   ├── test_processing.py    # Processing pipeline tests
│   └── test_redis.py         # Redis integration tests
├── conftest.py               # Pytest configuration
└── fixtures/                 # Test data
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest -v

# Run with debug output
pytest -s
```

### Test Configuration

Tests automatically use appropriate Redis backend:

```python
# conftest.py automatically configures test Redis
# Tests use FakeRedis by default for isolation
# Integration tests can use real Redis if needed

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'USE_FAKE_REDIS': True,
        'DATABASE_URL': 'sqlite:///:memory:'
    })
    return app
```

### Writing Tests

#### Unit Test Example
```python
# tests/unit/test_redis_service.py
import pytest
from backend.app.services.graceful_redis import GracefulRedisService

def test_redis_set_get():
    redis_service = GracefulRedisService()
    
    # Test basic operations
    assert redis_service.set('test_key', 'test_value') is True
    assert redis_service.get('test_key') == 'test_value'
    assert redis_service.delete('test_key') == 1
    assert redis_service.get('test_key') is None
```

#### Integration Test Example
```python
# tests/integration/test_api.py
def test_health_endpoint(client):
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
```

---

## Code Quality

### Formatting and Linting

```bash
# Format code with Black
black backend/ tests/

# Check formatting
black --check backend/ tests/

# Lint with flake8
flake8 backend/ tests/

# Type checking with mypy (optional)
mypy backend/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

The pre-commit configuration includes:
- Black (formatting)
- Flake8 (linting)
- isort (import sorting)
- Trailing whitespace removal
- Large file detection

### Code Style Guidelines

- **Line Length**: 88 characters (Black default)
- **Import Order**: Use isort for consistent import ordering
- **Docstrings**: Use Google-style docstrings
- **Type Hints**: Use type hints for function parameters and returns
- **Error Handling**: Use specific exception types

#### Example Code Style
```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ExampleService:
    """Service for handling example operations.
    
    Attributes:
        config: Configuration dictionary
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
    
    def process_data(self, data: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Process input data.
        
        Args:
            data: Input data to process
            timeout: Optional timeout in seconds
            
        Returns:
            Processing result dictionary
            
        Raises:
            ValueError: If data is invalid
            TimeoutError: If processing times out
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        try:
            # Processing logic here
            result = {"status": "success", "data": data}
            logger.info(f"Processed data successfully: {len(data)} characters")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            raise
```

---

## Debugging

### Debug Configuration

#### VS Code Launch Configuration
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/app.py",
            "env": {
                "FLASK_APP": "backend.app:create_app",
                "FLASK_ENV": "development"
            },
            "args": ["run", "--debug", "--host", "0.0.0.0", "--port", "5000"],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

### Debugging Tips

#### Application Debugging
```bash
# Enable debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1

# Run with debug server
flask run --debug

# Enable verbose logging
export LOG_LEVEL=DEBUG
```

#### Redis Debugging
```bash
# Check Redis status
curl http://localhost:5000/api/v1/health/redis

# Monitor Redis operations (if using real Redis)
redis-cli monitor

# Check Redis info
redis-cli info

# List Redis keys
redis-cli keys "*"
```

#### Celery Debugging
```bash
# Check Celery worker status
celery -A backend.celery_app inspect active

# Monitor Celery events
celery -A backend.celery_app events

# Purge task queue
celery -A backend.celery_app purge
```

### Common Issues and Solutions

#### Redis Connection Issues
```bash
# Check if Redis is running
ps aux | grep redis-server

# Check Redis logs
journalctl -u redis-server -f

# Test connection manually
redis-cli ping

# Use FakeRedis fallback
echo "USE_FAKE_REDIS=true" >> .env
```

#### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Contributing Guidelines

### Development Process

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/transcriber.git
   cd transcriber
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ./scripts/setup_redis.sh
   ```

4. **Make Changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation as needed

5. **Test Your Changes**
   ```bash
   pytest
   black --check backend/ tests/
   flake8 backend/ tests/
   ```

6. **Commit and Push**
   ```bash
   git add .
   git commit -m "Add feature: description"
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request**
   - Provide clear description of changes
   - Reference related issues
   - Ensure CI checks pass

### Code Review Process

- All changes require review before merging
- Automated tests must pass
- Code style checks must pass
- Documentation must be updated for new features

### Release Process

1. **Version Bump**: Update version in `__init__.py`
2. **Changelog**: Update CHANGELOG.md
3. **Tag Release**: Create git tag for version
4. **Build**: Create distribution packages
5. **Deploy**: Deploy to staging, then production

---

## Additional Resources

- [Architecture Documentation](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Redis Setup Guide](docs/REDIS_SETUP.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

For questions or support, please:
- Check existing documentation
- Search GitHub issues
- Create new issue with detailed description
- Follow issue template for bug reports

---

**Happy coding! 🚀**