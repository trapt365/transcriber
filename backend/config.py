import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Yandex SpeechKit Configuration
    YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY')
    YANDEX_FOLDER_ID = os.environ.get('YANDEX_FOLDER_ID')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH') or 524288000)  # 500MB
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE') or 524288000)  # 500MB
    ALLOWED_EXTENSIONS = set(
        os.environ.get('ALLOWED_EXTENSIONS', 'wav,mp3,m4a,flac,ogg').split(',')
    )
    
    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL
    
    # Audio Processing Configuration
    FFMPEG_PATH = os.environ.get('FFMPEG_PATH') or '/usr/bin/ffmpeg'
    MAX_AUDIO_DURATION = int(os.environ.get('MAX_AUDIO_DURATION') or 14400)  # 4 hours
    AUDIO_PROCESSING_TIMEOUT = int(os.environ.get('AUDIO_PROCESSING_TIMEOUT') or 3600)  # 1 hour
    
    # Security Configuration
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True').lower() == 'true'
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or SECRET_KEY
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Override for local development
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    
    # Development specific settings
    FLASK_ENV = 'development'
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Production specific settings
    FLASK_ENV = 'production'
    
    # Ensure critical environment variables are set
    if not os.environ.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY environment variable must be set in production")
    
    if not os.environ.get('YANDEX_API_KEY'):
        raise ValueError("YANDEX_API_KEY environment variable must be set in production")


class TestingConfig(Config):
    """Testing configuration."""
    
    DEBUG = True
    TESTING = True
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Testing specific settings
    WTF_CSRF_ENABLED = False
    REDIS_URL = 'redis://localhost:6379/1'  # Use different Redis DB for tests


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])