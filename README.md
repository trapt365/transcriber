# Transcriber - Audio Transcription Service

Audio transcription service with Yandex SpeechKit integration, built with Flask and modern web technologies.

## Features

- 🎵 **Multi-format Audio Support** - WAV, MP3, M4A, FLAC, OGG
- 🤖 **Yandex SpeechKit Integration** - High-quality speech-to-text
- 📊 **Real-time Processing** - WebSocket/Server-Sent Events for status updates
- 🚀 **Async Processing** - Celery with Redis for background jobs
- 🐳 **Docker Support** - Containerized development and deployment
- 🧪 **Comprehensive Testing** - Unit and integration tests with pytest
- 🔧 **Development Tools** - Black formatting, flake8 linting, pre-commit hooks

## Technology Stack

- **Backend**: Flask 2.3+ with SQLAlchemy, Marshmallow
- **Queue**: Celery 5.3+ with Redis 7.0+
- **Processing**: pydub, librosa, FFmpeg
- **Frontend**: HTML5, Bootstrap 5.3, Vanilla JavaScript
- **Database**: SQLite (MVP), PostgreSQL (Production)
- **Containerization**: Docker 24+ with Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- FFmpeg (for audio processing)
- Redis (if running without Docker)

### Option 1: Docker Development (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd transcriber
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your Yandex SpeechKit credentials
   ```

3. **Start development environment**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Access the application**
   - Web UI: http://localhost:5000
   - Redis: localhost:6379

### Option 2: Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd transcriber
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Redis (required for Celery)**
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine
   
   # Or install Redis locally
   # Ubuntu/Debian: sudo apt install redis-server
   # macOS: brew install redis
   ```

6. **Initialize database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

7. **Start the application**
   ```bash
   # Terminal 1: Flask app
   flask run --debug
   
   # Terminal 2: Celery worker
   celery -A backend.celery_app worker --loglevel=info
   
   # Terminal 3: Celery beat (optional, for scheduled tasks)
   celery -A backend.celery_app beat --loglevel=info
   ```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Yandex SpeechKit (Required)
YANDEX_API_KEY=your-api-key-here
YANDEX_FOLDER_ID=your-folder-id-here

# Database
DATABASE_URL=sqlite:///app.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
```

### Yandex SpeechKit Setup

1. Create a Yandex Cloud account
2. Enable SpeechKit API
3. Create API key and folder ID
4. Add credentials to `.env` file

## Development Workflow

### Code Quality Tools

```bash
# Format code
black backend/ tests/

# Lint code
flake8 backend/ tests/

# Type checking
mypy backend/

# Run pre-commit hooks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

## Project Structure

```
transcriber/
├── backend/                    # Flask application
│   ├── app/                   # Main application package
│   │   ├── models/           # Database models
│   │   ├── routes/           # API routes
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities
│   ├── config.py             # Configuration classes
│   └── app.py                # Application factory
├── frontend/                  # Static files
│   ├── static/               # CSS, JS, images
│   └── templates/            # HTML templates
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── docs/                      # Documentation
├── .github/workflows/         # CI/CD pipelines
├── docker-compose.yml         # Production Docker setup
├── docker-compose.dev.yml     # Development Docker setup
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── pyproject.toml            # Project configuration
```

## API Documentation

### Endpoints

- `GET /` - Main application interface
- `POST /api/upload` - Upload audio file for transcription
- `GET /api/status/{job_id}` - Check transcription status
- `GET /api/result/{job_id}` - Retrieve transcription result
- `GET /health` - Health check endpoint

### WebSocket Events

- `job_started` - Transcription job initiated
- `job_progress` - Processing progress updates
- `job_completed` - Transcription completed
- `job_failed` - Processing error occurred

## Deployment

### Production Docker

```bash
# Build and start production services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up --scale celery=3
```

### Environment-specific Configurations

- **Development**: `FLASK_ENV=development` - Debug enabled, auto-reload
- **Production**: `FLASK_ENV=production` - Optimized, security hardened
- **Testing**: `FLASK_ENV=testing` - In-memory database, CSRF disabled

## Monitoring & Observability

### Health Checks

- Application: `GET /health`
- Redis: `redis-cli ping`
- Celery: `celery -A backend.celery_app inspect active`

### Logging

Logs are written to:
- Console (development)
- File: `logs/app.log` (production)
- Structured JSON format for log aggregation

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Install pre-commit hooks: `pre-commit install`
4. Make changes and commit: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open Pull Request

### Development Standards

- Follow PEP 8 style guide (enforced by black/flake8)
- Write tests for new functionality
- Update documentation for API changes
- Ensure all CI checks pass

## Troubleshooting

### Common Issues

**Virtual environment creation fails**
```bash
# Ubuntu/Debian
sudo apt install python3.11-venv

# Alternative: use system Python
pip install --user -r requirements-dev.txt
```

**Redis connection errors**
```bash
# Check Redis is running
docker ps | grep redis
# Or: redis-cli ping

# Restart Redis
docker-compose restart redis
```

**Celery worker not starting**
```bash
# Check environment variables
echo $REDIS_URL

# Start with verbose logging
celery -A backend.celery_app worker --loglevel=debug
```

### Support

- 📖 [Documentation](docs/)
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

## License

This project is licensed under the MIT License - see the LICENSE file for details.