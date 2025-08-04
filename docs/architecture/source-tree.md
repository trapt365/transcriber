# Source Tree Structure

## Project Root Structure

```
transcriber/
├── README.md                    # Project overview and setup
├── CONTRIBUTING.md             # Contribution guidelines
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── setup.cfg                   # Tool configurations (flake8, mypy)
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore patterns
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── Dockerfile                 # Production container image
├── Dockerfile.dev             # Development container image
├── docker-compose.yml         # Production docker services
├── docker-compose.dev.yml     # Development docker services
├── app.py                     # Application entry point
├── config.py                  # Application configuration
└── wsgi.py                    # WSGI entry point for production
```

## Backend Application Structure

```
backend/
├── __init__.py                # Package initialization
├── app.py                     # Flask application factory
├── config.py                  # Configuration management
├── extensions.py              # Flask extensions initialization
└── app/
    ├── __init__.py            # App package init
    ├── models/                # Database models
    │   ├── __init__.py
    │   ├── job.py            # Job model and relationships
    │   ├── result.py         # Processing results model
    │   ├── speaker.py        # Speaker information model
    │   └── usage.py          # Usage statistics model
    ├── routes/                # API route handlers
    │   ├── __init__.py
    │   ├── upload.py         # File upload endpoints
    │   ├── jobs.py           # Job management endpoints
    │   ├── export.py         # Export format endpoints
    │   └── system.py         # Health check and status
    ├── services/              # Business logic services
    │   ├── __init__.py
    │   ├── audio_processor.py # Audio processing service
    │   ├── file_manager.py   # File handling service
    │   ├── yandex_client.py  # Yandex API integration
    │   ├── export_service.py # Export format generation
    │   └── cleanup_service.py # File cleanup automation
    ├── utils/                 # Utility functions
    │   ├── __init__.py
    │   ├── validators.py     # Input validation functions
    │   ├── security.py       # Security utilities
    │   ├── formatters.py     # Data formatting utilities
    │   └── exceptions.py     # Custom exception classes
    ├── schemas/               # Request/response schemas
    │   ├── __init__.py
    │   ├── upload.py         # Upload request schemas
    │   ├── job.py            # Job response schemas
    │   └── export.py         # Export format schemas
    └── tasks/                 # Celery task definitions
        ├── __init__.py
        ├── processing.py     # Audio processing tasks
        ├── cleanup.py        # Cleanup tasks
        └── export.py         # Export generation tasks
```

## Frontend Structure

```
frontend/
├── static/                    # Static assets
│   ├── css/
│   │   ├── main.css          # Main stylesheet
│   │   ├── upload.css        # Upload interface styles
│   │   └── results.css       # Results display styles
│   ├── js/
│   │   ├── main.js           # Core JavaScript functionality
│   │   ├── upload.js         # File upload handling
│   │   ├── status.js         # Status polling and updates
│   │   ├── export.js         # Export functionality
│   │   └── utils.js          # Utility functions
│   ├── images/
│   │   ├── logo.png
│   │   ├── icons/
│   │   └── backgrounds/
│   └── fonts/                # Custom fonts (if any)
└── templates/                # Jinja2 templates
    ├── base.html             # Base template with common elements
    ├── index.html            # Main upload page
    ├── status.html           # Job status page
    ├── results.html          # Results display page
    ├── error.html            # Error page template
    └── partials/             # Reusable template components
        ├── header.html
        ├── footer.html
        ├── upload_form.html
        └── status_card.html
```

## Documentation Structure

```
docs/
├── README.md                  # Documentation index
├── architecture.md           # Complete technical architecture
├── brief.md                  # Project brief and requirements
├── prd.md                    # Product requirements document
├── architecture/             # Detailed architecture documents
│   ├── index.md
│   ├── table-of-contents.md
│   ├── system-architecture-overview.md
│   ├── technology-stack-details.md
│   ├── database-design.md
│   ├── api-architecture.md
│   ├── file-processing-pipeline.md
│   ├── deployment-architecture.md
│   ├── security-architecture.md
│   ├── monitoring-observability.md
│   ├── scalability-plan.md
│   ├── phase-2-evolution-path.md
│   ├── coding-standards.md    # Development standards
│   ├── tech-stack.md         # Technology choices
│   └── source-tree.md        # This file
├── prd/                      # PRD breakdown
│   ├── index.md
│   ├── goals-and-background-context.md
│   ├── requirements.md
│   ├── technical-assumptions.md
│   ├── user-interface-design-goals.md
│   ├── epic-list.md
│   ├── epic-1-foundation-core-processing-infrastructure.md
│   ├── epic-2-multi-format-export-user-experience-enhancement.md
│   ├── epic-3-production-readiness-scalability-foundation.md
│   ├── next-steps.md
│   └── checklist-results-report.md
└── stories/                  # User stories breakdown
    ├── 1.1.project-setup-dev-environment.md
    └── 1.2.database-models-core-services-architecture.md
```

## Configuration Structure

