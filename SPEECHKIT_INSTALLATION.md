# SpeechKit Installation Guide

## Background

Due to compilation issues with `grpcio-tools` (a dependency of `speechkit`), the main Docker container starts without the SpeechKit SDK to ensure reliable builds across different environments.

## Installing SpeechKit

### Option 1: Install in Running Container
```bash
# Start the container
docker compose up -d

# Install speechkit in the running container
docker compose exec app pip install -r requirements-speechkit.txt
```

### Option 2: Use Alternative Dockerfile (Advanced)
If you need SpeechKit from the start, use the alternative Dockerfile:
```bash
# Build with the alternative Dockerfile that handles grpcio compilation
docker compose -f docker-compose.dev.yml up --build
```

### Option 3: Local Development
For local development without Docker:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install main dependencies
pip install -r requirements.txt

# Install speechkit separately
pip install -r requirements-speechkit.txt
```

## Verifying Installation

Check if speechkit is working:
```python
import speechkit
print("SpeechKit installed successfully!")
```

## Troubleshooting

If you encounter compilation errors:
1. Try the Ubuntu-based alternative Dockerfile
2. Install speechkit manually after container startup
3. Use precompiled wheels if available for your platform

## Impact on Functionality

Without speechkit installed:
- ✅ Basic Flask app functionality works
- ✅ File upload and processing pipeline works
- ✅ Database operations work
- ❌ Yandex SpeechKit transcription will fail (but won't crash the app)

The application is designed to gracefully handle missing speechkit and will log appropriate error messages.