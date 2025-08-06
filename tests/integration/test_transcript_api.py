"""Integration tests for transcript API endpoint."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from backend.app import create_app
from backend.app.models import Job, JobResult, Speaker, TranscriptSegment
from backend.app.models.enums import JobStatus
from backend.extensions import db


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app(testing=True)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_job(app):
    """Create a sample completed job with transcript data."""
    with app.app_context():
        # Create job
        job = Job(
            job_id='test-job-123',
            filename='test_audio.mp3',
            original_filename='test_audio.mp3',
            file_size=1024,
            file_format='mp3',
            status=JobStatus.COMPLETED.value,
            language='ru-RU',
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.session.add(job)
        db.session.flush()  # Get ID
        
        # Create job result
        job_result = JobResult(
            job_id=job.id,
            raw_transcript='Test raw transcript',
            confidence_score=0.85,
            word_count=50,
            processing_duration=45.5
        )
        db.session.add(job_result)
        
        # Create speakers
        speaker1 = Speaker(
            job_id=job.id,
            speaker_id='1',
            speaker_label='Alice',
            total_speech_time=30.5,
            segment_count=3
        )
        speaker2 = Speaker(
            job_id=job.id,
            speaker_id='2',
            speaker_label=None,  # Test default labeling
            total_speech_time=15.0,
            segment_count=2
        )
        db.session.add_all([speaker1, speaker2])
        db.session.flush()  # Get IDs
        
        # Create transcript segments
        segments = [
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=1,
                start_time=0.0,
                end_time=5.5,
                text='Привет всем, добро пожаловать на встречу',
                confidence_score=0.92
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=2,
                start_time=5.5,
                end_time=12.0,
                text='Сегодня мы обсудим важные вопросы',
                confidence_score=0.88
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker2.id,
                segment_order=3,
                start_time=13.0,
                end_time=18.5,
                text='Спасибо за приглашение',
                confidence_score=0.75
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker1.id,
                segment_order=4,
                start_time=19.0,
                end_time=25.0,
                text='Давайте начнем с первого пункта повестки дня',
                confidence_score=0.90
            ),
            TranscriptSegment(
                job_id=job.id,
                speaker_id=speaker2.id,
                segment_order=5,
                start_time=25.0,
                end_time=32.0,
                text='Қазақша мәтін тестісі үшін',
                confidence_score=0.80
            )
        ]
        db.session.add_all(segments)
        db.session.commit()
        
        return job


@pytest.fixture
def incomplete_job(app):
    """Create a job without transcript data."""
    with app.app_context():
        job = Job(
            job_id='incomplete-job-456',
            filename='incomplete.mp3',
            original_filename='incomplete.mp3',
            file_size=512,
            file_format='mp3',
            status=JobStatus.COMPLETED.value,
            language='en-US'
        )
        db.session.add(job)
        db.session.commit()
        
        return job


@pytest.fixture
def processing_job(app):
    """Create a job that's still processing."""
    with app.app_context():
        job = Job(
            job_id='processing-job-789',
            filename='processing.mp3',
            original_filename='processing.mp3',
            file_size=2048,
            file_format='mp3',
            status=JobStatus.PROCESSING.value,
            language='ru-RU'
        )
        db.session.add(job)
        db.session.commit()
        
        return job


