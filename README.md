# 🎙️ Transcriber - Audio Transcription Service

A professional-grade audio transcription service with **Yandex SpeechKit integration**. Built with Flask and modern web technologies, featuring real-time processing, speaker diarization, and multi-format export capabilities.

## 🚀 Quick Test (Epic 1 - Current Stage)

**Ready to test? Get started in 3 minutes:**

```bash
# 1. Clone and setup
git clone https://github.com/trapt365/transcriber.git
cd transcriber

# 2. Configure Yandex credentials (see Yandex Setup below)
cp .env.example .env
# Edit .env: add your YANDEX_API_KEY and YANDEX_FOLDER_ID

# 3. Start with Docker
docker-compose -f docker-compose.dev.yml up --build

# 4. Test the application
# Open: http://localhost:5000
# Upload: Small audio file (WAV/MP3, <10MB recommended)
# Verify: Real-time status updates and transcript download
```

**🧪 Test Checklist for Epic 1:**
- ✅ File upload interface loads
- ✅ Audio file upload succeeds 
- ✅ Processing status updates in real-time
- ✅ Transcript appears when complete
- ✅ Download transcript works
- ✅ Error handling for invalid files

**📁 Test Audio Files:** Use short samples (30sec-2min) in WAV or MP3 format for initial testing.

---

## 📊 Feature Status

| Feature | Epic 1 Status | Description |
|---------|---------------|-------------|
| 📤 **File Upload** | ✅ **Implemented** | Web interface with drag-and-drop |
| 🔄 **Processing Status** | ✅ **Implemented** | Real-time WebSocket updates |
| 🎵 **Audio Support** | ✅ **Implemented** | WAV, MP3, M4A, FLAC, OGG |
| 🤖 **Yandex Integration** | ✅ **Implemented** | Basic speech-to-text |
| 📄 **Transcript Download** | ✅ **Implemented** | TXT format export |
| 🎭 **Speaker Diarization** | 🔄 **In Progress** | Epic 2 |
| 📊 **Multi-format Export** | 📋 **Planned** | SRT, VTT, CSV, JSON - Epic 2 |
| 🌍 **Multi-language** | 📋 **Planned** | Auto-detection - Epic 3 |
| 🚀 **Advanced Processing** | 📋 **Planned** | Batch, scheduling - Epic 3 |

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

