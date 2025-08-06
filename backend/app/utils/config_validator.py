"""Configuration validation utilities."""

import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """Validates application configuration and environment setup."""
    
    # Required environment variables for different environments
    REQUIRED_VARS = {
        'production': [
            'SECRET_KEY',
            'YANDEX_API_KEY',
            'YANDEX_FOLDER_ID',
            'DATABASE_URL',
            'REDIS_URL'
        ],
        'development': [
            'YANDEX_API_KEY',
            'YANDEX_FOLDER_ID'
        ],
        'testing': []
    }
    
    # Optional environment variables with defaults
    OPTIONAL_VARS = {
        'UPLOAD_FOLDER': 'uploads',
        'MAX_FILE_SIZE': '524288000',
        'ALLOWED_EXTENSIONS': 'wav,mp3,m4a,flac,ogg',
        'FFMPEG_PATH': '/usr/bin/ffmpeg',
        'MAX_AUDIO_DURATION': '14400',
        'AUDIO_PROCESSING_TIMEOUT': '3600',
        'LOG_LEVEL': 'INFO',
        'CORS_ORIGINS': '*'
    }
    
    def __init__(self, environment: str = 'development'):
        """
        Initialize configuration validator.
        
        Args:
            environment: Target environment (development, production, testing)
        """
        self.environment = environment
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> bool:
        """
        Validate all configuration aspects.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigValidationError: If critical validation fails
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Validate environment variables
        self._validate_environment_variables()
        
        # Validate file system paths
        self._validate_file_system()
        
        # Validate external dependencies
        self._validate_external_dependencies()
        
        # Validate Yandex API credentials
        self._validate_yandex_credentials()
        
        # Log results
        if self.warnings:
            for warning in self.warnings:
                logger.warning(f"Configuration warning: {warning}")
        
        if self.errors:
            error_msg = f"Configuration validation failed: {'; '.join(self.errors)}"
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)
        
        logger.info(f"Configuration validation passed for {self.environment} environment")
        return True
    
    def _validate_environment_variables(self) -> None:
        """Validate required and optional environment variables."""
        required_vars = self.REQUIRED_VARS.get(self.environment, [])
        
        # Check required variables
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                self.errors.append(f"Required environment variable {var} is missing")
            elif var == 'SECRET_KEY' and len(value) < 16:
                self.errors.append(f"SECRET_KEY must be at least 16 characters long")
        
        # Check optional variables and set defaults
        for var, default in self.OPTIONAL_VARS.items():
            if not os.environ.get(var):
                self.warnings.append(f"Optional environment variable {var} not set, using default: {default}")
    
    def _validate_file_system(self) -> None:
        """Validate file system paths and permissions."""
        # Check upload folder
        upload_folder = os.environ.get('UPLOAD_FOLDER', 'uploads')
        upload_path = Path(upload_folder)
        
        if not upload_path.exists():
            try:
                upload_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created upload directory: {upload_path}")
            except PermissionError:
                self.errors.append(f"Cannot create upload directory: {upload_path}")
        elif not upload_path.is_dir():
            self.errors.append(f"Upload path exists but is not a directory: {upload_path}")
        elif not os.access(upload_path, os.W_OK):
            self.errors.append(f"Upload directory is not writable: {upload_path}")
        
        # Check log directory
        log_file = os.environ.get('LOG_FILE', 'logs/app.log')
        log_path = Path(log_file).parent
        
        if not log_path.exists():
            try:
                log_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created log directory: {log_path}")
            except PermissionError:
                self.warnings.append(f"Cannot create log directory: {log_path}")
        elif not os.access(log_path, os.W_OK):
            self.warnings.append(f"Log directory is not writable: {log_path}")
    
    def _validate_external_dependencies(self) -> None:
        """Validate external tool dependencies."""
        # Check FFmpeg
        ffmpeg_path = os.environ.get('FFMPEG_PATH', '/usr/bin/ffmpeg')
        if not Path(ffmpeg_path).exists():
            # Try to find ffmpeg in PATH
            import shutil
            if not shutil.which('ffmpeg'):
                self.errors.append("FFmpeg not found. Please install FFmpeg or set FFMPEG_PATH")
            else:
                self.warnings.append(f"FFmpeg found in PATH, but FFMPEG_PATH points to {ffmpeg_path}")
        
        # Check Redis connectivity (optional check)
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            logger.debug("Redis connection successful")
        except ImportError:
            self.warnings.append("Redis package not installed")
        except Exception as exc:
            self.warnings.append(f"Redis connection failed: {exc}")
    
    def _validate_yandex_credentials(self) -> None:
        """Validate Yandex API credentials format."""
        api_key = os.environ.get('YANDEX_API_KEY')
        folder_id = os.environ.get('YANDEX_FOLDER_ID')
        
        if api_key:
            # Basic format validation for Yandex API key
            if len(api_key) < 20:
                self.errors.append("YANDEX_API_KEY appears to be too short")
            elif not api_key.replace('-', '').replace('_', '').isalnum():
                self.warnings.append("YANDEX_API_KEY format may be invalid")
        
        if folder_id:
            # Basic format validation for Yandex folder ID
            if len(folder_id) < 10:
                self.errors.append("YANDEX_FOLDER_ID appears to be too short")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get validation summary.
        
        Returns:
            Dictionary with validation results
        """
        return {
            'environment': self.environment,
            'valid': len(self.errors) == 0,
            'errors': self.errors.copy(),
            'warnings': self.warnings.copy(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


def validate_config(environment: Optional[str] = None) -> bool:
    """
    Convenience function to validate configuration.
    
    Args:
        environment: Target environment, defaults to FLASK_ENV
        
    Returns:
        True if configuration is valid
        
    Raises:
        ConfigValidationError: If validation fails
    """
    if not environment:
        environment = os.environ.get('FLASK_ENV', 'development')
    
    validator = ConfigValidator(environment)
    return validator.validate_all()


__all__ = ['ConfigValidator', 'ConfigValidationError', 'validate_config']