# 🎙️ Transcriber - Audio Transcription Service

A professional-grade audio transcription service with **Yandex SpeechKit integration**. Built with Flask and modern web technologies, featuring real-time processing, speaker diarization, and multi-format export capabilities.

## ✨ Features

- 🎵 **Multi-format Audio Support** - WAV, MP3, M4A, FLAC, OGG (up to 500MB)
- 🤖 **Yandex SpeechKit Integration** - High-quality speech-to-text with speaker diarization
- 🌍 **Multi-language Support** - Russian, English, Kazakh with auto-detection
- 📊 **Real-time Processing** - WebSocket updates with progress tracking and cancellation
- 🎭 **Speaker Identification** - Automatic speaker labeling and turn organization
- 📄 **Multi-format Export** - Download transcripts as TXT, JSON, SRT, VTT, CSV
- 🚀 **Async Processing** - Celery with Redis for background job processing
- 📱 **Responsive Design** - Mobile-friendly drag-and-drop interface
- 🔧 **Production Ready** - Comprehensive error handling, logging, and monitoring

## Technology Stack

- **Backend**: Flask 2.3+ with SQLAlchemy, Marshmallow
- **Queue**: Celery 5.3+ with Redis 7.0+
- **Processing**: pydub, librosa, FFmpeg
- **Frontend**: HTML5, Bootstrap 5.3, Vanilla JavaScript
- **Database**: SQLite (MVP), PostgreSQL (Production)
- **Containerization**: Docker 24+ with Docker Compose

## Quick Start