**Quick Setup:**
1. Create Yandex Cloud account: [console.cloud.yandex.com](https://console.cloud.yandex.com)
2. Activate trial period (4000₽ for 60 days)
3. **Create cloud** → **Create folder** (важно: сохраните Folder ID!)
4. **Enable SpeechKit** service in the folder
5. **Create service account** → **Generate API key**
6. Add credentials to `.env` file:

**💡 Где взять Folder ID:** После создания каталога, ID показан в URL: `console.cloud.yandex.com/folders/YOUR_FOLDER_ID`

```bash
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx
```

**📖 Detailed Setup Guide:** See [docs/YANDEX_SETUP.md](docs/YANDEX_SETUP.md) for complete step-by-step instructions.

**🧪 Test Connection:**
```bash
python -c "
import os, requests
key, folder = os.getenv('YANDEX_API_KEY'), os.getenv('YANDEX_FOLDER_ID')
r = requests.post('https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
    headers={'Authorization': f'Api-Key {key}'}, 
    data={'folderId': folder, 'format': 'lpcm', 'sampleRateHertz': '8000'})
print('✅ API works!' if r.status_code in [200,400] else f'❌ Error: {r.status_code}')
"
```

## 🚀 Installation

### Option 1: Docker Setup (Recommended)

```bash
# 1. Clone and setup
git clone https://github.com/trapt365/transcriber.git
cd transcriber

# 2. Configure credentials
cp .env.example .env
# Edit .env: Add your YANDEX_API_KEY and YANDEX_FOLDER_ID

# 3. Start all services
docker-compose -f docker-compose.dev.yml up --build

# 4. Access application
# Web: http://localhost:5000
# Logs: docker-compose logs -f
```

### Option 2: Native Installation (Docker Alternative)

**If Docker is causing issues, use this native installation approach:**

#### Step 1: System Requirements & Dependencies

**Install Python 3.11+ and system dependencies:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-dev
sudo apt install ffmpeg redis-server
sudo apt install build-essential pkg-config

# For older Ubuntu versions, you may need the deadsnakes PPA:
# sudo add-apt-repository ppa:deadsnakes/ppa
# sudo apt update
# sudo apt install python3.11 python3.11-venv python3.11-dev

# macOS (using Homebrew)
brew install python@3.11 ffmpeg redis
brew services start redis

# Start Redis service on Ubuntu/Debian
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### Step 2: Python Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/trapt365/transcriber.git
cd transcriber

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# On Windows: venv\Scripts\activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Install additional development tools (optional)
pip install -r requirements-dev.txt
```

#### Step 3: Configuration

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env file with your Yandex credentials
nano .env  # or use any text editor

# Required settings in .env:
# YANDEX_API_KEY=your_api_key_here
# YANDEX_FOLDER_ID=your_folder_id_here
# REDIS_URL=redis://localhost:6379/0
# DATABASE_URL=sqlite:///transcriber.db
```

#### Step 4: Database Setup

```bash
# Set Flask app
export FLASK_APP=backend/app.py

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create uploads directory
mkdir -p uploads
```

#### Step 5: Start Services

**You need to run these commands in separate terminal windows/tabs:**

**Terminal 1 - Flask Application:**
```bash
cd transcriber
source venv/bin/activate
export FLASK_APP=backend/app.py
flask run --debug --host=0.0.0.0 --port=5000
```

**Terminal 2 - Celery Worker:**
```bash
cd transcriber
source venv/bin/activate
celery -A backend.celery_app worker --loglevel=info --pool=threads
```

**Terminal 3 - Redis (if not running as service):**
```bash
redis-server
```

#### Step 6: Verify Installation

```bash
# Test Redis connection
redis-cli ping  # Should return "PONG"

# Test Yandex API credentials
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
key, folder = os.getenv('YANDEX_API_KEY'), os.getenv('YANDEX_FOLDER_ID')
r = requests.post('https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
    headers={'Authorization': f'Api-Key {key}'}, 
    data={'folderId': folder, 'format': 'lpcm', 'sampleRateHertz': '8000'})
print('✅ API works!' if r.status_code in [200,400] else f'❌ Error: {r.status_code}')
"

# Access application
# Open: http://localhost:5000
```

#### Native Installation Troubleshooting

**❌ Python 3.11 not available:**
```bash
# Check current Python version
python3 --version

# Debian 12/Ubuntu 22.04+ should have Python 3.11+ by default
sudo apt install python3 python3-venv python3-dev

# For older Ubuntu versions (20.04/18.04) - add deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
# Then use python3.11 instead of python3 in commands

# macOS - use pyenv for version management
brew install pyenv
pyenv install 3.11.7
pyenv local 3.11.7
```

**❌ Redis connection errors:**
```bash
# Check Redis status
sudo systemctl status redis-server

# Start Redis manually
redis-server --port 6379 --daemonize yes

# Test connection
redis-cli -p 6379 ping
```

**❌ FFmpeg not found:**
```bash
# Verify FFmpeg installation
ffmpeg -version

# Add to PATH (if needed)
export PATH="/usr/local/bin:$PATH"

# Set FFmpeg path in .env
echo "FFMPEG_PATH=/usr/bin/ffmpeg" >> .env
```

**❌ Permission errors:**
```bash
# Fix upload directory permissions
sudo chown -R $USER:$USER uploads/
chmod 755 uploads/

# Fix Python package permissions
pip install --user --upgrade pip
```

**❌ Port already in use:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill process (replace PID)
kill -9 <PID>

# Or use different port
flask run --port=5001
```

#### Production Deployment (Native)

For production without Docker:

```bash
# Install production WSGI server
pip install gunicorn

# Run with Gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5000 "backend.app:create_app()"

# Run Celery in production
celery -A backend.celery_app worker --loglevel=info --detach

# Set up systemd services (recommended)
# Create service files in /etc/systemd/system/
```

## ⚙️ Configuration

**Essential .env Setup:**
```bash
# Required for Epic 1 testing
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxx
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx

# Optional (defaults work for testing)
FLASK_ENV=development
DATABASE_URL=sqlite:///transcriber.db
REDIS_URL=redis://redis:6379/0
```

<details>
<summary>Complete configuration reference</summary>

### Environment Variables Reference

```bash
# ===== REQUIRED SETTINGS =====
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxx  # API key from Yandex Cloud
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx      # Folder ID from Yandex Cloud

# ===== APPLICATION SETTINGS =====
FLASK_ENV=development                    # development/production/testing
SECRET_KEY=your-secret-key-here         # Generate: python -c "import secrets; print(secrets.token_hex(16))"
DATABASE_URL=sqlite:///transcriber.db    # SQLite for development
REDIS_URL=redis://localhost:6379/0      # Redis connection

# ===== PROCESSING SETTINGS =====
MAX_CONTENT_LENGTH=524288000            # 500MB file limit
UPLOAD_FOLDER=uploads/                  # Upload directory
MAX_AUDIO_DURATION=14400                # 4 hours max duration
FFMPEG_PATH=/usr/bin/ffmpeg             # FFmpeg path

# ===== CELERY SETTINGS =====
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ===== LOGGING =====
LOG_LEVEL=INFO                          # DEBUG/INFO/WARNING/ERROR
FLASK_DEBUG=1                           # Debug mode (development)
```

### Validation Commands

```bash
# Test Yandex API connection
python -c "
import os, requests
key, folder = os.getenv('YANDEX_API_KEY'), os.getenv('YANDEX_FOLDER_ID')
r = requests.post('https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
    headers={'Authorization': f'Api-Key {key}'}, 
    data={'folderId': folder, 'format': 'lpcm', 'sampleRateHertz': '8000'})
print('✅ API works!' if r.status_code in [200,400] else f'❌ Error: {r.status_code}')
"

# Test Redis connection
redis-cli ping  # Should return PONG

# Check environment variables
echo "API Key: ${YANDEX_API_KEY:0:10}..."
echo "Folder ID: $YANDEX_FOLDER_ID"
```

</details>

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