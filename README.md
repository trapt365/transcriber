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

### Шаг 1: Создание аккаунта Yandex Cloud

1. **Регистрация:**
   - Перейдите на [console.cloud.yandex.com](https://console.cloud.yandex.com)
   - Нажмите **"Создать аккаунт"** или войдите через Yandex ID
   - Подтвердите email адрес

2. **Активация пробного периода:**
   - При первом входе активируйте **пробный период** 
   - Вы получите 4000₽ на 60 дней для тестирования
   - Привяжите банковскую карту (средства не списываются в пробном периоде)

### Шаг 2: Создание облака и каталога

1. **Создайте облако (Cloud):**
   - В консоли нажмите **"Создать облако"**
   - Укажите название: `transcriber-cloud`
   - Выберите организацию или создайте новую

2. **Создайте каталог (Folder):**
   - Внутри облака нажмите **"Создать каталог"**
   - Название: `transcriber-folder`
   - **Важно**: Скопируйте **Folder ID** - это ваш `YANDEX_FOLDER_ID`
   - Пример ID: `b1g0123456789abcdef`

### Шаг 3: Включение SpeechKit API

1. **Активация сервиса:**
   - В каталоге перейдите в **"Сервисы"**
   - Найдите **"SpeechKit"** 
   - Нажмите **"Подключить"** или **"Активировать"**
   - Подтвердите включение сервиса

2. **Проверка доступности:**
   - Убедитесь, что статус SpeechKit: **"Активен"**
   - Проверьте квоты: STT (Speech-to-Text) должен быть доступен

### Шаг 4: Создание сервисного аккаунта

1. **Создание аккаунта:**
   - Перейдите в **"Сервисные аккаунты"** → **"Создать сервисный аккаунт"**
   - Имя: `transcriber-service-account`
   - Описание: `Service account for audio transcription`

2. **Назначение ролей:**
   - Добавьте роль: **`ai.speechkit.user`** (для использования SpeechKit)
   - Дополнительно: **`storage.viewer`** (если планируете загрузку из Object Storage)
   - Нажмите **"Создать"**

### Шаг 5: Получение API ключа

1. **Создание API ключа:**
   - Откройте созданный сервисный аккаунт
   - Перейдите на вкладку **"API-ключи"**
   - Нажмите **"Создать API-ключ"**
   - Описание: `Transcriber API Key`

2. **Сохранение ключа:**
   - **⚠️ ВАЖНО**: API ключ показывается только один раз!
   - Скопируйте ключ: `AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Это ваш `YANDEX_API_KEY`
   - Сохраните в надежном месте

### Шаг 6: Альтернативные методы аутентификации

#### Вариант A: IAM токен (временный, рекомендуется для продакшена)

```bash
# Установка Yandex CLI
curl https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash

# Аутентификация
yc init

# Получение IAM токена
yc iam create-token
# Токен действует 12 часов
```

#### Вариант B: Авторизованные ключи (для продакшена)

```bash
# Создание авторизованного ключа
yc iam key create --service-account-name transcriber-service-account --output key.json

# Использование в коде:
export GOOGLE_APPLICATION_CREDENTIALS=key.json
```

### Шаг 7: Настройка квот и лимитов

1. **Проверка квот:**
   - Перейдите в **"Квоты"** → **"SpeechKit"**
   - Убедитесь в наличии квот на:
     - **STT requests per second**: минимум 10
     - **STT requests per hour**: минимум 1000
     - **STT units per month**: в зависимости от потребности

2. **Увеличение квот (при необходимости):**
   - Нажмите **"Изменить квоты"**
   - Заполните форму с обоснованием
   - Ожидайте одобрения (обычно 1-2 дня)

### Шаг 8: Настройка биллинга

1. **Платежный аккаунт:**
   - Перейдите в **"Биллинг"**
   - Создайте платежный аккаунт
   - Привяжите карту для автоплатежей

2. **Мониторинг расходов:**
   - Настройте уведомления о расходах
   - Рекомендуемый лимит: 1000₽/месяц для начала
   - 1 час аудио ≈ 100-200₽ (зависит от качества)

### Шаг 9: Тестирование подключения

**Создайте тестовый скрипт:**

```bash
# test_yandex_connection.py
import os
import requests

API_KEY = "your-api-key-here"
FOLDER_ID = "your-folder-id-here"

# Тест синхронного распознавания (для файлов <1MB)
def test_sync_recognition():
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "text": "привет мир",  # Тест с синтезом речи
        "folderId": FOLDER_ID,
        "format": "lpcm",
        "sampleRateHertz": "8000"
    }
    
    response = requests.post(url, headers=headers, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

# Тест асинхронного распознавания
def test_async_recognition():
    url = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "config": {
            "specification": {
                "languageCode": "ru-RU",
                "model": "general",
                "profanityFilter": False,
                "literature_text": False,
                "format": "lpcm",
                "sampleRateHertz": 8000
            }
        },
        "audio": {
            "uri": f"https://storage.yandexcloud.net/{FOLDER_ID}/test.wav"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Async Status: {response.status_code}")
    return response.status_code in [200, 202]

if __name__ == "__main__":
    print("🧪 Testing Yandex SpeechKit connection...")
    
    if not API_KEY or API_KEY == "your-api-key-here":
        print("❌ Please set your API_KEY")
        exit(1)
    
    if not FOLDER_ID or FOLDER_ID == "your-folder-id-here":
        print("❌ Please set your FOLDER_ID") 
        exit(1)
    
    print("✅ Credentials configured")
    print("🔄 Testing API connection...")
    
    if test_sync_recognition():
        print("✅ Yandex SpeechKit connection successful!")
    else:
        print("❌ Connection failed. Check credentials and quotas.")
```

**Запуск теста:**
```bash
# Установите credentials в .env или экспортируйте
export YANDEX_API_KEY=AQVNxxxxxxxxx
export YANDEX_FOLDER_ID=b1gxxxxxxxxx

# Запустите тест
python test_yandex_connection.py
```

### Шаг 10: Финальная конфигурация

**Добавьте в `.env` файл:**
```bash
# ===== YANDEX SPEECHKIT CONFIGURATION =====
# API Key (обязательно)
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Folder ID (обязательно)  
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx

# Дополнительные настройки (опционально)
YANDEX_API_ENDPOINT=https://stt.api.cloud.yandex.net
YANDEX_ASYNC_ENDPOINT=https://transcribe.api.cloud.yandex.net
YANDEX_DEFAULT_LANGUAGE=ru-RU
YANDEX_MODEL=general
YANDEX_SAMPLE_RATE=16000

# Лимиты и таймауты
YANDEX_REQUEST_TIMEOUT=300
YANDEX_MAX_FILE_SIZE=1073741824  # 1GB
YANDEX_MAX_DURATION=14400        # 4 часа
```

### 🚨 Важные моменты безопасности:

1. **Никогда не публикуйте API ключи в коде**
2. **Используйте переменные окружения**
3. **Регулярно ротируйте API ключи**
4. **Мониторьте использование и расходы**
5. **Настройте уведомления о превышении лимитов**

### 💰 Тарификация (примерные цены):

- **STT (распознавание речи)**: ~2.40₽ за минуту
- **Бесплатный лимит**: 1000 запросов в месяц для разработчиков
- **Дискирование спикеров**: +20% к стоимости
- **Пунктуация**: включена бесплатно

### 📞 Поддержка:

- **Техническая поддержка**: support@cloud.yandex.com  
- **Документация**: [cloud.yandex.ru/docs/speechkit](https://cloud.yandex.ru/docs/speechkit)
- **Сообщество**: [Yandex Cloud Community](https://t.me/yandexcloud)

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
# Получите в консоли Yandex Cloud: https://console.cloud.yandex.com
YANDEX_API_KEY=AQVNxxxxxxxxxxxxxxxxxxxxxxx  # Ваш API ключ из сервисного аккаунта
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxxxx      # ID каталога из консоли Yandex Cloud

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

**Проверка подключения к Yandex SpeechKit:**

```bash
# Запустите тестовый скрипт для проверки подключения
python test_yandex_connection.py

# Или проверьте вручную:
python -c "
import os
import requests

api_key = os.getenv('YANDEX_API_KEY')
folder_id = os.getenv('YANDEX_FOLDER_ID')

if not api_key or not folder_id:
    print('❌ Не настроены YANDEX_API_KEY или YANDEX_FOLDER_ID')
    exit(1)

response = requests.post(
    'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
    headers={'Authorization': f'Api-Key {api_key}'},
    data={'folderId': folder_id, 'format': 'lpcm', 'sampleRateHertz': '8000'},
    timeout=10
)

if response.status_code in [200, 400]:  # 400 для пустых данных - это нормально
    print('✅ Yandex SpeechKit API доступен!')
else:
    print(f'❌ Ошибка API: {response.status_code}')
"

# Проверка других компонентов системы
python backend/validate_config.py  # Если существует
```

**Быстрая диагностика:**

```bash
# Проверка переменных окружения
echo "API Key: ${YANDEX_API_KEY:0:10}..." 
echo "Folder ID: $YANDEX_FOLDER_ID"

# Проверка доступности внешних сервисов
curl -s -o /dev/null -w "%{http_code}" https://stt.api.cloud.yandex.net/  # Должно быть 404
redis-cli ping  # Должно вернуть PONG
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