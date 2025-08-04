import os
import pytest
from backend.config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, get_config


class TestConfig:
    """Test configuration classes."""
    
    def test_base_config_defaults(self):
        """Test base configuration defaults."""
        config = Config()
        assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False
        assert config.MAX_CONTENT_LENGTH == 104857600  # 100MB
        assert 'wav' in config.ALLOWED_EXTENSIONS
        assert 'mp3' in config.ALLOWED_EXTENSIONS
    
    def test_development_config(self):
        """Test development configuration."""
        config = DevelopmentConfig()
        assert config.DEBUG is True
        assert config.TESTING is False
        assert 'dev.db' in config.SQLALCHEMY_DATABASE_URI
    
    def test_production_config_without_secrets(self):
        """Test production config validation without required secrets."""
        # Clear environment variables
        old_secret = os.environ.get('SECRET_KEY')
        old_yandex = os.environ.get('YANDEX_API_KEY')
        
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        if 'YANDEX_API_KEY' in os.environ:
            del os.environ['YANDEX_API_KEY']
        
        try:
            with pytest.raises(ValueError, match="SECRET_KEY environment variable must be set"):
                ProductionConfig()
        finally:
            # Restore environment variables
            if old_secret:
                os.environ['SECRET_KEY'] = old_secret
            if old_yandex:
                os.environ['YANDEX_API_KEY'] = old_yandex
    
    def test_testing_config(self):
        """Test testing configuration."""
        config = TestingConfig()
        assert config.DEBUG is True
        assert config.TESTING is True
        assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'
        assert config.WTF_CSRF_ENABLED is False
    
    def test_get_config_default(self):
        """Test get_config returns default configuration."""
        # Clear FLASK_ENV if set
        old_env = os.environ.get('FLASK_ENV')
        if 'FLASK_ENV' in os.environ:
            del os.environ['FLASK_ENV']
        
        try:
            config = get_config()
            assert config == DevelopmentConfig
        finally:
            if old_env:
                os.environ['FLASK_ENV'] = old_env
    
    def test_get_config_by_environment(self):
        """Test get_config returns correct config for environment."""
        old_env = os.environ.get('FLASK_ENV')
        
        try:
            os.environ['FLASK_ENV'] = 'testing'
            config = get_config()
            assert config == TestingConfig
            
            os.environ['FLASK_ENV'] = 'development'
            config = get_config()
            assert config == DevelopmentConfig
        finally:
            if old_env:
                os.environ['FLASK_ENV'] = old_env
            elif 'FLASK_ENV' in os.environ:
                del os.environ['FLASK_ENV']