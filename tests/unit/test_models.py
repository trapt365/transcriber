"""Unit tests for database models."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from backend.app.models.enums import JobStatus, AudioFormat, ExportFormat
from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.speaker import Speaker
from backend.app.models.segment import TranscriptSegment
from backend.app.models.usage import UsageStats


class TestJobStatus:
    """Test JobStatus enum functionality."""
    
    def test_status_values(self):
        """Test that status enum has correct values."""
        assert JobStatus.UPLOADED.value == "uploaded"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
    
    def test_valid_transitions(self):
        """Test valid status transitions."""
        transitions = JobStatus.valid_transitions()
        
        assert JobStatus.PROCESSING in transitions[JobStatus.UPLOADED]
        assert JobStatus.FAILED in transitions[JobStatus.UPLOADED]
        assert JobStatus.COMPLETED in transitions[JobStatus.PROCESSING]
        assert JobStatus.FAILED in transitions[JobStatus.PROCESSING]
        assert transitions[JobStatus.COMPLETED] == []
        assert transitions[JobStatus.FAILED] == []
    
    def test_can_transition_to(self):
        """Test transition validation."""
        assert JobStatus.UPLOADED.can_transition_to(JobStatus.PROCESSING)
        assert JobStatus.UPLOADED.can_transition_to(JobStatus.FAILED)
        assert not JobStatus.UPLOADED.can_transition_to(JobStatus.COMPLETED)
        assert not JobStatus.COMPLETED.can_transition_to(JobStatus.PROCESSING)


class TestJob:
    """Test Job model functionality."""
    
    def test_job_creation(self):
        """Test job model creation with default values."""
        job = Job(
            filename="test_audio.wav",
            original_filename="test_audio.wav",
            file_size=1024000,
            file_format="wav"
        )
        
        assert job.filename == "test_audio.wav"
        assert job.original_filename == "test_audio.wav"
        assert job.file_size == 1024000
        assert job.file_format == "wav"
        assert job.status == JobStatus.UPLOADED.value
        assert job.progress == 0
        assert job.enable_diarization is True
        assert job.language == 'auto'
        assert job.model == 'base'
        assert job.job_id is not None  # UUID should be generated
    
    def test_to_dict(self):
        """Test job serialization to dictionary."""
        job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav",
            duration=30.5
        )
        
        job_dict = job.to_dict()
        
        assert job_dict['filename'] == "test.wav"
        assert job_dict['file_size'] == 1000
        assert job_dict['file_format'] == "wav"
        assert job_dict['status'] == "uploaded"
        assert job_dict['progress'] == 0
        assert job_dict['duration'] == 30.5
        assert job_dict['enable_diarization'] is True
    
    def test_update_status_valid_transition(self):
        """Test valid status update."""
        job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav"
        )
        
        # Test transition to processing
        result = job.update_status(JobStatus.PROCESSING)
        assert result is True
        assert job.status == JobStatus.PROCESSING.value
        assert job.started_at is not None
        
        # Test transition to completed
        result = job.update_status(JobStatus.COMPLETED)
        assert result is True
        assert job.status == JobStatus.COMPLETED.value
        assert job.completed_at is not None
        assert job.progress == 100
    
    def test_update_status_invalid_transition(self):
        """Test invalid status update."""
        job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav"
        )
        
        # Try to go directly from uploaded to completed
        result = job.update_status(JobStatus.COMPLETED)
        assert result is False
        assert job.status == JobStatus.UPLOADED.value
    
    def test_update_status_with_error(self):
        """Test status update with error message."""
        job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav"
        )
        
        error_msg = "Processing failed due to invalid format"
        result = job.update_status(JobStatus.FAILED, error_msg)
        
        assert result is True
        assert job.status == JobStatus.FAILED.value
        assert job.error_message == error_msg
        assert job.completed_at is not None
    
    def test_is_expired(self):
        """Test job expiration check."""
        # Create expired job
        expired_job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav"
        )
        expired_job.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        assert expired_job.is_expired is True
        
        # Create non-expired job
        fresh_job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav"
        )
        fresh_job.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        assert fresh_job.is_expired is False
    
    def test_processing_time(self):
        """Test processing time calculation."""
        job = Job(
            filename="test.wav",
            original_filename="test.wav",
            file_size=1000,
            file_format="wav"
        )
        
        # No start time
        assert job.processing_time is None
        
        # Set start time
        job.started_at = datetime.utcnow() - timedelta(seconds=30)
        processing_time = job.processing_time
        
        assert processing_time is not None
        assert 29 <= processing_time <= 31  # Allow for small time differences
        
        # Set completion time
        job.completed_at = job.started_at + timedelta(seconds=25)
        assert job.processing_time == 25.0


class TestJobResult:
    """Test JobResult model functionality."""
    
    def test_result_creation(self):
        """Test job result creation."""
        result = JobResult(
            job_id=1,
            raw_transcript="Hello world",
            formatted_transcript="Hello, world!",
            confidence_score=0.95
        )
        
        assert result.job_id == 1
        assert result.raw_transcript == "Hello world"
        assert result.formatted_transcript == "Hello, world!"
        assert result.confidence_score == 0.95
        assert result.export_formats_generated is None
    
    def test_to_dict(self):
        """Test result serialization."""
        result = JobResult(
            job_id=1,
            raw_transcript="Test transcript",
            confidence_score=0.9,
            word_count=2
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['job_id'] == 1
        assert result_dict['raw_transcript'] == "Test transcript"
        assert result_dict['confidence_score'] == 0.9
        assert result_dict['word_count'] == 2
    
    def test_calculate_word_count(self):
        """Test word count calculation."""
        result = JobResult(job_id=1)
        
        # Empty transcript
        result.formatted_transcript = ""
        assert result.calculate_word_count() == 0
        assert result.word_count == 0
        
        # Simple transcript
        result.formatted_transcript = "Hello world test"
        assert result.calculate_word_count() == 3
        assert result.word_count == 3
        
        # None transcript
        result.formatted_transcript = None
        assert result.calculate_word_count() == 0
    
    def test_export_format_management(self):
        """Test export format tracking."""
        result = JobResult(job_id=1)
        
        # Initially no formats
        assert result.get_export_status("json") is False
        
        # Add format
        result.add_export_format("json")
        assert result.get_export_status("json") is True
        assert result.export_formats_generated == ["json"]
        
        # Add another format
        result.add_export_format("txt")
        assert result.get_export_status("txt") is True
        assert len(result.export_formats_generated) == 2
        
        # Don't duplicate formats
        result.add_export_format("json")
        assert len(result.export_formats_generated) == 2


class TestSpeaker:
    """Test Speaker model functionality."""
    
    def test_speaker_creation(self):
        """Test speaker creation."""
        speaker = Speaker(
            job_id=1,
            speaker_id="speaker_001",
            speaker_label="John Doe",
            confidence_score=0.9
        )
        
        assert speaker.job_id == 1
        assert speaker.speaker_id == "speaker_001"
        assert speaker.speaker_label == "John Doe"
        assert speaker.confidence_score == 0.9
    
    def test_to_dict(self):
        """Test speaker serialization."""
        speaker = Speaker(
            job_id=1,
            speaker_id="speaker_001",
            total_speech_time=120.5,
            segment_count=15
        )
        
        speaker_dict = speaker.to_dict()
        
        assert speaker_dict['job_id'] == 1
        assert speaker_dict['speaker_id'] == "speaker_001"
        assert speaker_dict['total_speech_time'] == 120.5
        assert speaker_dict['segment_count'] == 15
        assert speaker_dict['speaker_label'] == "Speaker speaker_001"  # Default label
    
    def test_calculate_speech_statistics(self):
        """Test speech statistics calculation."""
        speaker = Speaker(job_id=1, speaker_id="speaker_001")
        
        # Mock segments
        mock_segments = [
            Mock(start_time=0.0, end_time=10.0),
            Mock(start_time=20.0, end_time=35.0),
            Mock(start_time=50.0, end_time=60.0)
        ]
        speaker.segments = mock_segments
        
        stats = speaker.calculate_speech_statistics()
        
        expected_total = 10.0 + 15.0 + 10.0  # 35.0 seconds
        assert stats['total_time'] == expected_total
        assert stats['segment_count'] == 3
        assert stats['avg_segment_length'] == expected_total / 3
        
        # Check model fields were updated
        assert speaker.total_speech_time == expected_total
        assert speaker.segment_count == 3
    
    def test_get_speaking_percentage(self):
        """Test speaking percentage calculation."""
        speaker = Speaker(job_id=1, speaker_id="speaker_001")
        speaker.total_speech_time = 30.0
        
        # 30 seconds out of 120 seconds = 25%
        percentage = speaker.get_speaking_percentage(120.0)
        assert percentage == 25.0
        
        # Edge cases
        assert speaker.get_speaking_percentage(0.0) == 0.0
        
        speaker.total_speech_time = None
        assert speaker.get_speaking_percentage(120.0) == 0.0
    
    def test_set_label(self):
        """Test speaker label setting."""
        speaker = Speaker(job_id=1, speaker_id="speaker_001")
        
        speaker.set_label("Alice")
        assert speaker.speaker_label == "Alice"
        assert speaker.updated_at is not None


class TestTranscriptSegment:
    """Test TranscriptSegment model functionality."""
    
    def test_segment_creation(self):
        """Test segment creation."""
        segment = TranscriptSegment(
            job_id=1,
            segment_order=1,
            start_time=0.0,
            end_time=10.5,
            text="Hello world"
        )
        
        assert segment.job_id == 1
        assert segment.segment_order == 1
        assert segment.start_time == 0.0
        assert segment.end_time == 10.5
        assert segment.text == "Hello world"
        assert segment.is_silence is False
        assert segment.contains_profanity is False
    
    def test_duration_property(self):
        """Test duration calculation."""
        segment = TranscriptSegment(
            job_id=1,
            segment_order=1,
            start_time=5.0,
            end_time=15.5,
            text="Test"
        )
        
        assert segment.duration == 10.5
    
    def test_formatted_time_range(self):
        """Test time range formatting."""
        segment = TranscriptSegment(
            job_id=1,
            segment_order=1,
            start_time=65.25,  # 1:05.25
            end_time=125.75,   # 2:05.75
            text="Test"
        )
        
        time_range = segment.formatted_time_range
        assert "01:05.25" in time_range
        assert "02:05.75" in time_range
        assert " - " in time_range
    
    def test_calculate_word_count(self):
        """Test word count calculation."""
        segment = TranscriptSegment(
            job_id=1,
            segment_order=1,
            start_time=0.0,
            end_time=10.0,
            text="Hello world test segment"
        )
        
        word_count = segment.calculate_word_count()
        assert word_count == 4
        assert segment.word_count == 4
    
    def test_update_text(self):
        """Test text updating with formatting tracking."""
        segment = TranscriptSegment(
            job_id=1,
            segment_order=1,
            start_time=0.0,
            end_time=10.0,
            text="original text"
        )
        
        # Update without formatting flag
        segment.update_text("updated text")
        assert segment.text == "updated text"
        assert segment.original_text == "original text"
        assert segment.word_count == 2
        
        # Update with formatting flag
        segment.update_text("formatted text", is_formatted=True)
        assert segment.text == "formatted text"
        assert segment.original_text == "original text"  # Should not change


class TestUsageStats:
    """Test UsageStats model functionality."""
    
    def test_usage_stats_creation(self):
        """Test usage stats creation."""
        from datetime import date
        
        stats = UsageStats(
            usage_date=date.today(),
            audio_minutes_processed=60.5,
            api_calls_made=10,
            successful_jobs=8,
            failed_jobs=2,
            api_cost=15.50
        )
        
        assert stats.usage_date == date.today()
        assert stats.audio_minutes_processed == 60.5
        assert stats.api_calls_made == 10
        assert stats.successful_jobs == 8
        assert stats.failed_jobs == 2
        assert stats.api_cost == 15.50
        assert stats.cost_currency == 'USD'
    
    def test_to_dict(self):
        """Test usage stats serialization."""
        from datetime import date
        
        stats = UsageStats(
            usage_date=date.today(),
            successful_jobs=5,
            failed_jobs=1,
            api_cost=10.0
        )
        
        stats_dict = stats.to_dict()
        
        assert stats_dict['successful_jobs'] == 5
        assert stats_dict['failed_jobs'] == 1
        assert stats_dict['total_jobs'] == 6
        assert stats_dict['api_cost'] == 10.0
        assert 'success_rate' in stats_dict
        assert 'cost_per_minute' in stats_dict
    
    def test_get_success_rate(self):
        """Test success rate calculation."""
        stats = UsageStats()
        
        # No jobs
        assert stats.get_success_rate() == 0.0
        
        # Mixed results
        stats.successful_jobs = 8
        stats.failed_jobs = 2
        assert stats.get_success_rate() == 80.0
        
        # All successful
        stats.failed_jobs = 0
        assert stats.get_success_rate() == 100.0
    
    def test_get_cost_per_minute(self):
        """Test cost per minute calculation."""
        stats = UsageStats()
        
        # No minutes processed
        assert stats.get_cost_per_minute() == 0.0
        
        # With data
        stats.audio_minutes_processed = 30.0
        stats.api_cost = 15.0
        assert stats.get_cost_per_minute() == 0.5
    
    def test_add_job_stats(self):
        """Test adding job statistics."""
        stats = UsageStats()
        
        # Mock job
        mock_job = Mock()
        mock_job.duration = 120.0  # 2 minutes
        mock_job.status = 'completed'
        mock_job.file_size = 1024 * 1024  # 1MB
        mock_job.processing_time = 30.0
        
        stats.add_job_stats(mock_job, api_cost=2.5)
        
        assert stats.audio_minutes_processed == 2.0
        assert stats.api_calls_made == 1
        assert stats.files_processed == 1
        assert stats.successful_jobs == 1
        assert stats.failed_jobs == 0
        assert stats.api_cost == 2.5
        assert stats.storage_used_mb == 1.0
        assert stats.avg_processing_time == 30.0
    
    def test_efficiency_metrics(self):
        """Test efficiency metrics calculation."""
        stats = UsageStats(
            successful_jobs=12,
            failed_jobs=3,
            audio_minutes_processed=45.0,
            api_cost=30.0,
            storage_used_mb=150.0
        )
        
        metrics = stats.get_efficiency_metrics()
        
        assert 'jobs_per_hour' in metrics
        assert 'minutes_per_job' in metrics
        assert 'cost_efficiency' in metrics
        assert 'storage_efficiency' in metrics
        
        assert metrics['minutes_per_job'] == 3.0  # 45 minutes / 15 jobs
        assert metrics['cost_efficiency'] == 0.5   # 15 jobs / 30 cost
        assert metrics['storage_efficiency'] == 0.3  # 45 minutes / 150 MB