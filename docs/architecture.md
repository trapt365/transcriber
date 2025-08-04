# KazRu-STT Pro Technical Architecture

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Technology Stack Details](#technology-stack-details)
3. [Database Design](#database-design)
4. [API Architecture](#api-architecture)
5. [File Processing Pipeline](#file-processing-pipeline)
6. [Deployment Architecture](#deployment-architecture)
7. [Security Architecture](#security-architecture)
8. [Monitoring & Observability](#monitoring--observability)
9. [Scalability Plan](#scalability-plan)
10. [Phase 2 Evolution Path](#phase-2-evolution-path)

## System Architecture Overview

### High-Level Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Frontend Web UI   │    │   Backend API        │    │   External Services │
│                     │    │                      │    │                     │
│ - Upload Interface  │◄──►│ - Flask Application  │◄──►│ - Yandex SpeechKit │
│ - Status Tracking   │    │ - File Management    │    │ - File Storage      │
│ - Results Display   │    │ - Processing Queue   │    │ - Monitoring        │
│ - Export Downloads  │    │ - Export Generation  │    │                     │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
           │                           │                           │
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                           ┌───────────▼────────────┐
                           │     Data Layer         │
                           │                        │
                           │ - SQLite (MVP)         │
                           │ - File System Storage  │
                           │ - Redis (Queuing)      │
                           │ - Session Storage      │
                           └────────────────────────┘
```

### Core Components

1. **Web Frontend**: Responsive HTML5/CSS3/JavaScript interface with drag-and-drop file upload
2. **Flask API Backend**: RESTful API handling file processing, status tracking, and export generation
3. **Processing Engine**: Yandex SpeechKit integration with retry logic and error handling
4. **File Manager**: Secure file upload, storage, validation, and automated cleanup
5. **Export System**: Multi-format transcript generation (Plain Text, SRT, VTT, JSON)
6. **Queue System**: Redis-backed Celery for concurrent processing management
7. **Monitoring Layer**: Health checks, logging, metrics collection, and alerting

### Data Flow

```
Upload → Validation → Queue → Processing → Export → Cleanup
   │         │          │         │          │        │
   ▼         ▼          ▼         ▼          ▼        ▼
Web UI → File Check → Redis → Yandex API → Generate → Delete
```

1. **Upload**: User uploads audio file via web interface
2. **Validation**: File format, size, and content validation
3. **Queue**: Job queued in Redis for processing
4. **Processing**: Yandex SpeechKit transcription with diarization
5. **Export**: Multi-format transcript generation
6. **Cleanup**: Automated file deletion after 24 hours

## Technology Stack Details

### Backend Framework
- **Flask 2.3+**: Lightweight web framework for MVP speed
- **Flask-SQLAlchemy 3.0+**: ORM for database operations
- **Flask-Migrate**: Database migration management
- **Flask-CORS**: Cross-origin resource sharing
- **Marshmallow 3.19+**: Request/response serialization

**Rationale**: Flask provides rapid development capability while maintaining production readiness. Its ecosystem supports all required features without over-engineering.

### Processing & Queue Management
- **Celery 5.3+**: Distributed task queue for concurrent processing
- **Redis 7.0+**: Message broker and caching layer
- **Kombu**: Celery message transport abstraction

**Rationale**: Celery+Redis provides robust async processing with minimal setup complexity, supporting the 5 concurrent user requirement.

### External APIs
- **Yandex SpeechKit Python SDK**: Primary STT service
- **requests 2.31+**: HTTP client with retry capabilities
- **urllib3**: Connection pooling and retry logic

**Rationale**: Yandex SpeechKit provides best-in-class Kazakh-Russian language support with built-in diarization.

### File Processing
- **pydub 0.25+**: Audio format conversion and manipulation
- **librosa 0.10+**: Audio analysis and preprocessing
- **FFmpeg**: Audio codec support (system dependency)

**Rationale**: Comprehensive audio processing capabilities for format standardization and optimization.

### Frontend Stack
- **HTML5**: Modern web standards with File API support
- **Bootstrap 5.3**: Responsive UI framework
- **Vanilla JavaScript ES6+**: No framework overhead for MVP
- **WebSocket/Server-Sent Events**: Real-time status updates

**Rationale**: Minimal dependencies, fast loading, maximum compatibility across browsers.

### Development & Testing
- **pytest 7.4+**: Testing framework
- **pytest-cov**: Coverage reporting
- **black**: Code formatting
- **flake8**: Linting
- **pre-commit**: Git hooks for code quality

### Containerization & Deployment
- **Docker 24+**: Containerization
- **Docker Compose**: Multi-container orchestration
- **nginx**: Reverse proxy and static file serving
- **gunicorn**: WSGI HTTP server

## Database Design

### MVP Schema (SQLite)

```sql
-- Job tracking and processing status
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) UNIQUE NOT NULL,           -- UUID for external reference
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_format VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    progress INTEGER DEFAULT 0,                   -- Processing progress 0-100
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL               -- For 24-hour cleanup
);

-- Processing results and metadata
CREATE TABLE job_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) NOT NULL,
    raw_transcript TEXT,                        -- Original API response
    formatted_transcript TEXT,                  -- Processed transcript
    speaker_count INTEGER,
    confidence_score FLOAT,
    language_detected VARCHAR(50),
    processing_duration INTEGER,                -- Seconds
    api_cost DECIMAL(10,4),                    -- Track Yandex API costs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Speaker information from diarization
CREATE TABLE speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) NOT NULL,
    speaker_id VARCHAR(20) NOT NULL,           -- Speaker 1, Speaker 2, etc.
    speaker_label VARCHAR(100),                -- User-customizable name
    speaking_duration INTEGER,                 -- Total seconds
    segment_count INTEGER,                     -- Number of speaking segments
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Transcript segments with timestamps
CREATE TABLE transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(36) NOT NULL,
    speaker_id VARCHAR(20) NOT NULL,
    start_time DECIMAL(10,3) NOT NULL,         -- Seconds with millisecond precision
    end_time DECIMAL(10,3) NOT NULL,
    text TEXT NOT NULL,
    confidence DECIMAL(5,4),                   -- 0.0000 to 1.0000
    segment_order INTEGER NOT NULL,            -- Sequence in transcript
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- System usage tracking
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    files_processed INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0,          -- Total audio minutes processed
    api_cost_total DECIMAL(10,4) DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_expires_at ON jobs(expires_at);
CREATE INDEX idx_job_results_job_id ON job_results(job_id);
CREATE INDEX idx_speakers_job_id ON speakers(job_id);
CREATE INDEX idx_transcript_segments_job_id ON transcript_segments(job_id);
CREATE INDEX idx_transcript_segments_order ON transcript_segments(job_id, segment_order);
```

### Migration Strategy

**Phase 1 (MVP)**: SQLite with file-based storage
- Single file database for simplicity
- Automatic schema creation on first run
- Built-in backup via file copy

**Phase 2 (Production)**: PostgreSQL migration
```python
# Migration utility structure
class DatabaseMigrator:
    def migrate_sqlite_to_postgres(self):
        # 1. Export SQLite data to JSON
        # 2. Create PostgreSQL schema
        # 3. Import data with validation
        # 4. Verify data integrity
        # 5. Switch application config
```

### Data Relationships

```
jobs (1) ──── (1) job_results
  │
  ├── (1:N) speakers
  │
  └── (1:N) transcript_segments
```

## API Architecture

### RESTful Endpoints

```python
# File Upload and Management
POST   /api/v1/upload                 # Upload audio file
GET    /api/v1/jobs/{job_id}          # Get job status
DELETE /api/v1/jobs/{job_id}          # Cancel/delete job
GET    /api/v1/jobs                   # List user jobs (future auth)

# Processing and Results
GET    /api/v1/jobs/{job_id}/status   # Real-time status updates
GET    /api/v1/jobs/{job_id}/transcript # Get formatted transcript
PUT    /api/v1/jobs/{job_id}/speakers # Update speaker labels

# Export Endpoints
GET    /api/v1/jobs/{job_id}/export/txt    # Plain text export
GET    /api/v1/jobs/{job_id}/export/srt    # SRT subtitle export
GET    /api/v1/jobs/{job_id}/export/vtt    # VTT subtitle export
GET    /api/v1/jobs/{job_id}/export/json   # JSON structured export

# System Endpoints
GET    /api/v1/health                 # Health check
GET    /api/v1/status                 # System status
```

### Request/Response Schemas

```python
# Upload Request
class FileUploadRequest:
    file: MultipartFile           # Audio file
    metadata: dict = {}          # Optional metadata

# Job Status Response
class JobStatusResponse:
    job_id: str
    status: JobStatus            # UPLOADED, PROCESSING, COMPLETED, FAILED
    progress: int               # 0-100
    created_at: datetime
    estimated_completion: datetime = None
    error_message: str = None

# Transcript Response
class TranscriptResponse:
    job_id: str
    speakers: List[Speaker]
    segments: List[TranscriptSegment]
    metadata: TranscriptMetadata
    
class Speaker:
    speaker_id: str
    label: str = None
    speaking_duration: int
    segment_count: int

class TranscriptSegment:
    speaker_id: str
    start_time: float
    end_time: float
    text: str
    confidence: float
```

### Authentication & Authorization

**MVP Phase**: Session-based authentication
```python
@app.before_request
def load_session():
    # Simple session management for MVP
    session_id = request.headers.get('X-Session-ID') or session.get('session_id')
    if not session_id:
        session['session_id'] = str(uuid.uuid4())
```

**Production Phase**: JWT-based authentication
```python
@jwt_required()
def protected_endpoint():
    user_id = get_jwt_identity()
    # Process with user context
```

### Error Handling

```python
class APIError(Exception):
    def __init__(self, message: str, code: int = 400, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}

@app.errorhandler(APIError)
def handle_api_error(error):
    return jsonify({
        'error': error.message,
        'code': error.code,
        'details': error.details,
        'timestamp': datetime.utcnow().isoformat()
    }), error.code

# Specific error types
class FileValidationError(APIError):
    pass

class ProcessingError(APIError):
    pass

class ExternalAPIError(APIError):
    pass
```

### Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/v1/upload')
@limiter.limit("5 per minute")  # Prevent abuse
def upload_file():
    pass
```

## File Processing Pipeline

### Upload Workflow

```python
def process_upload(file) -> str:
    """
    Upload processing pipeline
    Returns: job_id for tracking
    """
    # 1. Validation
    validate_file_format(file)
    validate_file_size(file)
    validate_audio_content(file)
    
    # 2. Storage
    job_id = str(uuid.uuid4())
    file_path = save_file_securely(file, job_id)
    
    # 3. Database Record
    job = create_job_record(job_id, file.filename, file_path)
    
    # 4. Queue for Processing
    process_audio_task.delay(job_id)
    
    return job_id
```

### Processing Pipeline

```python
@celery.task(bind=True)
def process_audio_task(self, job_id: str):
    """
    Main audio processing task
    """
    try:
        # Update status
        update_job_status(job_id, JobStatus.PROCESSING, progress=10)
        
        # 1. Preprocess Audio
        audio_path = preprocess_audio(job_id)
        update_job_status(job_id, JobStatus.PROCESSING, progress=30)
        
        # 2. Yandex API Call
        transcript_data = call_yandex_api(audio_path)
        update_job_status(job_id, JobStatus.PROCESSING, progress=70)
        
        # 3. Process Results
        process_transcript_data(job_id, transcript_data)
        update_job_status(job_id, JobStatus.PROCESSING, progress=90)
        
        # 4. Generate Exports
        generate_export_formats(job_id)
        update_job_status(job_id, JobStatus.COMPLETED, progress=100)
        
    except Exception as e:
        handle_processing_error(job_id, e)
        update_job_status(job_id, JobStatus.FAILED, error=str(e))
```

### Yandex API Integration

```python
class YandexSpeechKitClient:
    def __init__(self):
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.session = requests.Session()
        self.session.mount('https://', HTTPAdapter(max_retries=3))
    
    def transcribe_audio(self, audio_path: str) -> dict:
        """
        Transcribe audio with retry logic and error handling
        """
        config = {
            'specification': {
                'languageCode': 'auto',  # Universal mode
                'model': 'general',
                'profanityFilter': False,
                'literature_text': True,
                'format': 'lpcm',
                'sampleRateHertz': 16000,
            },
            'recognition_config': {
                'enable_speaker_diarization': True,
                'max_speaker_count': 10,
                'enable_automatic_punctuation': True,
            }
        }
        
        with open(audio_path, 'rb') as audio_file:
            response = self._call_api_with_retry(audio_file, config)
            
        return self._process_response(response)
    
    def _call_api_with_retry(self, audio_file, config) -> dict:
        """Implements exponential backoff retry"""
        for attempt in range(3):
            try:
                response = self.session.post(
                    'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
                    headers={'Authorization': f'Api-Key {self.api_key}'},
                    files={'audio': audio_file},
                    data={'config': json.dumps(config)},
                    timeout=300  # 5 minutes timeout
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == 2:  # Last attempt
                    raise ExternalAPIError(f"Yandex API failed: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
```

### File Cleanup Automation

```python
@celery.task
def cleanup_expired_files():
    """
    Automated cleanup task - runs every hour
    """
    expired_jobs = Job.query.filter(
        Job.expires_at < datetime.utcnow(),
        Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
    ).all()
    
    for job in expired_jobs:
        try:
            # Delete physical files
            if os.path.exists(job.file_path):
                os.remove(job.file_path)
            
            # Clean export files
            export_dir = f"exports/{job.job_id}"
            if os.path.exists(export_dir):
                shutil.rmtree(export_dir)
            
            # Update database
            job.status = JobStatus.DELETED
            db.session.commit()
            
            logger.info(f"Cleaned up job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Cleanup failed for job {job.job_id}: {str(e)}")

# Schedule cleanup task
from celery.schedules import crontab

celery.conf.beat_schedule = {
    'cleanup-expired-files': {
        'task': 'cleanup_expired_files',
        'schedule': crontab(minute=0),  # Run every hour
    },
}
```

## Deployment Architecture

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "app:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///app.db
      - REDIS_URL=redis://redis:6379/0
      - YANDEX_API_KEY=${YANDEX_API_KEY}
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    depends_on:
      - redis
      - worker
    restart: unless-stopped

  worker:
    build: .
    command: celery -A app.celery worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=sqlite:///app.db
      - REDIS_URL=redis://redis:6379/0
      - YANDEX_API_KEY=${YANDEX_API_KEY}
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    depends_on:
      - redis
    restart: unless-stopped

  beat:
    build: .
    command: celery -A app.celery beat --loglevel=info
    environment:
      - DATABASE_URL=sqlite:///app.db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - web
    restart: unless-stopped

volumes:
  redis_data:
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy KazRu-STT Pro

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 app/ tests/
        black --check app/ tests/
    
    - name: Run tests
      run: |
        pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t kazru-stt:${{ github.sha }} .
        docker tag kazru-stt:${{ github.sha }} kazru-stt:latest
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_TOKEN }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push kazru-stt:${{ github.sha }}
        docker push kazru-stt:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/kazru-stt
          docker-compose pull
          docker-compose up -d
          docker-compose exec web flask db upgrade
```

### Environment Configuration

```bash
# .env.production
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///data/app.db
REDIS_URL=redis://redis:6379/0

# Yandex API
YANDEX_API_KEY=your-yandex-api-key
YANDEX_FOLDER_ID=your-folder-id

# File storage
UPLOAD_FOLDER=/app/uploads
MAX_FILE_SIZE=524288000  # 500MB
ALLOWED_EXTENSIONS=wav,mp3,flac

# Processing
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
MAX_CONCURRENT_JOBS=5

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

## Security Architecture

### Input Validation & Sanitization

```python
class FileValidator:
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac'}
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    @staticmethod
    def validate_upload(file) -> None:
        # Check file extension
        if not FileValidator._has_allowed_extension(file.filename):
            raise FileValidationError("Unsupported file format")
        
        # Check file size
        if file.content_length > FileValidator.MAX_FILE_SIZE:
            raise FileValidationError("File too large")
        
        # Validate audio content
        if not FileValidator._is_valid_audio(file):
            raise FileValidationError("Invalid audio file")
    
    @staticmethod
    def _is_valid_audio(file) -> bool:
        """Validate file is actually audio using librosa"""
        try:
            # Read first 10 seconds to validate
            y, sr = librosa.load(file, duration=10.0)
            return len(y) > 0 and sr > 0
        except Exception:
            return False
```

### Data Protection

```python
class SecureFileManager:
    def __init__(self):
        self.upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
        os.makedirs(self.upload_dir, mode=0o700, exist_ok=True)
    
    def save_file(self, file, job_id: str) -> str:
        """Save file with secure naming and permissions"""
        # Generate secure filename
        secure_name = f"{job_id}_{int(time.time())}.{file.filename.rsplit('.', 1)[1].lower()}"
        file_path = os.path.join(self.upload_dir, secure_name)
        
        # Save with restricted permissions
        file.save(file_path)
        os.chmod(file_path, 0o600)  # Read/write for owner only
        
        return file_path
    
    def encrypt_file(self, file_path: str) -> str:
        """Encrypt file at rest (production enhancement)"""
        from cryptography.fernet import Fernet
        key = os.getenv('FILE_ENCRYPTION_KEY').encode()
        fernet = Fernet(key)
        
        with open(file_path, 'rb') as f:
            encrypted_data = fernet.encrypt(f.read())
        
        encrypted_path = file_path + '.enc'
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        os.remove(file_path)  # Remove unencrypted file
        return encrypted_path
```

### API Security

```python
from flask_limiter import Limiter
from flask_talisman import Talisman

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"]
)

# Security headers
Talisman(app, {
    'force_https': True,
    'strict_transport_security': True,
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",  # Bootstrap inline scripts
        'style-src': "'self' 'unsafe-inline'",   # Bootstrap inline styles
        'img-src': "'self' data:",
        'connect-src': "'self'",
    }
})

# CSRF Protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Session Security
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)
```

### Data Privacy Compliance

```python
class PrivacyManager:
    @staticmethod
    def schedule_data_deletion(job_id: str):
        """Schedule automatic data deletion"""
        deletion_time = datetime.utcnow() + timedelta(hours=24)
        
        # Update job expiration
        job = Job.query.filter_by(job_id=job_id).first()
        job.expires_at = deletion_time
        db.session.commit()
        
        # Schedule cleanup task
        cleanup_job_data.apply_async(args=[job_id], eta=deletion_time)
    
    @staticmethod
    def anonymize_logs(log_entry: str) -> str:
        """Remove PII from log entries"""
        # Remove potential email addresses
        log_entry = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', log_entry)
        
        # Remove potential phone numbers
        log_entry = re.sub(r'\b\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', '[PHONE]', log_entry)
        
        return log_entry
```

## Monitoring & Observability

### Health Checks

```python
@app.route('/api/v1/health')
def health_check():
    """Comprehensive health check endpoint"""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config.get('VERSION', '1.0.0'),
        'checks': {}
    }
    
    # Database connectivity
    try:
        db.session.execute('SELECT 1')
        status['checks']['database'] = 'healthy'
    except Exception as e:
        status['checks']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Redis connectivity
    try:
        redis_client.ping()
        status['checks']['redis'] = 'healthy'
    except Exception as e:
        status['checks']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Yandex API connectivity
    try:
        # Quick API test (cached for 5 minutes)
        test_result = cache.get('yandex_api_test')
        if test_result is None:
            # Perform actual test
            yandex_client = YandexSpeechKitClient()
            test_result = yandex_client.test_connection()
            cache.set('yandex_api_test', test_result, timeout=300)
        
        status['checks']['yandex_api'] = 'healthy' if test_result else 'unhealthy'
    except Exception as e:
        status['checks']['yandex_api'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Worker status
    try:
        inspect = celery.control.inspect()
        active_workers = inspect.active()
        status['checks']['workers'] = f"active: {len(active_workers) if active_workers else 0}"
    except Exception as e:
        status['checks']['workers'] = f'unhealthy: {str(e)}'
        status['status'] = 'degraded'
    
    status_code = 200 if status['status'] == 'healthy' else 503
    return jsonify(status), status_code
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
PROCESSING_DURATION = Histogram('audio_processing_duration_seconds', 'Audio processing duration')
ACTIVE_JOBS = Gauge('active_jobs_total', 'Number of active processing jobs')
API_COST = Counter('yandex_api_cost_total', 'Total Yandex API cost')

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(time.time() - request.start_time)
    return response

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()
```

### Logging Configuration

```python
import logging
from logging.handlers import RotatingFileHandler
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add custom fields
        if hasattr(record, 'job_id'):
            log_entry['job_id'] = record.job_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        return json.dumps(log_entry)

def setup_logging(app):
    if not app.debug:
        # File handler with rotation
        file_handler = RotatingFileHandler(
            'logs/app.log', maxBytes=10240000, backupCount=10
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Set logging level
        app.logger.setLevel(logging.INFO)
        app.logger.info('KazRu-STT Pro startup')
```

### Alerting Configuration

```python
class AlertManager:
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.email_settings = {
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD')
        }
    
    def send_alert(self, level: str, message: str, details: dict = None):
        """Send alert to configured channels"""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'service': 'kazru-stt-pro',
            'message': message,
            'details': details or {}
        }
        
        if level in ['CRITICAL', 'ERROR']:
            self._send_slack_alert(alert)
            self._send_email_alert(alert)
        elif level == 'WARNING':
            self._send_slack_alert(alert)
    
    def _send_slack_alert(self, alert):
        """Send alert to Slack channel"""
        if not self.slack_webhook:
            return
        
        color = {
            'CRITICAL': 'danger',
            'ERROR': 'danger',
            'WARNING': 'warning',
            'INFO': 'good'
        }.get(alert['level'], 'good')
        
        payload = {
            'attachments': [{
                'color': color,
                'title': f"KazRu-STT Pro Alert: {alert['level']}",
                'text': alert['message'],
                'fields': [
                    {'title': key, 'value': str(value), 'short': True}
                    for key, value in alert['details'].items()
                ],
                'ts': int(datetime.fromisoformat(alert['timestamp']).timestamp())
            }]
        }
        
        requests.post(self.slack_webhook, json=payload)

# Usage in error handlers
alert_manager = AlertManager()

@app.errorhandler(500)
def internal_error(error):
    alert_manager.send_alert(
        'ERROR',
        'Internal server error occurred',
        {
            'error': str(error),
            'endpoint': request.endpoint,
            'method': request.method,
            'user_agent': request.user_agent.string
        }
    )
    
    return jsonify({'error': 'Internal server error'}), 500
```

## Scalability Plan

### Concurrent Processing Architecture

```python
# Celery configuration for scalability
from celery import Celery
from kombu import Queue

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    
    # Configure queues for different priorities
    celery.conf.task_routes = {
        'process_audio_task': {'queue': 'processing'},
        'cleanup_expired_files': {'queue': 'maintenance'},
        'generate_export': {'queue': 'export'}
    }
    
    celery.conf.task_default_queue = 'default'
    celery.conf.task_queues = (
        Queue('default'),
        Queue('processing', routing_key='processing'),
        Queue('maintenance', routing_key='maintenance'),
        Queue('export', routing_key='export'),
    )
    
    # Worker configuration
    celery.conf.worker_prefetch_multiplier = 1  # Prevent worker hoarding
    celery.conf.task_acks_late = True           # Ensure reliability
    celery.conf.worker_max_tasks_per_child = 100  # Prevent memory leaks
    
    return celery
```

### Resource Management

```python
class ResourceManager:
    def __init__(self):
        self.max_concurrent_jobs = int(os.getenv('MAX_CONCURRENT_JOBS', 5))
        self.redis_client = redis.Redis.from_url(os.getenv('REDIS_URL'))
    
    def can_process_job(self) -> bool:
        """Check if system can handle another job"""
        active_jobs = self.get_active_job_count()
        return active_jobs < self.max_concurrent_jobs
    
    def get_active_job_count(self) -> int:
        """Get current number of active processing jobs"""
        active_count = Job.query.filter_by(status=JobStatus.PROCESSING).count()
        return active_count
    
    def estimate_queue_time(self) -> int:
        """Estimate queue wait time in seconds"""
        queue_length = self.get_queue_length()
        avg_processing_time = self.get_average_processing_time()
        
        return (queue_length * avg_processing_time) // self.max_concurrent_jobs
    
    def get_queue_length(self) -> int:
        """Get current queue length"""
        queued_count = Job.query.filter_by(status=JobStatus.UPLOADED).count()
        return queued_count
    
    def get_average_processing_time(self) -> int:
        """Get average processing time from recent jobs"""
        recent_jobs = Job.query.filter(
            Job.status == JobStatus.COMPLETED,
            Job.completed_at > datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if not recent_jobs:
            return 600  # Default 10 minutes
        
        total_time = sum(
            (job.completed_at - job.started_at).total_seconds()
            for job in recent_jobs
            if job.started_at and job.completed_at
        )
        
        return int(total_time / len(recent_jobs))
```

### Auto-scaling Configuration

```yaml
# Docker Swarm configuration for horizontal scaling
version: '3.8'

services:
  web:
    image: kazru-stt:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    ports:
      - "5000:5000"
    networks:
      - app_network

  worker:
    image: kazru-stt:latest
    command: celery -A app.celery worker --loglevel=info --concurrency=2
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
    networks:
      - app_network

  redis:
    image: redis:7-alpine
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
      placement:
        constraints: [node.role == manager]
    networks:
      - app_network

networks:
  app_network:
    driver: overlay
```

### Performance Optimization

```python
class PerformanceOptimizer:
    def __init__(self):
        self.cache = redis.Redis.from_url(os.getenv('REDIS_URL'))
    
    def optimize_audio_for_api(self, file_path: str) -> str:
        """Optimize audio file for Yandex API processing"""
        from pydub import AudioSegment
        
        audio = AudioSegment.from_file(file_path)
        
        # Convert to optimal format for API
        audio = audio.set_frame_rate(16000)  # 16kHz sample rate
        audio = audio.set_channels(1)        # Mono
        audio = audio.set_sample_width(2)    # 16-bit
        
        # Apply audio normalization
        audio = audio.normalize()
        
        # Export optimized version
        optimized_path = file_path.replace('.', '_optimized.')
        audio.export(optimized_path, format="wav")
        
        return optimized_path
    
    def cache_processing_result(self, job_id: str, result: dict):
        """Cache processing results for duplicate files"""
        file_hash = self.get_file_hash(job_id)
        cache_key = f"result:{file_hash}"
        
        # Cache for 7 days
        self.cache.setex(
            cache_key,
            timedelta(days=7).total_seconds(),
            json.dumps(result)
        )
    
    def get_cached_result(self, job_id: str) -> dict:
        """Retrieve cached result if available"""
        file_hash = self.get_file_hash(job_id)
        cache_key = f"result:{file_hash}"
        
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        return None
    
    def get_file_hash(self, job_id: str) -> str:
        """Generate hash for file content"""
        job = Job.query.filter_by(job_id=job_id).first()
        if not job or not os.path.exists(job.file_path):
            return None
        
        import hashlib
        hash_md5 = hashlib.md5()
        with open(job.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
```

## Phase 2 Evolution Path

### Microservices Architecture

```python
# Proposed Phase 2 architecture
"""
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │    │   User Service   │    │  Auth Service   │
│                 │    │                  │    │                 │
│ - Rate Limiting │◄──►│ - User Profiles  │◄──►│ - JWT Tokens    │
│ - Load Balancing│    │ - Usage Tracking │    │ - OAuth2        │
│ - Request Routing│   │ - Billing        │    │ - Permissions   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Processing Svc  │    │  Storage Service │    │ Export Service  │
│                 │    │                  │    │                 │
│ - STT Providers │◄──►│ - File Storage   │◄──►│ - Multi-format  │
│ - Queue Mgmt    │    │ - Metadata DB    │    │ - Templates     │
│ - Diarization   │    │ - Backup/Archive │    │ - Delivery      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  AI/ML Service  │
│                 │
│ - Local Whisper │
│ - Enhanced Diarz│
│ - Custom Models │
└─────────────────┘
"""

# Service interface definitions
from abc import ABC, abstractmethod

class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, config: dict) -> dict:
        pass

class YandexSTTProvider(STTProvider):
    def transcribe(self, audio_path: str, config: dict) -> dict:
        # Existing Yandex implementation
        pass

class WhisperSTTProvider(STTProvider):
    def transcribe(self, audio_path: str, config: dict) -> dict:
        import whisper
        
        model = whisper.load_model(config.get('model_size', 'base'))
        result = model.transcribe(
            audio_path,
            language=config.get('language'),
            task=config.get('task', 'transcribe')
        )
        
        return self._format_result(result)
    
    def _format_result(self, whisper_result: dict) -> dict:
        # Convert Whisper format to standard format
        pass
```

### Enhanced Diarization Service

```python
class EnhancedDiarizationService:
    def __init__(self):
        self.pipeline = None
        self._load_pyannote_model()
    
    def _load_pyannote_model(self):
        """Load pyannote.audio model for enhanced diarization"""
        try:
            from pyannote.audio import Pipeline
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization",
                use_auth_token=os.getenv('HUGGINGFACE_TOKEN')
            )
        except ImportError:
            logger.warning("pyannote.audio not available, using basic diarization")
    
    def diarize_audio(self, audio_path: str) -> dict:
        """Enhanced speaker diarization with pyannote.audio"""
        if not self.pipeline:
            return self._basic_diarization(audio_path)
        
        # Apply the pipeline to an audio file
        diarization = self.pipeline(audio_path)
        
        # Convert to standard format
        speakers = {}
        segments = []
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_id = f"Speaker_{speaker}"
            
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    'speaker_id': speaker_id,
                    'total_duration': 0,
                    'segment_count': 0
                }
            
            speakers[speaker_id]['total_duration'] += turn.duration
            speakers[speaker_id]['segment_count'] += 1
            
            segments.append({
                'speaker_id': speaker_id,
                'start_time': turn.start,
                'end_time': turn.end,
                'duration': turn.duration
            })
        
        return {
            'speakers': list(speakers.values()),
            'segments': segments,
            'total_speakers': len(speakers)
        }
    
    def _basic_diarization(self, audio_path: str) -> dict:
        """Fallback to basic diarization from Yandex API"""
        # Existing implementation
        pass
```

### Configuration Management

```python
class ConfigurationManager:
    """Centralized configuration management for Phase 2"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(os.getenv('REDIS_URL'))
    
    def get_processing_config(self, user_id: str = None) -> dict:
        """Get processing configuration with user preferences"""
        base_config = {
            'stt_provider': 'yandex',  # yandex, whisper, combined
            'model_size': 'base',      # For Whisper: tiny, base, small, medium, large
            'language_detection': 'auto',
            'diarization_enabled': True,
            'enhanced_diarization': False,
            'post_processing': True,
            'quality_threshold': 0.8
        }
        
        if user_id:
            user_config = self.get_user_preferences(user_id)
            base_config.update(user_config)
        
        return base_config
    
    def get_user_preferences(self, user_id: str) -> dict:
        """Get user-specific preferences"""
        cache_key = f"user_prefs:{user_id}"
        cached_prefs = self.redis_client.get(cache_key)
        
        if cached_prefs:
            return json.loads(cached_prefs)
        
        # Fetch from database
        # Implementation depends on user management system
        return {}
    
    def update_feature_flags(self, flags: dict):
        """Update feature flags for A/B testing"""
        for flag, enabled in flags.items():
            self.redis_client.set(f"feature_flag:{flag}", str(enabled))
    
    def is_feature_enabled(self, feature: str, user_id: str = None) -> bool:
        """Check if feature is enabled for user"""
        flag_value = self.redis_client.get(f"feature_flag:{feature}")
        
        if flag_value is None:
            return False
        
        if flag_value.decode() == "True":
            return True
        
        # Implement A/B testing logic if needed
        if user_id and self._user_in_test_group(feature, user_id):
            return True
        
        return False
    
    def _user_in_test_group(self, feature: str, user_id: str) -> bool:
        """Determine if user is in test group for feature"""
        import hashlib
        hash_input = f"{feature}:{user_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        return (hash_value % 100) < 50  # 50% test group
```

### Migration Strategy

```python
class MigrationManager:
    """Handle migration from monolith to microservices"""
    
    def __init__(self):
        self.current_version = self.get_current_version()
    
    def migrate_to_microservices(self):
        """Step-by-step migration plan"""
        migration_steps = [
            self._extract_user_service,
            self._extract_processing_service,
            self._extract_storage_service,
            self._setup_api_gateway,
            self._migrate_data,
            self._validate_migration
        ]
        
        for step in migration_steps:
            try:
                logger.info(f"Executing migration step: {step.__name__}")
                step()
                self._mark_step_complete(step.__name__)
            except Exception as e:
                logger.error(f"Migration step failed: {step.__name__}: {str(e)}")
                raise
    
    def _extract_user_service(self):
        """Extract user management to separate service"""
        # 1. Deploy user service
        # 2. Migrate user data
        # 3. Update authentication flows
        # 4. Switch traffic gradually
        pass
    
    def _extract_processing_service(self):
        """Extract processing logic to separate service"""
        # 1. Deploy processing service
        # 2. Implement dual-write pattern
        # 3. Validate processing results
        # 4. Switch processing traffic
        pass
    
    def _setup_database_replication(self):
        """Setup database replication for zero-downtime migration"""
        # PostgreSQL setup with read replicas
        pass
    
    def rollback_migration(self, step: str):
        """Rollback migration to specific step"""
        # Implement rollback procedures
        pass
```

This comprehensive technical architecture provides a solid foundation for the KazRu-STT Pro MVP while establishing clear paths for future evolution. The architecture balances rapid development needs with production-ready scalability, ensuring the 2-3 day delivery timeline while maintaining code quality and system reliability.

The design emphasizes:
- **Simplicity for MVP**: Monolithic Flask application with minimal dependencies
- **Scalability foundation**: Redis queuing, Docker containerization, horizontal scaling readiness
- **Production readiness**: Comprehensive monitoring, security, error handling
- **Evolution path**: Clear migration strategy to microservices and enhanced AI capabilities

The architecture directly addresses all PRD requirements while providing the flexibility needed for Phase 2 enhancements including local processing capabilities and advanced diarization features.