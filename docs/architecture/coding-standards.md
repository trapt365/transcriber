# Coding Standards

## Python Code Standards

### Code Formatting
- **Black**: Automatic code formatting with line length of 88 characters
- **isort**: Import sorting and organization
- **flake8**: Linting with E203, W503 exceptions for Black compatibility

### Code Style Guidelines

#### Naming Conventions
```python
# Variables and functions: snake_case
user_id = "12345"
def process_audio_file():
    pass

# Classes: PascalCase
class AudioProcessor:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 500 * 1024 * 1024
API_TIMEOUT = 300

# Private methods: leading underscore
def _internal_helper(self):
    pass
```

#### Type Hints
```python
from typing import Optional, List, Dict, Union
from datetime import datetime

def process_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Process audio transcription job
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Processing result dictionary or None if failed
    """
    pass

class JobResult:
    def __init__(self, job_id: str, transcript: str, 
                 confidence: float) -> None:
        self.job_id = job_id
        self.transcript = transcript
        self.confidence = confidence
```

#### Error Handling
```python
# Custom exceptions hierarchy
class TranscriberError(Exception):
    """Base exception for transcriber application"""
    pass

class FileValidationError(TranscriberError):
    """Raised when file validation fails"""
    pass

class ProcessingError(TranscriberError):
    """Raised when processing fails"""
    pass

# Error handling pattern
def upload_file(file) -> str:
    try:
        validate_file(file)
        job_id = create_job(file)
        return job_id
    except FileValidationError as e:
        logger.error(f"File validation failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise ProcessingError("Failed to process upload")
```

#### Logging Standards
```python
import logging

logger = logging.getLogger(__name__)

# Log levels usage:
# DEBUG: Detailed diagnostic info
# INFO: General application flow
# WARNING: Recoverable problems
# ERROR: Serious problems
# CRITICAL: Application may crash

def process_audio(job_id: str):
    logger.info(f"Starting audio processing for job {job_id}")
    
    try:
        result = call_external_api()
        logger.debug(f"API response received: {len(result)} bytes")
        
    except APITimeout:
        logger.warning(f"API timeout for job {job_id}, retrying...")
        
    except APIError as e:
        logger.error(f"API error for job {job_id}: {str(e)}")
        raise ProcessingError("External API failed")
```

## Flask Application Standards

### Route Organization
```python
# Group related routes in blueprints
from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_v1.route('/upload', methods=['POST'])
def upload_file():
    pass

@api_v1.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    pass
```

### Request/Response Standards
```python
from marshmallow import Schema, fields, validate

# Input validation schemas
class FileUploadSchema(Schema):
    metadata = fields.Dict(missing={})

# Response schemas
class JobStatusSchema(Schema):
    job_id = fields.Str(required=True)
    status = fields.Str(required=True, 
                       validate=validate.OneOf(['uploaded', 'processing', 
                                               'completed', 'failed']))
    progress = fields.Int(validate=validate.Range(min=0, max=100))
    created_at = fields.DateTime(required=True)
    error_message = fields.Str(allow_none=True)

# Usage in routes
@api_v1.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    job = Job.query.filter_by(job_id=job_id).first_or_404()
    schema = JobStatusSchema()
    return jsonify(schema.dump(job))
```

### Database Standards
```python
# Model definitions
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False, 
                      default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='uploaded')
    created_at = db.Column(db.DateTime, nullable=False, 
                          default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Job {self.job_id}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'job_id': self.job_id,
            'filename': self.filename,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
```

## Testing Standards

### Test Organization
```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/
│   ├── test_api.py
│   └── test_processing.py
└── fixtures/
    ├── sample_audio.wav
    └── test_data.json
```

### Test Naming and Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestJobProcessing:
    """Test job processing functionality"""
    
    def test_process_job_success(self, sample_job):
        """Test successful job processing"""
        # Arrange
        processor = AudioProcessor()
        
        # Act
        result = processor.process(sample_job)
        
        # Assert
        assert result.status == 'completed'
        assert result.transcript is not None
    
    def test_process_job_invalid_file(self):
        """Test job processing with invalid file"""
        # Arrange
        processor = AudioProcessor()
        invalid_job = Job(filename="invalid.txt")
        
        # Act & Assert
        with pytest.raises(FileValidationError):
            processor.process(invalid_job)
    
    @patch('app.services.yandex_client.transcribe')
    def test_process_job_api_failure(self, mock_transcribe, sample_job):
        """Test job processing when API fails"""
        # Arrange
        mock_transcribe.side_effect = APIError("Service unavailable")
        processor = AudioProcessor()
        
        # Act & Assert
        with pytest.raises(ProcessingError):
            processor.process(sample_job)

