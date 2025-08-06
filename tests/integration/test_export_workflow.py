"""Integration tests for export workflow."""

import json
import pytest
from unittest.mock import patch, Mock
from backend.app import create_app
from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.speaker import Speaker
from backend.app.models.segment import TranscriptSegment
from backend.app.models.enums import JobStatus, ExportFormat
from backend.app.services.export_service import TranscriptExportService
from backend.app.utils.exceptions import ExportError


class TestExportWorkflow:
    """Integration tests for the complete export workflow."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        app, _ = create_app()
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def sample_job_data(self):
        """Create sample job data."""
        job = Mock(spec=Job)
        job.job_id = 'test-job-123'
        job.original_filename = 'test-audio.mp3'
        job.status = JobStatus.COMPLETED.value
        job.duration = 120.5
        job.language = 'ru'  # Russian to test UTF-8
        job.created_at = None
        job.completed_at = None
        
        # Mock result
        result = Mock(spec=JobResult)
        result.formatted_transcript = "Привет, как дела? Хорошо, спасибо."
        result.raw_transcript = "Привет, как дела? Хорошо, спасибо."
        result.word_count = 5
        result.confidence_score = 0.95
        result.processing_duration = 30.0
        job.results = [result]
        
        # Mock speakers
        speaker1 = Mock(spec=Speaker)
        speaker1.speaker_id = 'spk1'
        speaker1.speaker_label = 'Speaker 1'
        speaker1.total_speech_time = 60.0
        speaker1.confidence_score = 0.92
        
        speaker2 = Mock(spec=Speaker)
        speaker2.speaker_id = 'spk2'
        speaker2.speaker_label = 'Speaker 2'
        speaker2.total_speech_time = 60.5
        speaker2.confidence_score = 0.88
        
        job.speakers = [speaker1, speaker2]
        
        # Mock segments
        segment1 = Mock(spec=TranscriptSegment)
        segment1.segment_order = 1
        segment1.start_time = 0.0
        segment1.end_time = 2.5
        segment1.duration = 2.5
        segment1.text = "Привет, как дела?"
        segment1.confidence_score = 0.95
        segment1.word_count = 3
        segment1.speaker = speaker1
        segment1.get_srt_format = Mock(return_value="1\n00:00:00,000 --> 00:00:02,500\nПривет, как дела?\n")
        segment1.get_vtt_format = Mock(return_value="00:00.000 --> 00:02.500\nПривет, как дела?\n")
        
        segment2 = Mock(spec=TranscriptSegment)
        segment2.segment_order = 2
        segment2.start_time = 3.0
        segment2.end_time = 5.2
        segment2.duration = 2.2
        segment2.text = "Хорошо, спасибо."
        segment2.confidence_score = 0.93
        segment2.word_count = 2
        segment2.speaker = speaker2
        segment2.get_srt_format = Mock(return_value="2\n00:00:03,000 --> 00:00:05,200\nХорошо, спасибо.\n")
        segment2.get_vtt_format = Mock(return_value="00:03.000 --> 00:05.200\nХорошо, спасибо.\n")
        
        job.segments = [segment1, segment2]
        
        return job

    def test_export_service_integration(self, sample_job_data):
        """Test export service with complete job data."""
        service = TranscriptExportService()
        
        # Test all supported formats
        formats = service.get_supported_formats()
        assert len(formats) == 5
        assert ExportFormat.JSON in formats
        assert ExportFormat.TXT in formats
        assert ExportFormat.SRT in formats
        assert ExportFormat.VTT in formats
        assert ExportFormat.CSV in formats
        
        # Test validation
        assert service.validate_export_data(sample_job_data) is True
        
        # Test JSON export
        json_content = service.export_transcript(sample_job_data, ExportFormat.JSON)
        json_data = json.loads(json_content)
        assert json_data['job_info']['job_id'] == 'test-job-123'
        assert json_data['transcript']['text'] == "Привет, как дела? Хорошо, спасибо."
        assert len(json_data['speakers']) == 2
        assert len(json_data['segments']) == 2
        
        # Test TXT export
        txt_content = service.export_transcript(sample_job_data, ExportFormat.TXT)
        assert 'test-audio.mp3' in txt_content
        assert 'test-job-123' in txt_content
        assert 'Привет, как дела?' in txt_content
        assert 'Speaker 1' in txt_content
        
        # Test SRT export
        srt_content = service.export_transcript(sample_job_data, ExportFormat.SRT)
        assert '1\n00:00:00,000 --> 00:00:02,500\nПривет, как дела?' in srt_content
        assert '2\n00:00:03,000 --> 00:00:05,200\nХорошо, спасибо.' in srt_content
        
        # Test VTT export
        vtt_content = service.export_transcript(sample_job_data, ExportFormat.VTT)
        assert 'WEBVTT' in vtt_content
        assert '00:00.000 --> 00:02.500\nПривет, как дела?' in vtt_content
        assert 'test-audio.mp3' in vtt_content
        
        # Test CSV export
        csv_content = service.export_transcript(sample_job_data, ExportFormat.CSV)
        lines = csv_content.strip().split('\n')
        assert len(lines) >= 3  # Header + 2 segments
        assert 'segment_order' in lines[0]
        assert 'spk1' in csv_content
        assert 'spk2' in csv_content

    def test_export_stats(self, sample_job_data):
        """Test export statistics generation."""
        service = TranscriptExportService()
        stats = service.get_export_stats(sample_job_data)
        
        assert stats['job_id'] == 'test-job-123'
        assert stats['word_count'] == 5
        assert stats['segment_count'] == 2
        assert stats['speaker_count'] == 2
        assert stats['can_export_timed'] is True
        assert stats['confidence_score'] == 0.95
        assert 'json' in stats['available_formats']
        assert 'srt' in stats['available_formats']

    def test_export_validation_failures(self):
        """Test export validation failure cases."""
        service = TranscriptExportService()
        
        # Test with None job
        with pytest.raises(ExportError, match="Job object is required"):
            service.validate_export_data(None)
        
        # Test with job without results
        job_no_results = Mock()
        job_no_results.results = []
        with pytest.raises(ExportError, match="Job has no transcription results"):
            service.validate_export_data(job_no_results)
        
        # Test with job without transcript content
        job_no_transcript = Mock()
        result = Mock()
        result.formatted_transcript = None
        result.raw_transcript = None
        job_no_transcript.results = [result]
        with pytest.raises(ExportError, match="Job has no transcript content"):
            service.validate_export_data(job_no_transcript)

    def test_srt_vtt_without_segments(self, sample_job_data):
        """Test SRT/VTT export without segment data."""
        service = TranscriptExportService()
        
        # Remove segments
        sample_job_data.segments = []
        
        # Should raise error for SRT
        with pytest.raises(ExportError, match="SRT export requires segmented transcript data"):
            service.export_transcript(sample_job_data, ExportFormat.SRT)
        
        # Should raise error for VTT
        with pytest.raises(ExportError, match="VTT export requires segmented transcript data"):
            service.export_transcript(sample_job_data, ExportFormat.VTT)
        
        # But TXT and JSON should still work
        txt_content = service.export_transcript(sample_job_data, ExportFormat.TXT)
        assert len(txt_content) > 0
        
        json_content = service.export_transcript(sample_job_data, ExportFormat.JSON)
        json_data = json.loads(json_content)
        assert len(json_data['segments']) == 0

    @patch('backend.app.routes.jobs.Job.query')
    def test_end_to_end_export_api(self, mock_query, client, sample_job_data):
        """Test complete end-to-end export API workflow."""
        # Setup mock
        mock_query.filter_by.return_value.first.return_value = sample_job_data
        
        # Test export formats endpoint
        response = client.get('/api/v1/jobs/test-job-123/export-formats')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'txt' in data['export_formats']['available']
        assert 'json' in data['export_formats']['available']
        
        # Test actual export for each format
        formats_to_test = ['txt', 'json', 'srt', 'vtt', 'csv']
        
        for format_name in formats_to_test:
            response = client.get(f'/api/v1/jobs/test-job-123/export/{format_name}')
            assert response.status_code == 200, f"Failed for format {format_name}"
            
            # Check headers
            assert 'charset=utf-8' in response.headers['Content-Type']
            assert 'attachment' in response.headers['Content-Disposition']
            assert f'.{format_name}' in response.headers['Content-Disposition']
            
            # Check content is not empty
            assert len(response.data) > 0
            
            # For text-based formats, check UTF-8 content
            if format_name in ['txt', 'json', 'srt', 'vtt', 'csv']:
                content = response.data.decode('utf-8')
                assert len(content) > 0

    def test_utf8_handling_cyrillic(self, sample_job_data):
        """Test proper UTF-8 handling with Cyrillic characters."""
        service = TranscriptExportService()
        
        # Export as JSON and verify Cyrillic characters are preserved
        json_content = service.export_transcript(sample_job_data, ExportFormat.JSON)
        json_data = json.loads(json_content)
        
        assert 'Привет' in json_data['transcript']['text']
        assert 'спасибо' in json_data['transcript']['text']
        
        # Test TXT format
        txt_content = service.export_transcript(sample_job_data, ExportFormat.TXT)
        assert 'Привет' in txt_content
        assert 'спасибо' in txt_content
        
        # Test that content can be properly encoded/decoded
        encoded = txt_content.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert decoded == txt_content

    def test_concurrent_exports(self, sample_job_data):
        """Test that multiple concurrent exports work correctly."""
        import threading
        import time
        
        service = TranscriptExportService()
        results = {}
        errors = {}
        
        def export_worker(format_type, worker_id):
            try:
                time.sleep(0.1)  # Small delay to encourage concurrency
                content = service.export_transcript(sample_job_data, format_type)
                results[worker_id] = content
            except Exception as e:
                errors[worker_id] = str(e)
        
        # Start multiple export threads
        threads = []
        formats = [ExportFormat.JSON, ExportFormat.TXT, ExportFormat.CSV]
        
        for i, fmt in enumerate(formats):
            thread = threading.Thread(target=export_worker, args=(fmt, f"worker_{i}"))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == len(formats)
        
        # Verify each result is different (different formats produce different content)
        contents = list(results.values())
        assert len(set(contents)) == len(contents), "All exports should be different"