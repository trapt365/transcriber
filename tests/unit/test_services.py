"""Unit tests for service classes."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from io import BytesIO

from backend.app.services.file_service import FileService
from backend.app.services.processing_service import (
    YandexProcessingService, MockProcessingService, create_processing_service
)
from backend.app.services.export_service import TranscriptExportService, create_export_service  
from backend.app.services.health_service import HealthService
from backend.app.utils.exceptions import (
    FileValidationError, FileSizeError, FileFormatError, 
    FileContentError, StorageError, ProcessingError, ExportError
)
from backend.app.models.enums import ExportFormat


class TestFileService:
    """Test FileService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.file_service = FileService(
            upload_folder=self.temp_dir,
            max_file_size=1024 * 1024  # 1MB for testing
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test FileService initialization."""
        assert self.file_service.upload_folder == Path(self.temp_dir)
        assert self.file_service.max_file_size == 1024 * 1024
        assert self.file_service.upload_folder.exists()
    
    def test_validate_file_empty_filename(self):
        """Test validation with empty filename."""
        file_obj = BytesIO(b"test data")
        
        with pytest.raises(FileValidationError, match="Filename cannot be empty"):
            self.file_service.validate_file(file_obj, "")
    
    def test_validate_file_no_extension(self):
        """Test validation with no file extension."""
        file_obj = BytesIO(b"test data")
        
        with pytest.raises(FileFormatError, match="File must have an extension"):
            self.file_service.validate_file(file_obj, "filename")
    
    def test_validate_file_unsupported_format(self):
        """Test validation with unsupported format."""
        file_obj = BytesIO(b"test data")
        
        with pytest.raises(FileFormatError, match="Unsupported file format"):
            self.file_service.validate_file(file_obj, "test.txt")
    
    def test_validate_file_empty_content(self):
        """Test validation with empty file."""
        file_obj = BytesIO(b"")
        
        with pytest.raises(FileValidationError, match="File cannot be empty"):
            self.file_service.validate_file(file_obj, "test.wav")
    
    def test_validate_file_too_large(self):
        """Test validation with oversized file."""
        large_data = b"x" * (2 * 1024 * 1024)  # 2MB
        file_obj = BytesIO(large_data)
        
        with pytest.raises(FileSizeError, match="exceeds maximum allowed size"):
            self.file_service.validate_file(file_obj, "test.wav")
    
    def test_validate_file_valid_wav(self):
        """Test validation with valid WAV file."""
        # Mock WAV file header
        wav_header = b'RIFF\x24\x08\x00\x00WAVE'
        file_obj = BytesIO(wav_header + b'\x00' * 100)
        
        metadata = self.file_service.validate_file(file_obj, "test.wav")
        
        assert metadata['original_filename'] == "test.wav"
        assert metadata['file_extension'] == ".wav"
        assert metadata['expected_mime_type'] == "audio/wav"
        assert metadata['file_size'] == len(wav_header) + 100
        assert 'file_hash' in metadata
        assert 'validated_at' in metadata
    
    def test_validate_file_content_wav_invalid(self):
        """Test content validation with invalid WAV header."""
        invalid_wav = b'INVALID_HEADER' + b'\x00' * 100
        file_obj = BytesIO(invalid_wav)
        
        with pytest.raises(FileContentError, match="does not match expected format"):
            self.file_service.validate_file(file_obj, "test.wav")
    
    def test_validate_file_content_mp3_valid(self):
        """Test content validation with valid MP3 header."""
        mp3_header = b'ID3\x03\x00\x00\x00'
        file_obj = BytesIO(mp3_header + b'\x00' * 100)
        
        metadata = self.file_service.validate_file(file_obj, "test.mp3")
        assert metadata['expected_mime_type'] == "audio/mpeg"
    
    def test_save_file_success(self):
        """Test successful file saving."""
        wav_header = b'RIFF\x24\x08\x00\x00WAVE'
        file_obj = BytesIO(wav_header + b'\x00' * 100)
        
        storage_info = self.file_service.save_file(file_obj, "test.wav", "test-job-id")
        
        assert storage_info['job_id'] == "test-job-id"
        assert storage_info['original_filename'] == "test.wav"
        assert 'filename' in storage_info
        assert 'file_path' in storage_info
        assert 'saved_at' in storage_info
        
        # Verify file was actually saved
        saved_path = Path(storage_info['file_path'])
        assert saved_path.exists()
        assert saved_path.stat().st_size == len(wav_header) + 100
    
    def test_save_file_generate_job_id(self):
        """Test file saving with auto-generated job ID."""
        wav_header = b'RIFF\x24\x08\x00\x00WAVE'
        file_obj = BytesIO(wav_header + b'\x00' * 50)
        
        storage_info = self.file_service.save_file(file_obj, "test.wav")
        
        assert 'job_id' in storage_info
        assert len(storage_info['job_id']) == 36  # UUID length
    
    def test_delete_file_success(self):
        """Test successful file deletion."""
        # Create a test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_file.write_text("test content")
        
        result = self.file_service.delete_file(str(test_file))
        
        assert result is True
        assert not test_file.exists()
    
    def test_delete_file_not_exists(self):
        """Test deletion of non-existent file."""
        non_existent = Path(self.temp_dir) / "does_not_exist.txt"
        
        result = self.file_service.delete_file(str(non_existent))
        
        assert result is False
    
    def test_delete_file_outside_upload_folder(self):
        """Test deletion with path outside upload folder."""
        outside_path = "/tmp/outside_file.txt"
        
        with pytest.raises(StorageError, match="outside upload folder"):
            self.file_service.delete_file(outside_path)
    
    def test_get_file_info_exists(self):
        """Test getting info for existing file."""
        test_file = Path(self.temp_dir) / "info_test.txt"
        test_file.write_text("test content")
        
        info = self.file_service.get_file_info(str(test_file))
        
        assert info is not None
        assert info['filename'] == "info_test.txt"
        assert info['file_size'] == 12  # len("test content")
        assert info['exists'] is True
        assert 'created_at' in info
        assert 'modified_at' in info
    
    def test_get_file_info_not_exists(self):
        """Test getting info for non-existent file."""
        non_existent = Path(self.temp_dir) / "does_not_exist.txt"
        
        info = self.file_service.get_file_info(str(non_existent))
        
        assert info is None
    
    def test_cleanup_expired_files(self):
        """Test cleanup of expired files."""
        # Create test files with different ages
        old_file = Path(self.temp_dir) / "old_file.txt"
        recent_file = Path(self.temp_dir) / "recent_file.txt"
        
        old_file.write_text("old content")
        recent_file.write_text("recent content")
        
        # Mock file modification times
        import time
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        recent_time = time.time() - (1 * 3600)  # 1 hour ago
        
        os.utime(old_file, (old_time, old_time))
        os.utime(recent_file, (recent_time, recent_time))
        
        # Run cleanup with 24 hour expiration
        stats = self.file_service.cleanup_expired_files(expiration_hours=24)
        
        assert stats['deleted_files'] == 1
        assert stats['deleted_size_bytes'] == 11  # len("old content")
        assert not old_file.exists()
        assert recent_file.exists()
    
    def test_get_storage_stats(self):
        """Test storage statistics."""
        # Create test files
        (Path(self.temp_dir) / "test1.wav").write_text("content1")
        (Path(self.temp_dir) / "test2.mp3").write_text("content2")
        
        stats = self.file_service.get_storage_stats()
        
        assert stats['upload_folder'] == str(self.file_service.upload_folder)
        assert stats['total_files'] == 2
        assert stats['total_size_bytes'] == 16  # 8 + 8
        assert '.wav' in stats['file_types']
        assert '.mp3' in stats['file_types']
        assert stats['file_types']['.wav']['count'] == 1
        assert stats['file_types']['.mp3']['count'] == 1


class TestProcessingService:
    """Test ProcessingService functionality."""
    
    def test_yandex_service_init_valid(self):
        """Test YandexProcessingService initialization with valid credentials."""
        service = YandexProcessingService(
            api_key="test_api_key",
            folder_id="test_folder_id"
        )
        
        assert service.api_key == "test_api_key"
        assert service.folder_id == "test_folder_id"
    
    def test_yandex_service_init_invalid(self):
        """Test YandexProcessingService initialization with invalid credentials."""
        with pytest.raises(ProcessingError, match="API key is required"):
            YandexProcessingService(api_key="", folder_id="test_folder_id")
        
        with pytest.raises(ProcessingError, match="folder ID is required"):
            YandexProcessingService(api_key="test_api_key", folder_id="")
    
    def test_yandex_validate_configuration_valid(self):
        """Test configuration validation with valid config."""
        service = YandexProcessingService("test_key", "test_folder")
        
        config = {
            'language': 'ru',
            'model': 'base'
        }
        
        assert service.validate_configuration(config) is True
    
    def test_yandex_validate_configuration_invalid(self):
        """Test configuration validation with invalid config."""
        service = YandexProcessingService("test_key", "test_folder")
        
        # Missing required field
        with pytest.raises(ProcessingError, match="Missing required configuration"):
            service.validate_configuration({'language': 'ru'})
        
        # Invalid language
        with pytest.raises(ProcessingError, match="Unsupported language"):
            service.validate_configuration({'language': 'invalid', 'model': 'base'})
        
        # Invalid model
        with pytest.raises(ProcessingError, match="Unsupported model"):
            service.validate_configuration({'language': 'ru', 'model': 'invalid'})
    
    def test_mock_service_process_audio(self):
        """Test MockProcessingService audio processing."""
        service = MockProcessingService()
        
        mock_job = Mock()
        mock_job.id = 1
        mock_job.original_filename = "test.wav"
        
        result = service.process_audio(mock_job)
        
        assert result.job_id == 1
        assert "test.wav" in result.raw_transcript
        assert result.confidence_score == 0.85
        assert result.processing_duration == 5.0
        assert result.api_response_metadata['provider'] == 'mock'
    
    def test_mock_service_get_status(self):
        """Test MockProcessingService status retrieval."""
        service = MockProcessingService()
        
        status = service.get_processing_status("test_job_id")
        
        assert status['job_id'] == "test_job_id"
        assert status['status'] == "completed"
        assert status['progress'] == 100
        assert status['provider'] == "mock"
    
    def test_mock_service_cancel(self):
        """Test MockProcessingService cancellation."""
        service = MockProcessingService()
        
        result = service.cancel_processing("test_job_id")
        assert result is True
    
    def test_create_processing_service_yandex(self):
        """Test factory function for Yandex service."""
        service = create_processing_service(
            provider="yandex",
            api_key="test_key",
            folder_id="test_folder"
        )
        
        assert isinstance(service, YandexProcessingService)
    
    def test_create_processing_service_mock(self):
        """Test factory function for mock service."""
        service = create_processing_service(provider="mock")
        
        assert isinstance(service, MockProcessingService)
    
    def test_create_processing_service_invalid(self):
        """Test factory function with invalid provider."""
        with pytest.raises(ProcessingError, match="Unsupported processing provider"):
            create_processing_service(provider="invalid")
        
        with pytest.raises(ProcessingError, match="requires 'api_key' and 'folder_id'"):
            create_processing_service(provider="yandex")


class TestExportService:
    """Test ExportService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_service = TranscriptExportService(export_folder=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_mock_job_with_results(self):
        """Create mock job with transcript results."""
        mock_job = Mock()
        mock_job.job_id = "test-job-123"
        mock_job.original_filename = "test.wav"
        mock_job.duration = 60.0
        mock_job.language = "ru"
        mock_job.created_at = Mock()
        mock_job.created_at.isoformat.return_value = "2023-01-01T00:00:00"
        mock_job.completed_at = Mock()
        mock_job.completed_at.isoformat.return_value = "2023-01-01T00:01:00"
        
        mock_result = Mock()
        mock_result.formatted_transcript = "Hello world test transcript"
        mock_result.raw_transcript = "hello world test transcript"
        mock_result.word_count = 4
        mock_result.confidence_score = 0.95
        mock_result.processing_duration = 10.5
        
        mock_job.results = [mock_result]
        mock_job.speakers = []
        mock_job.segments = []
        
        return mock_job
    
    def test_get_supported_formats(self):
        """Test getting supported export formats."""
        formats = self.export_service.get_supported_formats()
        
        assert ExportFormat.JSON in formats
        assert ExportFormat.TXT in formats
        assert ExportFormat.SRT in formats
        assert ExportFormat.VTT in formats
        assert ExportFormat.CSV in formats
    
    def test_validate_export_data_valid(self):
        """Test export data validation with valid job."""
        mock_job = self.create_mock_job_with_results()
        
        assert self.export_service.validate_export_data(mock_job) is True
    
    def test_validate_export_data_no_job(self):
        """Test export data validation with no job."""
        with pytest.raises(ExportError, match="Job object is required"):
            self.export_service.validate_export_data(None)
    
    def test_validate_export_data_no_results(self):
        """Test export data validation with no results."""
        mock_job = Mock()
        mock_job.results = []
        
        with pytest.raises(ExportError, match="Job has no transcription results"):
            self.export_service.validate_export_data(mock_job)
    
    def test_validate_export_data_no_transcript(self):
        """Test export data validation with no transcript content."""
        mock_job = Mock()
        mock_result = Mock()
        mock_result.formatted_transcript = None
        mock_result.raw_transcript = None
        mock_job.results = [mock_result]
        
        with pytest.raises(ExportError, match="Job has no transcript content"):
            self.export_service.validate_export_data(mock_job)
    
    def test_export_json(self):
        """Test JSON export."""
        mock_job = self.create_mock_job_with_results()
        
        json_content = self.export_service.export_transcript(mock_job, ExportFormat.JSON)
        
        assert json_content is not None
        assert "test-job-123" in json_content
        assert "Hello world test transcript" in json_content
        assert "test.wav" in json_content
        
        # Verify it's valid JSON
        import json
        data = json.loads(json_content)
        assert data['job_info']['job_id'] == "test-job-123"
        assert data['transcript']['text'] == "Hello world test transcript"
    
    def test_export_txt(self):
        """Test TXT export."""
        mock_job = self.create_mock_job_with_results()
        
        txt_content = self.export_service.export_transcript(mock_job, ExportFormat.TXT)
        
        assert "Transcript: test.wav" in txt_content
        assert "Job ID: test-job-123" in txt_content
        assert "Duration: 60.00 seconds" in txt_content
        assert "Hello world test transcript" in txt_content
        assert "Word count: 4" in txt_content
        assert "Confidence: 95.00%" in txt_content
    
    def test_export_csv(self):
        """Test CSV export."""
        mock_job = self.create_mock_job_with_results()
        
        csv_content = self.export_service.export_transcript(mock_job, ExportFormat.CSV)
        
        lines = csv_content.strip().split('\n')
        assert len(lines) >= 2  # Header + at least one data row
        
        header = lines[0]
        assert "segment_order" in header
        assert "start_time" in header
        assert "text" in header
        
        data_row = lines[1]
        assert "Hello world test transcript" in data_row
    
    def test_export_srt_without_segments(self):
        """Test SRT export without segments (should fail)."""
        mock_job = self.create_mock_job_with_results()
        
        with pytest.raises(ExportError, match="SRT export requires segmented transcript"):
            self.export_service.export_transcript(mock_job, ExportFormat.SRT)
    
    def test_export_vtt_without_segments(self):
        """Test VTT export without segments (should fail)."""
        mock_job = self.create_mock_job_with_results()
        
        with pytest.raises(ExportError, match="VTT export requires segmented transcript"):
            self.export_service.export_transcript(mock_job, ExportFormat.VTT)
    
    def test_export_unsupported_format(self):
        """Test export with unsupported format."""
        mock_job = self.create_mock_job_with_results()
        
        # Create a mock unsupported format
        unsupported_format = Mock()
        unsupported_format.value = "unsupported"
        
        with pytest.raises(ExportError, match="Unsupported export format"):
            self.export_service.export_transcript(mock_job, unsupported_format)
    
    def test_save_export(self):
        """Test saving export to file."""
        mock_job = self.create_mock_job_with_results()
        
        file_path = self.export_service.save_export(
            mock_job, 
            ExportFormat.JSON,
            content='{"test": "content"}'
        )
        
        assert file_path is not None
        assert Path(file_path).exists()
        assert Path(file_path).suffix == ".json"
        
        # Verify content
        with open(file_path, 'r') as f:
            content = f.read()
            assert content == '{"test": "content"}'
    
    def test_get_export_stats(self):
        """Test getting export statistics."""
        mock_job = self.create_mock_job_with_results()
        
        stats = self.export_service.get_export_stats(mock_job)
        
        assert stats['job_id'] == "test-job-123"
        assert stats['transcript_length'] == len("Hello world test transcript")
        assert stats['word_count'] == 4
        assert stats['segment_count'] == 0
        assert stats['speaker_count'] == 0
        assert stats['can_export_timed'] is False
        assert stats['confidence_score'] == 0.95
        assert 'available_formats' in stats
    
    def test_create_export_service(self):
        """Test export service factory function."""
        service = create_export_service(export_folder=self.temp_dir)
        
        assert isinstance(service, TranscriptExportService)
        assert service.export_folder == Path(self.temp_dir)


class TestHealthService:
    """Test HealthService functionality."""
    
    def test_health_service_init(self):
        """Test HealthService initialization."""
        service = HealthService(
            redis_url="redis://localhost:6379/0",
            upload_folder="/tmp/uploads"
        )
        
        assert service.redis_url == "redis://localhost:6379/0"
        assert service.upload_folder == Path("/tmp/uploads")
    
    @patch('backend.extensions.db')
    def test_check_database_healthy(self, mock_db):
        """Test database health check when healthy."""
        # Mock successful database query
        mock_db.engine.execute.return_value.scalar.return_value = 1
        mock_db.text.return_value = "SELECT 1"
        
        # Mock table inspection
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = [
            'jobs', 'job_results', 'speakers', 'transcript_segments', 'usage_stats'
        ]
        mock_db.inspect.return_value = mock_inspector
        
        service = HealthService()
        result = service.check_database()
        
        assert result['status'] == 'healthy'
        assert result['connection'] == 'ok'
        assert result['tables_count'] == 5
        assert result['missing_tables'] == []
    
    @patch('backend.extensions.db')
    def test_check_database_missing_tables(self, mock_db):
        """Test database health check with missing tables."""
        mock_db.engine.execute.return_value.scalar.return_value = 1
        mock_db.text.return_value = "SELECT 1"
        
        # Mock missing tables
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = ['jobs', 'job_results']  # Missing 3 tables
        mock_db.inspect.return_value = mock_inspector
        
        service = HealthService()
        result = service.check_database()
        
        assert result['status'] == 'degraded'
        assert len(result['missing_tables']) == 3
        assert 'speakers' in result['missing_tables']
    
    @patch('backend.extensions.db')
    def test_check_database_connection_failed(self, mock_db):
        """Test database health check when connection fails."""
        mock_db.engine.execute.side_effect = Exception("Connection failed")
        
        service = HealthService()
        result = service.check_database()
        
        assert result['status'] == 'unhealthy'
        assert result['connection'] == 'failed'
        assert 'Connection failed' in result['error']
    
    def test_check_redis_not_configured(self):
        """Test Redis health check when not configured."""
        service = HealthService()
        result = service.check_redis()
        
        assert result['status'] == 'not_configured'
    
    @patch('redis.from_url')
    def test_check_redis_healthy(self, mock_redis_from_url):
        """Test Redis health check when healthy."""
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = b'test_value'
        mock_redis_client.info.return_value = {
            'redis_version': '7.0.0',
            'used_memory_human': '1.5M',
            'connected_clients': 2
        }
        mock_redis_from_url.return_value = mock_redis_client
        
        service = HealthService(redis_url="redis://localhost:6379/0")
        result = service.check_redis()
        
        assert result['status'] == 'healthy'
        assert result['connection'] == 'ok'
        assert result['version'] == '7.0.0'
        assert result['used_memory'] == '1.5M'
        assert result['connected_clients'] == 2
    
    @patch('redis.from_url')
    def test_check_redis_connection_failed(self, mock_redis_from_url):
        """Test Redis health check when connection fails."""
        mock_redis_from_url.side_effect = Exception("Redis connection failed")
        
        service = HealthService(redis_url="redis://localhost:6379/0")
        result = service.check_redis()
        
        assert result['status'] == 'unhealthy'
        assert result['connection'] == 'failed'
        assert 'Redis connection failed' in result['error']
    
    def test_check_external_services(self):
        """Test external services check (not implemented)."""
        service = HealthService()
        result = service.check_external_services()
        
        assert result['status'] == 'not_implemented'
    
    @patch.object(HealthService, 'check_database')
    @patch.object(HealthService, 'check_redis')
    @patch.object(HealthService, 'check_filesystem')
    @patch.object(HealthService, 'check_external_services')
    def test_get_comprehensive_health_all_healthy(self, mock_external, mock_fs, mock_redis, mock_db):
        """Test comprehensive health check when all components are healthy."""
        mock_db.return_value = {'status': 'healthy'}
        mock_redis.return_value = {'status': 'not_configured'}
        mock_fs.return_value = {'status': 'healthy'}
        mock_external.return_value = {'status': 'not_implemented'}
        
        service = HealthService()
        result = service.get_comprehensive_health()
        
        assert result['status'] == 'healthy'
        assert result['service'] == 'transcriber'
        assert 'components' in result
        assert result['summary']['healthy_components'] == 2  # db and filesystem
        assert result['summary']['total_components'] == 2
    
    @patch.object(HealthService, 'check_database')
    @patch.object(HealthService, 'check_redis')
    @patch.object(HealthService, 'check_filesystem')
    def test_get_comprehensive_health_with_unhealthy(self, mock_fs, mock_redis, mock_db):
        """Test comprehensive health check with unhealthy components."""
        mock_db.return_value = {'status': 'unhealthy'}
        mock_redis.return_value = {'status': 'healthy'}
        mock_fs.return_value = {'status': 'degraded'}
        
        service = HealthService(redis_url="redis://localhost:6379/0")
        result = service.get_comprehensive_health()
        
        assert result['status'] == 'unhealthy'  # Overall status should be unhealthy
        assert result['summary']['unhealthy_components'] == 1
        assert result['summary']['degraded_components'] == 1
        assert result['summary']['healthy_components'] == 1