class TestTranscriptAPI:
    """Test transcript API endpoint functionality."""
    
    def test_get_transcript_success(self, client, sample_job):
        """Test successful transcript retrieval."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert data['success'] is True
        assert data['job_id'] == sample_job.job_id
        assert data['filename'] == sample_job.original_filename
        
        # Verify transcript data
        transcript = data['transcript']
        assert 'formatted_text' in transcript
        assert 'preview' in transcript
        assert 'segments' in transcript
        assert transcript['speaker_count'] == 2
        assert transcript['total_segments'] == 5
        assert transcript['total_duration'] > 0
        
        # Verify metadata
        assert 'metadata' in data
        assert 'validation' in data
        
    def test_get_transcript_formatted_text_structure(self, client, sample_job):
        """Test formatted transcript text structure and content."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        data = json.loads(response.data)
        
        formatted_text = data['transcript']['formatted_text']
        
        # Should contain timestamps in brackets
        assert '[00:00]' in formatted_text
        assert '[00:05]' in formatted_text
        
        # Should contain speaker labels
        assert 'Alice:' in formatted_text
        assert 'Speaker 2:' in formatted_text
        
        # Should contain Cyrillic text
        assert 'Привет всем' in formatted_text
        assert 'Қазақша мәтін' in formatted_text
        
        # Should be properly formatted with paragraphs
        assert '\n\n' in formatted_text
        
    def test_get_transcript_segments_structure(self, client, sample_job):
        """Test transcript segments structure and data."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        data = json.loads(response.data)
        
        segments = data['transcript']['segments']
        
        assert len(segments) == 2  # Should be grouped by speaker changes
        
        # Check first segment (Alice)
        first_segment = segments[0]
        assert first_segment['speaker'] == 'Alice'
        assert 'Привет всем' in first_segment['text']
        assert first_segment['start_time'] == 0.0
        
        # Check second segment (Speaker 2)
        second_segment = segments[1]
        assert second_segment['speaker'] == 'Speaker 2'
        assert 'Спасибо за приглашение' in second_segment['text']
        
    def test_get_transcript_preview(self, client, sample_job):
        """Test transcript preview generation."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        data = json.loads(response.data)
        
        preview = data['transcript']['preview']
        
        # Preview should be limited to 500 characters
        assert len(preview) <= 500
        
        # Should contain start of transcript
        assert '[00:00]' in preview
        assert 'Alice:' in preview
        
    def test_get_transcript_validation_warnings(self, client, sample_job):
        """Test transcript validation warnings."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        data = json.loads(response.data)
        
        validation = data['validation']
        
        assert 'warnings' in validation
        assert 'segment_count' in validation
        assert 'speaker_count' in validation
        assert validation['segment_count'] == 5
        assert validation['speaker_count'] == 2
        
    def test_get_transcript_job_not_found(self, client):
        """Test transcript request for non-existent job."""
        response = client.get('/api/v1/jobs/nonexistent-job/transcript')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'Job not found'
        
    def test_get_transcript_job_not_completed(self, client, processing_job):
        """Test transcript request for job that's not completed."""
        response = client.get(f'/api/v1/jobs/{processing_job.job_id}/transcript')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'Job not completed'
        
    def test_get_transcript_incomplete_data(self, client, incomplete_job):
        """Test transcript request for job with incomplete data."""
        response = client.get(f'/api/v1/jobs/{incomplete_job.job_id}/transcript')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'Invalid transcript data'
        
    def test_get_transcript_cyrillic_encoding(self, client, sample_job):
        """Test proper handling of Cyrillic text encoding."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        
        # Ensure response is properly encoded as UTF-8
        assert response.content_type == 'application/json'
        
        # Decode and verify Cyrillic characters are preserved
        data = json.loads(response.data.decode('utf-8'))
        formatted_text = data['transcript']['formatted_text']
        
        # Check Russian text
        assert 'Привет всем, добро пожаловать на встречу' in formatted_text
        assert 'Сегодня мы обсудим важные вопросы' in formatted_text
        
        # Check Kazakh text
        assert 'Қазақша мәтін тестісі үшін' in formatted_text
        
    def test_get_transcript_confidence_scores(self, client, sample_job):
        """Test confidence score handling and display."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        data = json.loads(response.data)
        
        # Overall confidence should be calculated
        assert data['transcript']['confidence_score'] == 0.85
        
        # Individual segment confidence should be preserved
        segments = data['transcript']['segments']
        assert len(segments) > 0
        
    def test_get_transcript_time_formatting(self, client, sample_job):
        """Test time formatting in different scenarios."""
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        data = json.loads(response.data)
        
        formatted_text = data['transcript']['formatted_text']
        
        # Should use MM:SS format for short durations
        assert '[00:00]' in formatted_text
        assert '[00:05]' in formatted_text
        assert '[00:13]' in formatted_text
        
        # Duration should be formatted properly
        total_duration = data['transcript']['total_duration']
        assert total_duration == 32.0
        
    def test_transcript_page_route(self, client, sample_job):
        """Test transcript page HTML route."""
        response = client.get(f'/transcript/{sample_job.job_id}')
        
        assert response.status_code == 200
        assert b'transcript-page' in response.data  # Check body class
        assert sample_job.original_filename.encode() in response.data
        
    def test_transcript_page_not_completed_redirect(self, client, processing_job):
        """Test transcript page redirects to status for incomplete jobs."""
        response = client.get(f'/transcript/{processing_job.job_id}')
        
        # Should render status template instead
        assert response.status_code == 200
        # Should not contain transcript-specific elements
        assert b'transcript-page' not in response.data


class TestTranscriptAPIEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_segments_handling(self, client, app):
        """Test handling of jobs with no segments."""
        with app.app_context():
            job = Job(
                job_id='empty-segments-job',
                filename='empty.mp3',
                original_filename='empty.mp3',
                file_size=100,
                file_format='mp3',
                status=JobStatus.COMPLETED.value
            )
            db.session.add(job)
            db.session.flush()
            
            # Add job result but no segments
            job_result = JobResult(
                job_id=job.id,
                raw_transcript='',
                confidence_score=0.0
            )
            db.session.add(job_result)
            db.session.commit()
            
            response = client.get(f'/api/v1/jobs/{job.job_id}/transcript')
            assert response.status_code == 400
            
    def test_malformed_segment_data(self, client, app):
        """Test handling of malformed segment data."""
        with app.app_context():
            job = Job(
                job_id='malformed-job',
                filename='malformed.mp3',
                original_filename='malformed.mp3',
                file_size=100,
                file_format='mp3',
                status=JobStatus.COMPLETED.value
            )
            db.session.add(job)
            db.session.flush()
            
            job_result = JobResult(
                job_id=job.id,
                raw_transcript='Test',
                confidence_score=0.5
            )
            db.session.add(job_result)
            
            # Add segment with missing data
            segment = TranscriptSegment(
                job_id=job.id,
                speaker_id=None,  # Missing speaker
                segment_order=1,
                start_time=0.0,
                end_time=5.0,
                text='',  # Empty text
                confidence_score=None
            )
            db.session.add(segment)
            db.session.commit()
            
            response = client.get(f'/api/v1/jobs/{job.job_id}/transcript')
            
            # Should still work but with warnings
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['validation']['warnings']) > 0
            
    @patch('backend.app.services.transcript_formatter.TranscriptFormatter.format_transcript')
    def test_formatter_exception_handling(self, mock_format, client, sample_job):
        """Test handling of formatter exceptions."""
        mock_format.side_effect = Exception("Formatter error")
        
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/transcript')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'Internal server error'
        
    def test_database_error_handling(self, client, app):
        """Test handling of database errors."""
        with app.app_context():
            # Create job but close database connection to simulate error
            job = Job(
                job_id='db-error-job',
                filename='db_error.mp3',
                original_filename='db_error.mp3',
                file_size=100,
                file_format='mp3',
                status=JobStatus.COMPLETED.value
            )
            db.session.add(job)
            db.session.commit()
            
            # Mock database error
            with patch('backend.app.models.Job.find_by_job_id') as mock_find:
                mock_find.side_effect = Exception("Database connection error")
                
                response = client.get(f'/api/v1/jobs/{job.job_id}/transcript')
                assert response.status_code == 500


if __name__ == '__main__':
    pytest.main([__file__])