```
config/
├── development.py            # Development environment config
├── production.py             # Production environment config
├── testing.py               # Test environment config
├── nginx/
│   ├── nginx.conf           # Nginx configuration
│   └── ssl/                 # SSL certificates
├── docker/
│   ├── web.dockerfile       # Web service container
│   ├── worker.dockerfile    # Worker service container
│   └── nginx.dockerfile     # Nginx container
└── deployment/
    ├── docker-swarm.yml     # Docker Swarm stack file
    ├── kubernetes/          # Kubernetes manifests (Phase 2)
    └── terraform/           # Infrastructure as Code (Phase 2)
```

## Testing Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_models.py       # Model tests
│   ├── test_services.py     # Service layer tests
│   ├── test_utils.py        # Utility function tests
│   ├── test_validators.py   # Validation tests
│   └── test_tasks.py        # Celery task tests
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_api.py          # API endpoint tests
│   ├── test_processing.py   # End-to-end processing tests
│   ├── test_database.py     # Database integration tests
│   └── test_external_apis.py # External service tests
├── fixtures/                # Test data and mock files
│   ├── sample_audio.wav     # Test audio file
│   ├── test_responses.json  # Mock API responses
│   └── test_data.sql        # Test database data
└── performance/             # Performance tests (optional)
    ├── test_load.py         # Load testing
    └── test_stress.py       # Stress testing
```

## Data Structure

```
data/
├── uploads/                 # Uploaded audio files (temporary)
│   └── .gitkeep
├── exports/                 # Generated export files
│   └── .gitkeep
├── database/               # Database files (SQLite)
│   ├── app.db             # Main application database
│   └── migrations/        # Database migration files
│       ├── versions/
│       └── alembic.ini
├── logs/                   # Application logs
│   ├── app.log
│   ├── celery.log
│   └── nginx.log
├── cache/                  # Application cache files
│   └── .gitkeep
└── backups/               # Database and file backups
    ├── daily/
    ├── weekly/
    └── monthly/
```

## Scripts Structure

```
scripts/
├── setup.sh               # Initial project setup
├── deploy.sh              # Deployment script
├── backup.sh              # Backup script
├── restore.sh             # Restore script
├── test.sh                # Test runner script
├── lint.sh                # Code linting script
├── migration.py           # Database migration utility
└── cleanup.py             # Cleanup utility script
```

## Environment Configuration Files

```
.env.development           # Development environment variables
.env.production           # Production environment variables
.env.testing              # Testing environment variables
.env.example              # Template for environment setup
```

## CI/CD Structure

```
.github/
└── workflows/
    ├── test.yml           # Test workflow
    ├── deploy.yml         # Deployment workflow
    ├── security.yml       # Security scanning
    └── docs.yml           # Documentation updates
```

## Key File Purposes

### Application Entry Points
- **app.py**: Main Flask application factory and configuration
- **wsgi.py**: WSGI entry point for production deployment
- **config.py**: Centralized configuration management

### Core Business Logic
- **models/**: SQLAlchemy models defining data structure
- **services/**: Business logic abstracted from route handlers
- **tasks/**: Celery tasks for asynchronous processing
- **utils/**: Reusable utility functions and helpers

### API Layer
- **routes/**: Flask route handlers organized by functionality
- **schemas/**: Marshmallow schemas for request/response validation

### Frontend Assets
- **templates/**: Jinja2 HTML templates
- **static/**: CSS, JavaScript, images, and other assets

### Testing Infrastructure
- **conftest.py**: Shared pytest fixtures and configuration
- **unit/**: Fast, isolated unit tests
- **integration/**: Full-stack integration tests
- **fixtures/**: Test data and mock objects

## File Naming Conventions

### Python Files
- **Models**: Singular nouns (e.g., `job.py`, `user.py`)
- **Services**: Descriptive names with `_service.py` suffix
- **Routes**: Plural nouns matching resource names (e.g., `jobs.py`)
- **Tests**: `test_` prefix matching the module being tested
- **Tasks**: Functional names describing the task purpose

### Template Files
- **Base templates**: Descriptive names (e.g., `base.html`)
- **Page templates**: Match route names (e.g., `upload.html`)
- **Partials**: Underscore prefix (e.g., `_header.html`)

### Static Assets
- **CSS**: Kebab-case names (e.g., `main-style.css`)
- **JavaScript**: Camel-case or kebab-case (e.g., `fileUpload.js`)
- **Images**: Descriptive names with appropriate extensions

## Import Organization

### Import Order (per isort configuration)
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
import json
from datetime import datetime
from typing import Optional, List

# Third-party
from flask import Flask, request, jsonify
from sqlalchemy import Column, String, DateTime
from celery import Celery

# Local application
from app.models.job import Job
from app.services.audio_processor import AudioProcessor
from app.utils.validators import validate_file
```

## Directory Permissions and Security

### File Permissions
- **Configuration files**: 600 (owner read/write only)
- **Log files**: 644 (owner write, group/other read)
- **Upload directories**: 700 (owner access only)
- **Static assets**: 644 (readable by web server)

### Directory Structure Security
- **Uploads**: Outside web root, restricted access
- **Logs**: Restricted access, log rotation enabled
- **Database**: Protected directory, backup encryption
- **Configuration**: Version controlled templates only

This source tree structure supports rapid development while maintaining clear separation of concerns and providing a foundation for future scaling and microservices migration.