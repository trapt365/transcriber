# Technical Assumptions

## Repository Structure: Monorepo
Single repository containing frontend, backend, и deployment configs. Enables rapid iteration, simplified dependency management, и streamlined CI/CD pipeline. Perfect для MVP development с single developer и 2-3 day timeline constraints.

## Service Architecture
**Monolith для MVP:** Single Python Flask/FastAPI application handling file upload, Yandex API integration, processing status tracking, и multi-format export. Architecture designed for horizontal scaling readiness но deployed as single service для simplicity.

**Evolution path:** Monolith → API Gateway + Microservices when scaling requirements demand it (Phase 2+).

## Testing Requirements
**Unit + Integration testing:** Comprehensive test coverage для core business logic, API integrations, и file processing workflows. Critical для production reliability given external API dependencies и complex audio processing pipeline.

**Testing priorities:**
- Unit tests for file validation, format conversion, export generation
- Integration tests for Yandex API interaction, error handling, retry logic  
- Manual testing protocols for audio quality validation и user workflow verification
- Load testing для concurrent upload scenarios

## Additional Technical Assumptions and Requests

**Language & Framework Stack:**
- **Backend:** Python 3.9+ с Flask/FastAPI для API development
- **Frontend:** HTML5/CSS3/Vanilla JavaScript с Bootstrap 5 для responsive UI
- **File Processing:** Python libraries для audio manipulation (pydub, librosa)
- **API Integration:** Yandex SpeechKit Python SDK + custom retry/error handling

**Database & Storage:**
- **MVP:** SQLite для processing metadata, job tracking, user sessions
- **File Storage:** Local filesystem с automatic cleanup после 24 hours
- **Production Evolution:** PostgreSQL + S3-compatible storage for scaling

**Infrastructure & Deployment:**
- **MVP Platform:** Heroku или DigitalOcean Droplet для simple deployment
- **Containerization:** Docker для consistent environments и easy scaling
- **CDN:** CloudFlare для static asset delivery и basic DDoS protection
- **Monitoring:** Basic logging + health checks, ready для observability tools

**Security & Compliance:**
- **File Encryption:** At-rest encryption для temporary audio storage
- **API Security:** Rate limiting, input validation, CSRF protection
- **Privacy:** Automatic file deletion, no persistent sensitive data storage
- **Authentication:** Session-based для MVP, готовность к OAuth integration

**Development & CI/CD:**
- **Version Control:** Git с GitHub для code management
- **CI/CD:** GitHub Actions для automated testing и deployment
- **Code Quality:** Black formatter, flake8 linting, pytest для testing
- **Documentation:** README, API docs, deployment guides

**Performance & Scalability Assumptions:**
- **Concurrent Processing:** Initial support для 5 parallel uploads
- **API Rate Limits:** Yandex SpeechKit quota management и cost tracking
- **Caching Strategy:** Result caching для identical file processing (future enhancement)
- **Auto-scaling:** Architecture ready для horizontal pod autoscaling

**Third-party Dependencies:**
- **Critical:** Yandex SpeechKit API (core STT functionality)
- **Optional:** pyannote.audio для enhanced diarization (Phase 2)
- **Supporting:** Redis для job queuing, Celery для async processing
- **Development:** pytest, black, flake8, pre-commit hooks