# Fixtures
@pytest.fixture
def sample_job():
    """Provide sample job for testing"""
    return Job(
        job_id="test-job-123",
        filename="sample.wav",
        file_path="/tmp/sample.wav"
    )
```

## Security Standards

### Input Validation
```python
import os
from werkzeug.utils import secure_filename

def validate_and_save_file(file, job_id: str) -> str:
    """Secure file upload handling"""
    # Validate filename
    if not file.filename:
        raise FileValidationError("No filename provided")
    
    filename = secure_filename(file.filename)
    if not filename:
        raise FileValidationError("Invalid filename")
    
    # Validate extension
    if not allowed_file(filename):
        raise FileValidationError("File type not allowed")
    
    # Generate secure path
    upload_dir = app.config['UPLOAD_FOLDER']
    secure_name = f"{job_id}_{int(time.time())}_{filename}"
    file_path = os.path.join(upload_dir, secure_name)
    
    # Ensure path is within upload directory
    if not os.path.abspath(file_path).startswith(os.path.abspath(upload_dir)):
        raise FileValidationError("Invalid file path")
    
    return file_path
```

### Environment Variables
```python
import os
from typing import Optional

def get_required_env(key: str) -> str:
    """Get required environment variable"""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value

def get_optional_env(key: str, default: str = None) -> Optional[str]:
    """Get optional environment variable"""
    return os.getenv(key, default)

# Usage
YANDEX_API_KEY = get_required_env('YANDEX_API_KEY')
MAX_FILE_SIZE = int(get_optional_env('MAX_FILE_SIZE', '524288000'))
```

## Documentation Standards

### Docstring Format (Google Style)
```python
def transcribe_audio(audio_path: str, config: dict) -> dict:
    """Transcribe audio file using configured STT provider.
    
    Args:
        audio_path: Path to audio file to transcribe
        config: Configuration dictionary with processing options
            - language: Target language code (default: 'auto')
            - model: Model size for processing (default: 'base')
            - enable_diarization: Enable speaker separation (default: True)
    
    Returns:
        Dictionary containing transcription results:
            - transcript: Full text transcript
            - speakers: List of identified speakers
            - segments: List of timestamped segments
            - confidence: Overall confidence score
    
    Raises:
        FileNotFoundError: If audio file doesn't exist
        ProcessingError: If transcription fails
        
    Example:
        >>> config = {'language': 'ru', 'enable_diarization': True}
        >>> result = transcribe_audio('/path/to/audio.wav', config)
        >>> print(result['transcript'])
    """
    pass
```

### README Structure
```markdown
# Project Title

Brief description of what the project does.

## Features

- Feature 1
- Feature 2

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional)

### Installation
```bash
pip install -r requirements.txt
```

### Usage
```bash
python app.py
```

## API Documentation

### Endpoints
- `POST /api/v1/upload` - Upload audio file
- `GET /api/v1/jobs/{id}` - Get job status

## Development

### Setup
```bash
pip install -r requirements-dev.txt
pre-commit install
```

### Testing
```bash
pytest tests/
```

### Linting
```bash
flake8 app/ tests/
black app/ tests/
```
```

## Git Standards

### Commit Messages
```
feat: add audio file validation
fix: resolve timeout issue in Yandex API calls
docs: update API documentation
test: add unit tests for job processing
refactor: extract file handling to separate service
style: format code with black
chore: update dependencies
```

### Branch Naming
- `feature/audio-processing`
- `bugfix/timeout-handling`
- `hotfix/security-patch`
- `release/v1.2.0`

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## Code Review Checklist

### General
- [ ] Code follows established patterns
- [ ] No hardcoded secrets or credentials
- [ ] Error handling is appropriate
- [ ] Logging is adequate but not excessive

### Security
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] File upload security measures
- [ ] Authentication/authorization checks

### Performance
- [ ] Database queries are optimized
- [ ] No N+1 query problems
- [ ] Appropriate caching implemented
- [ ] Resource cleanup (files, connections)

### Testing
- [ ] Unit tests cover new functionality
- [ ] Integration tests for API changes
- [ ] Test data doesn't contain real PII
- [ ] Tests are deterministic

### Documentation
- [ ] Code is self-documenting
- [ ] Complex logic has comments
- [ ] API changes documented
- [ ] README updated if needed