## 📋 Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.11+** - [Download Python](https://python.org/downloads/)
- **Git** - [Install Git](https://git-scm.com/downloads)
- **FFmpeg** - Required for audio processing
  - **Ubuntu/Debian**: `sudo apt update && sudo apt install ffmpeg`
  - **macOS**: `brew install ffmpeg`
  - **Windows**: Download from [FFmpeg.org](https://ffmpeg.org/download.html)
- **Redis Server** (if not using Docker)
  - **Ubuntu/Debian**: `sudo apt install redis-server`
  - **macOS**: `brew install redis`
  - **Windows**: Use Docker or WSL2
- **Docker & Docker Compose** (recommended) - [Install Docker](https://docs.docker.com/get-docker/)

## 🎯 Yandex SpeechKit Setup (Required)

1. **Create Yandex Cloud Account**
   - Go to [Yandex Cloud Console](https://console.cloud.yandex.com)
   - Sign up for an account and verify your email

2. **Enable SpeechKit API**
   - Navigate to "SpeechKit" in the console
   - Enable the SpeechKit API service

3. **Get API Credentials**
   - Go to "Service accounts" → Create service account
   - Assign role: `ai.speechkit.user`
   - Create API key and note the **Folder ID**

4. **Save Credentials**
   - You'll need: `YANDEX_API_KEY` and `YANDEX_FOLDER_ID`

## 🚀 Installation Methods

### Method 1: Docker Development (Recommended)

**Step 1: Clone and Setup**
```bash
# Clone the repository
git clone https://github.com/trapt365/transcriber.git
cd transcriber

# Copy and configure environment variables
cp .env.example .env
```

**Step 2: Configure Environment Variables**
Edit `.env` file with your Yandex SpeechKit credentials:
```bash
# Required: Yandex SpeechKit credentials
YANDEX_API_KEY=your-yandex-api-key-here
YANDEX_FOLDER_ID=your-yandex-folder-id-here

# Optional: Other settings (defaults are fine for development)
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///transcriber.db
REDIS_URL=redis://redis:6379/0
```

**Step 3: Start Development Environment**
```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# Run in background
docker-compose -f docker-compose.dev.yml up --build -d
```

**Step 4: Access the Application**
- 🌐 **Web Interface**: http://localhost:5000
- 📊 **Redis**: localhost:6379
- 📝 **Logs**: `docker-compose logs -f`

### Method 2: Local Development

**Step 1: Clone and Setup Virtual Environment**
```bash
# Clone repository
git clone https://github.com/trapt365/transcriber.git
cd transcriber

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

**Step 2: Install Dependencies**
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements-dev.txt

# Verify installation
pip list | grep -E "(flask|celery|redis)"
```

**Step 3: Setup Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials (use nano, vim, or any text editor)
nano .env
```

**Step 4: Start Redis Server**
```bash
# Option A: Using Docker (recommended)
docker run -d --name redis-transcriber -p 6379:6379 redis:7-alpine

# Option B: System Redis (if installed locally)
# Ubuntu/Debian:
sudo systemctl start redis-server
# macOS:
brew services start redis

# Verify Redis is running
redis-cli ping  # Should respond with "PONG"
```

**Step 5: Initialize Database**
```bash
# Set Flask app environment
export FLASK_APP=backend/app.py

# Initialize database (creates migrations folder)
flask db init

# Create initial migration
flask db migrate -m "Initial database setup"

# Apply migrations
flask db upgrade

# Verify database was created
ls -la *.db  # Should show transcriber.db file
```

**Step 6: Start Application Services**

**Terminal 1 - Flask Web Server:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Start Flask development server
export FLASK_APP=backend/app.py
export FLASK_ENV=development
flask run --debug --host=0.0.0.0 --port=5000
```

**Terminal 2 - Celery Worker:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS

# Start Celery worker for background processing
celery -A backend.celery_app worker --loglevel=info --pool=threads
```

**Terminal 3 - Celery Beat (Optional - for scheduled tasks):**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS

# Start Celery beat scheduler
celery -A backend.celery_app beat --loglevel=info
```

**Step 7: Verify Installation**
- 🌐 Open http://localhost:5000 in your browser
- 📤 Try uploading a small audio file
- 📊 Check processing status updates
- 📄 Download transcript when complete

## ⚙️ Configuration

### Environment Variables Reference

Create a `.env` file in the project root with these variables:

```bash
# ===== REQUIRED SETTINGS =====
# Yandex SpeechKit API Credentials (REQUIRED)
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxx  # Your Yandex API key
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx      # Your Yandex folder ID

# ===== APPLICATION SETTINGS =====
# Flask Configuration
FLASK_ENV=development                    # development/production/testing
SECRET_KEY=your-secret-key-here         # Generate with: python -c "import secrets; print(secrets.token_hex(16))"
FLASK_APP=backend/app.py

# Database Configuration
DATABASE_URL=sqlite:///transcriber.db    # SQLite for development
# DATABASE_URL=postgresql://user:pass@localhost:5432/transcriber  # PostgreSQL for production

# Redis Configuration (for Celery task queue)
REDIS_URL=redis://localhost:6379/0      # Local Redis
# REDIS_URL=redis://redis:6379/0         # Docker Redis

# ===== PROCESSING SETTINGS =====
# File Upload Limits
MAX_CONTENT_LENGTH=524288000            # 500MB in bytes
UPLOAD_FOLDER=uploads/                  # Upload directory

# Audio Processing
FFMPEG_PATH=/usr/bin/ffmpeg             # Path to FFmpeg binary
MAX_AUDIO_DURATION=14400                # 4 hours in seconds
AUDIO_PROCESSING_TIMEOUT=3600           # 1 hour timeout

# ===== CELERY SETTINGS =====
# Task Queue Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json

# ===== OPTIONAL SETTINGS =====
# Logging
LOG_LEVEL=INFO                          # DEBUG/INFO/WARNING/ERROR
LOG_FILE=logs/app.log

# Development Tools
FLASK_DEBUG=1                           # Enable debug mode (development only)
```

### 🔧 Configuration Validation

Run this command to validate your configuration:

```bash
# Check if all required environment variables are set
python backend/validate_config.py

# Test Yandex API connection
python -c "
import os
from backend.app.services.yandex_client import YandexSpeechKitClient

client = YandexSpeechKitClient(
    api_key=os.getenv('YANDEX_API_KEY'),
    folder_id=os.getenv('YANDEX_FOLDER_ID')
)
print('✅ Yandex API connection successful')
"
```

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

## 🔧 Troubleshooting

### Common Installation Issues

**❌ Virtual environment creation fails**
```bash
# Ubuntu/Debian - Install venv module
sudo apt update && sudo apt install python3.11-venv python3.11-dev

# Alternative: Use system Python (not recommended)
pip install --user -r requirements-dev.txt

# macOS - Install Python via Homebrew
brew install python@3.11
```

**❌ FFmpeg not found errors**
```bash
# Test FFmpeg installation
ffmpeg -version

# Ubuntu/Debian installation
sudo apt update && sudo apt install ffmpeg

# macOS installation
brew install ffmpeg

# Windows - Add FFmpeg to PATH or set FFMPEG_PATH in .env
```

**❌ Redis connection errors**
```bash
# Test Redis connection
redis-cli ping  # Should return "PONG"

# Docker Redis troubleshooting
docker ps | grep redis                    # Check if Redis container is running
docker logs redis-transcriber            # Check Redis logs
docker restart redis-transcriber         # Restart Redis container

# System Redis troubleshooting
sudo systemctl status redis-server       # Ubuntu/Debian
brew services list | grep redis          # macOS

# Kill existing Redis processes
sudo pkill -f redis-server
```

**❌ Celery worker not starting**
```bash
# Debug Celery configuration
echo $REDIS_URL                         # Should show Redis URL
echo $CELERY_BROKER_URL                 # Should match Redis URL

# Test Celery connection
celery -A backend.celery_app inspect ping

# Start with detailed logging
celery -A backend.celery_app worker --loglevel=debug --pool=threads

# Windows users - use eventlet pool
pip install eventlet
celery -A backend.celery_app worker --loglevel=info --pool=eventlet
```

**❌ Database migration errors**
```bash
# Reset database completely (CAUTION: destroys data)
rm -f transcriber.db
rm -rf migrations/

# Reinitialize database
export FLASK_APP=backend/app.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

**❌ Import errors or module not found**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Verify Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements-dev.txt --force-reinstall
```

**❌ Permission denied errors on uploads**
```bash
# Create upload directory with proper permissions
mkdir -p uploads/
chmod 755 uploads/

# Check disk space
df -h .
```

### Yandex API Issues

**❌ Authentication errors (401)**
```bash
# Verify API credentials
echo $YANDEX_API_KEY
echo $YANDEX_FOLDER_ID

# Test API connection
curl -H "Authorization: Api-Key $YANDEX_API_KEY" \
     "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
```

**❌ Rate limiting (429)**
- Wait a few minutes and retry
- Consider upgrading your Yandex Cloud plan
- Implement request throttling in your application

### Performance Issues

**❌ Slow transcription processing**
```bash
# Check system resources
htop  # or top on macOS/Windows
df -h # disk space

# Increase Celery workers
celery -A backend.celery_app worker --concurrency=4

# Monitor Celery tasks
celery -A backend.celery_app flower  # Web-based monitoring
```

### Getting Help

**📝 Enable Debug Logging**
```bash
# Add to .env file
LOG_LEVEL=DEBUG
FLASK_DEBUG=1

# Check logs
tail -f logs/app.log
```

**🔍 Collect System Information**
```bash
# Generate system info for bug reports
python --version
pip list | grep -E "(flask|celery|redis)"
ffmpeg -version
redis-cli --version
```

## 📚 Additional Resources

### API Documentation

The application provides several REST endpoints:

**Upload & Job Management:**
- `GET /` - Main upload interface
- `POST /api/v1/upload` - Upload audio file for transcription
- `GET /api/v1/jobs/{job_id}` - Get job status and details
- `POST /api/v1/jobs/{job_id}/cancel` - Cancel processing job

**Transcription Results:**
- `GET /api/v1/jobs/{job_id}/transcript` - Get formatted transcript
- `GET /api/v1/jobs/{job_id}/export/{format}` - Download transcript (TXT, JSON, SRT, VTT, CSV)
- `GET /api/v1/jobs/{job_id}/export-formats` - List available export formats

**Real-time Updates:**
- WebSocket events: `job_status_update`, `queue_position_update`
- Server-Sent Events fallback for older browsers

### Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API      │    │   Celery        │
│   (Bootstrap)   │◄──►│   (REST/WebSocket)│◄──►│   (Background)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │                          │
                       ┌───────▼──────────┐    ┌─────────▼─────────┐
                       │   SQLite/PostgreSQL │    │   Yandex SpeechKit │
                       │   (Job Storage)    │    │   (Transcription)  │
                       └────────────────────┘    └───────────────────┘
```

### Production Deployment

For production deployment, consider:

**Infrastructure:**
- Use PostgreSQL instead of SQLite
- Deploy Redis with persistence enabled
- Use reverse proxy (Nginx) for static files
- Configure SSL/TLS certificates

**Scaling:**
```bash
# Scale Celery workers
docker-compose up --scale celery=4

# Use production WSGI server
gunicorn --workers 4 --bind 0.0.0.0:5000 backend.app:create_app()
```

**Security:**
- Change default secret keys
- Configure CORS properly
- Enable rate limiting
- Set up monitoring and logging

### Performance Tips

**For Large Files:**
- Files are processed asynchronously via Celery
- Progress tracking provides real-time updates
- Audio preprocessing optimizes files for Yandex API

**For High Volume:**
- Scale Celery workers horizontally
- Use Redis Cluster for high availability
- Consider load balancing across multiple instances

### Contributing & Support

**Contributing:**
1. Fork the repository: https://github.com/trapt365/transcriber/fork
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Install pre-commit hooks: `pre-commit install`
4. Make changes and commit: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open Pull Request

**Getting Help:**
- 📖 **Documentation**: Check the `docs/` folder
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/trapt365/transcriber/issues)
- 💬 **Questions**: [GitHub Discussions](https://github.com/trapt365/transcriber/discussions)
- 📧 **Security Issues**: Report privately via GitHub security advisories

**Development Standards:**
- Follow PEP 8 style guide (enforced by black/flake8)
- Write tests for new functionality (pytest)
- Update documentation for API changes
- Ensure all CI checks pass before submitting PRs

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**🎉 Ready to transcribe? Start by uploading your first audio file!**

Built with ❤️ using Flask, Celery, and Yandex SpeechKit