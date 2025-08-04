# Technology Stack Details

## Backend Framework
- **Flask 2.3+**: Lightweight web framework for MVP speed
- **Flask-SQLAlchemy 3.0+**: ORM for database operations
- **Flask-Migrate**: Database migration management
- **Flask-CORS**: Cross-origin resource sharing
- **Marshmallow 3.19+**: Request/response serialization

**Rationale**: Flask provides rapid development capability while maintaining production readiness. Its ecosystem supports all required features without over-engineering.

## Processing & Queue Management
- **Celery 5.3+**: Distributed task queue for concurrent processing
- **Redis 7.0+**: Message broker and caching layer
- **Kombu**: Celery message transport abstraction

**Rationale**: Celery+Redis provides robust async processing with minimal setup complexity, supporting the 5 concurrent user requirement.

## External APIs
- **Yandex SpeechKit Python SDK**: Primary STT service
- **requests 2.31+**: HTTP client with retry capabilities
- **urllib3**: Connection pooling and retry logic

**Rationale**: Yandex SpeechKit provides best-in-class Kazakh-Russian language support with built-in diarization.

## File Processing
- **pydub 0.25+**: Audio format conversion and manipulation
- **librosa 0.10+**: Audio analysis and preprocessing
- **FFmpeg**: Audio codec support (system dependency)

**Rationale**: Comprehensive audio processing capabilities for format standardization and optimization.

## Frontend Stack
- **HTML5**: Modern web standards with File API support
- **Bootstrap 5.3**: Responsive UI framework
- **Vanilla JavaScript ES6+**: No framework overhead for MVP
- **WebSocket/Server-Sent Events**: Real-time status updates

**Rationale**: Minimal dependencies, fast loading, maximum compatibility across browsers.

## Development & Testing
- **pytest 7.4+**: Testing framework
- **pytest-cov**: Coverage reporting
- **black**: Code formatting
- **flake8**: Linting
- **pre-commit**: Git hooks for code quality

## Containerization & Deployment
- **Docker 24+**: Containerization
- **Docker Compose**: Multi-container orchestration
- **nginx**: Reverse proxy and static file serving
- **gunicorn**: WSGI HTTP server
