#!/usr/bin/env python3
"""Development environment setup script."""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent


def create_directories():
    """Create necessary directories."""
    dirs_to_create = [
        project_root / 'uploads',
        project_root / 'logs',
        project_root / 'temp'
    ]
    
    for directory in dirs_to_create:
        directory.mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")


def create_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text())
        logger.info("Created .env file from .env.example")
        logger.warning("Please update .env file with your actual configuration values")
    elif env_file.exists():
        logger.info(".env file already exists")
    else:
        logger.error(".env.example not found")


def check_dependencies():
    """Check for required system dependencies."""
    dependencies = {
        'redis-server': 'Redis server for Celery task queue',
        'ffmpeg': 'FFmpeg for audio processing'
    }
    
    missing_deps = []
    
    for dep, description in dependencies.items():
        if subprocess.run(['which', dep], capture_output=True).returncode != 0:
            missing_deps.append((dep, description))
    
    if missing_deps:
        logger.error("Missing system dependencies:")
        for dep, desc in missing_deps:
            logger.error(f"  - {dep}: {desc}")
        logger.error("Please install missing dependencies before proceeding")
        return False
    else:
        logger.info("All system dependencies found")
        return True


def init_database():
    """Initialize database."""
    try:
        # Add project root to Python path
        sys.path.insert(0, str(project_root))
        
        from backend.app import create_app
        from backend.extensions import db
        
        app, _ = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("Database initialized successfully")
            
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}")
        return False
    
    return True


def test_configuration():
    """Test configuration validation."""
    try:
        sys.path.insert(0, str(project_root))
        
        from backend.app.utils.config_validator import validate_config
        validate_config()
        logger.info("Configuration validation passed")
        return True
        
    except Exception as exc:
        logger.error(f"Configuration validation failed: {exc}")
        return False


def main():
    """Main setup function."""
    logger.info("Starting development environment setup...")
    
    # Create necessary directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    # Check system dependencies
    if not check_dependencies():
        logger.error("Setup failed due to missing dependencies")
        sys.exit(1)
    
    # Test configuration
    if not test_configuration():
        logger.warning("Configuration validation failed - please check your .env file")
    
    # Initialize database
    if not init_database():
        logger.error("Database initialization failed")
        sys.exit(1)
    
    logger.info("Development environment setup completed successfully!")
    logger.info("\nNext steps:")
    logger.info("1. Update .env file with your Yandex API credentials")
    logger.info("2. Start Redis server: redis-server")
    logger.info("3. Start Celery worker: python scripts/start_celery_worker.py")
    logger.info("4. Start Celery beat: python scripts/start_celery_beat.py")
    logger.info("5. Start Flask app: python backend/app.py")


if __name__ == '__main__':
    main()