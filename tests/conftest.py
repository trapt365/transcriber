"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path

from backend.app import create_app
from backend.extensions import db


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_audio_files(temp_dir):
    """Create sample audio files for testing."""
    files = {}
    
    # Create mock WAV file
    wav_content = b'RIFF\x24\x08\x00\x00WAVE' + b'\x00' * 100
    wav_path = Path(temp_dir) / "sample.wav"
    wav_path.write_bytes(wav_content)
    files['wav'] = str(wav_path)
    
    # Create mock MP3 file
    mp3_content = b'ID3\x03\x00\x00\x00' + b'\x00' * 100  
    mp3_path = Path(temp_dir) / "sample.mp3"
    mp3_path.write_bytes(mp3_content)
    files['mp3'] = str(mp3_path)
    
    # Create invalid file
    invalid_path = Path(temp_dir) / "invalid.txt"
    invalid_path.write_text("Not an audio file")
    files['invalid'] = str(invalid_path)
    
    return files


@pytest.fixture
def mock_job_data():
    """Provide mock job data for tests."""
    return {
        'filename': 'test_audio.wav',
        'original_filename': 'test_audio.wav',
        'file_size': 1024000,
        'file_format': 'wav',
        'duration': 60.0,
        'sample_rate': 44100,
        'channels': 2,
        'language': 'ru',
        'enable_diarization': True
    }


@pytest.fixture
def mock_transcript_data():
    """Provide mock transcript data for tests."""
    return {
        'raw_transcript': 'This is a test transcript for testing purposes',
        'formatted_transcript': 'This is a test transcript for testing purposes.',
        'confidence_score': 0.95,
        'word_count': 9,
        'processing_duration': 15.5
    }


@pytest.fixture(scope='session')
def app_config():
    """Provide test application configuration."""
    return {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'UPLOAD_FOLDER': '/tmp/test_uploads',
        'MAX_CONTENT_LENGTH': 1024 * 1024,  # 1MB for testing
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'REDIS_URL': 'redis://localhost:6379/1'
    }


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test (requires external dependencies)"
    )
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow (takes more than 1 second)"
    )
    config.addinivalue_line(
        "markers", 
        "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", 
        "redis: mark test as requiring Redis"
    )


def pytest_runtest_setup(item):
    """Setup for individual test runs."""
    # Skip integration tests if external dependencies are not available
    if "integration" in item.keywords:
        # Add checks for external dependencies here if needed
        pass