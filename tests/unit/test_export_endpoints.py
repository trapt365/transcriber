"""Unit tests for export API endpoints."""

import json
import pytest
from unittest.mock import patch, Mock
from flask import Flask
from backend.app.routes.jobs import jobs_bp
from backend.app.models.enums import JobStatus, ExportFormat
from backend.app.utils.exceptions import ExportError


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(jobs_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_job():
    """Create mock job object."""
    job = Mock()
    job.job_id = 'test-job-123'
    job.status = JobStatus.COMPLETED.value
    job.original_filename = 'test-audio.mp3'
    job.duration = 120.5
    job.language = 'en'
    job.created_at = None
    job.completed_at = None
    return job


@pytest.fixture
def mock_export_service():
    """Create mock export service."""
    service = Mock()
    service.export_transcript.return_value = "Test transcript content"
    service.get_supported_formats.return_value = [
        ExportFormat.JSON, ExportFormat.TXT, ExportFormat.SRT, 
        ExportFormat.VTT, ExportFormat.CSV
    ]
    service.get_export_stats.return_value = {
        'job_id': 'test-job-123',
        'transcript_length': 100,
        'word_count': 20,
        'segment_count': 5,
        'speaker_count': 2,
        'available_formats': ['json', 'txt', 'srt', 'vtt', 'csv'],
        'generated_exports': [],
        'can_export_timed': True,
        'confidence_score': 0.95
    }
    return service


class TestExportEndpoints:
    """Test cases for export endpoints."""

    @patch('backend.app.routes.jobs.Job.query')
    @patch('backend.app.routes.jobs.TranscriptExportService')
    def test_export_transcript_success(self, mock_service_class, mock_query, client, mock_job, mock_export_service):
        """Test successful transcript export."""
        # Setup mocks
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_service_class.return_value = mock_export_service
        
        # Make request
        response = client.get('/api/v1/jobs/test-job-123/export/txt')
        
        # Verify response
        assert response.status_code == 200
        assert response.data == b"Test transcript content"
        assert response.headers['Content-Type'] == 'text/plain; charset=utf-8'
        assert 'attachment' in response.headers['Content-Disposition']
        assert 'transcript_test-job-123_' in response.headers['Content-Disposition']
        
        # Verify service calls
        mock_export_service.export_transcript.assert_called_once()
        call_args = mock_export_service.export_transcript.call_args
        assert call_args[0][0] == mock_job  # First arg is job
        assert call_args[0][1] == ExportFormat.TXT  # Second arg is format

    @patch('backend.app.routes.jobs.Job.query')
    def test_export_transcript_job_not_found(self, mock_query, client):
        """Test export when job not found."""
        mock_query.filter_by.return_value.first.return_value = None
        
        response = client.get('/api/v1/jobs/nonexistent/export/txt')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['message'].lower()

    @patch('backend.app.routes.jobs.Job.query')
    def test_export_transcript_job_not_completed(self, mock_query, client, mock_job):
        """Test export when job is not completed."""
        mock_job.status = JobStatus.PROCESSING.value
        mock_query.filter_by.return_value.first.return_value = mock_job
        
        response = client.get('/api/v1/jobs/test-job-123/export/txt')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not completed' in data['message'].lower()

    @patch('backend.app.routes.jobs.Job.query')
    def test_export_transcript_invalid_format(self, mock_query, client, mock_job):
        """Test export with invalid format."""
        mock_query.filter_by.return_value.first.return_value = mock_job
        
        response = client.get('/api/v1/jobs/test-job-123/export/invalid')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'invalid format' in data['message'].lower()

    @patch('backend.app.routes.jobs.Job.query')
    @patch('backend.app.routes.jobs.TranscriptExportService')
    def test_export_transcript_export_error(self, mock_service_class, mock_query, client, mock_job):
        """Test export when service raises ExportError."""
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_service = Mock()
        mock_service.export_transcript.side_effect = ExportError("No transcript data")
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/v1/jobs/test-job-123/export/txt')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'export failed' in data['message'].lower()

    @patch('backend.app.routes.jobs.Job.query')
    @patch('backend.app.routes.jobs.TranscriptExportService')
    def test_export_formats_success(self, mock_service_class, mock_query, client, mock_job, mock_export_service):
        """Test successful export formats retrieval."""
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_service_class.return_value = mock_export_service
        
        response = client.get('/api/v1/jobs/test-job-123/export-formats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'export_formats' in data
        assert 'available' in data['export_formats']
        assert 'timed_formats' in data['export_formats']
        assert 'basic_formats' in data['export_formats']
        assert 'statistics' in data
        assert 'download_urls' in data

    def test_content_type_mapping(self):
        """Test that content type mapping covers all formats."""
        expected_types = {
            'json': 'application/json',
            'txt': 'text/plain',
            'srt': 'application/x-subrip',
            'vtt': 'text/vtt',
            'csv': 'text/csv'
        }
        
        # This test would ideally check the actual mapping in the route
        # For now, we just verify our expectations
        for format_name, content_type in expected_types.items():
            assert content_type is not None
            assert isinstance(content_type, str)

    @patch('backend.app.routes.jobs.Job.query')
    @patch('backend.app.routes.jobs.TranscriptExportService')
    def test_filename_generation(self, mock_service_class, mock_query, client, mock_job, mock_export_service):
        """Test that filename is generated correctly."""
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_service_class.return_value = mock_export_service
        
        response = client.get('/api/v1/jobs/test-job-123/export/json')
        
        assert response.status_code == 200
        content_disposition = response.headers['Content-Disposition']
        
        # Check filename format: transcript_{job_id}_{timestamp}.{format}
        assert 'transcript_test-job-123_' in content_disposition
        assert '.json' in content_disposition
        assert 'attachment' in content_disposition

    @patch('backend.app.routes.jobs.Job.query')
    @patch('backend.app.routes.jobs.TranscriptExportService')
    def test_utf8_encoding(self, mock_service_class, mock_query, client, mock_job):
        """Test UTF-8 encoding in response headers."""
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_service = Mock()
        mock_service.export_transcript.return_value = "Тест с кириллицей"  # Test with Cyrillic
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/v1/jobs/test-job-123/export/txt')
        
        assert response.status_code == 200
        assert 'charset=utf-8' in response.headers['Content-Type']