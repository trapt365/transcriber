"""Integration tests for database operations."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.extensions import db
from backend.app import create_app
from backend.app.models import Job, JobResult, Speaker, TranscriptSegment, UsageStats
from backend.app.models.enums import JobStatus, AudioFormat


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
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
    """Create sample job for testing."""
    with app.app_context():
        job = Job(
            filename="test_sample.wav",
            original_filename="sample_audio.wav",
            file_size=1024000,
            file_format="wav",
            duration=60.0,
            sample_rate=44100,
            channels=2,
            language="ru",
            enable_diarization=True
        )
        db.session.add(job)
        db.session.commit()
        return job


class TestJobModel:
    """Test Job model database operations."""
    
    def test_create_job(self, app):
        """Test creating a job in database."""
        with app.app_context():
            job = Job(
                filename="test_db.wav",
                original_filename="test_database.wav",
                file_size=500000,
                file_format="wav"
            )
            db.session.add(job)
            db.session.commit()
            
            # Verify job was created
            assert job.id is not None
            assert job.job_id is not None
            assert len(job.job_id) == 36  # UUID length
            assert job.status == JobStatus.UPLOADED.value
            assert job.created_at is not None
            assert job.expires_at is not None
    
    def test_job_relationships(self, app, sample_job):
        """Test job relationships with other models."""
        with app.app_context():
            # Create related objects
            result = JobResult(
                job_id=sample_job.id,
                raw_transcript="Test transcript",
                formatted_transcript="Test transcript.",
                confidence_score=0.9
            )
            
            speaker = Speaker(
                job_id=sample_job.id,
                speaker_id="speaker_001",
                speaker_label="Test Speaker",
                total_speech_time=30.0
            )
            
            segment = TranscriptSegment(
                job_id=sample_job.id,
                segment_order=1,
                start_time=0.0,
                end_time=10.0,
                text="Hello world"
            )
            
            db.session.add_all([result, speaker, segment])
            db.session.commit()
            
            # Test relationships
            job = db.session.get(Job, sample_job.id)
            assert len(job.results) == 1
            assert len(job.speakers) == 1
            assert len(job.segments) == 1
            assert job.results[0].raw_transcript == "Test transcript"
            assert job.speakers[0].speaker_label == "Test Speaker"
            assert job.segments[0].text == "Hello world"
    
    def test_job_status_updates(self, app, sample_job):
        """Test job status transitions in database."""
        with app.app_context():
            job = db.session.get(Job, sample_job.id)
            
            # Test valid transition
            success = job.update_status(JobStatus.PROCESSING)
            assert success is True
            db.session.commit()
            
            # Verify in database
            job = db.session.get(Job, sample_job.id)
            assert job.status == JobStatus.PROCESSING.value
            assert job.started_at is not None
            
            # Test completion
            success = job.update_status(JobStatus.COMPLETED)
            db.session.commit()
            
            job = db.session.get(Job, sample_job.id)
            assert job.status == JobStatus.COMPLETED.value
            assert job.completed_at is not None
            assert job.progress == 100
    
    def test_job_queries(self, app):
        """Test job query methods."""
        with app.app_context():
            # Create multiple jobs
            jobs = []
            for i in range(5):
                job = Job(
                    filename=f"test_{i}.wav",
                    original_filename=f"test_{i}.wav",
                    file_size=1000 * (i + 1),
                    file_format="wav"
                )
                jobs.append(job)
            
            db.session.add_all(jobs)
            db.session.commit()
            
            # Test find_by_job_id
            test_job = Job.find_by_job_id(jobs[0].job_id)
            assert test_job is not None
            assert test_job.id == jobs[0].id
            
            # Test find_by_status
            uploaded_jobs = Job.find_by_status(JobStatus.UPLOADED)
            assert len(uploaded_jobs) == 5
            
            # Update one job status and test again
            jobs[0].update_status(JobStatus.PROCESSING)
            db.session.commit()
            
            uploaded_jobs = Job.find_by_status(JobStatus.UPLOADED)
            processing_jobs = Job.find_by_status(JobStatus.PROCESSING)
            assert len(uploaded_jobs) == 4
            assert len(processing_jobs) == 1
    
    def test_job_expiration(self, app):
        """Test job expiration functionality."""
        with app.app_context():
            # Create expired job
            expired_job = Job(
                filename="expired.wav",
                original_filename="expired.wav",
                file_size=1000,
                file_format="wav"
            )
            expired_job.expires_at = datetime.utcnow() - timedelta(hours=1)
            
            # Create fresh job
            fresh_job = Job(
                filename="fresh.wav",
                original_filename="fresh.wav",
                file_size=1000,
                file_format="wav"
            )
            
            db.session.add_all([expired_job, fresh_job])
            db.session.commit()
            
            # Test individual expiration check
            assert expired_job.is_expired is True
            assert fresh_job.is_expired is False
            
            # Test finding expired jobs
            expired_jobs = Job.find_expired()
            assert len(expired_jobs) == 1
            assert expired_jobs[0].id == expired_job.id


class TestJobResultModel:
    """Test JobResult model database operations."""
    
    def test_create_job_result(self, app, sample_job):
        """Test creating job result in database."""
        with app.app_context():
            result = JobResult(
                job_id=sample_job.id,
                raw_transcript="This is a test transcript",
                formatted_transcript="This is a test transcript.",
                confidence_score=0.95,
                processing_duration=15.5
            )
            db.session.add(result)
            db.session.commit()
            
            # Verify result was created
            assert result.id is not None
            assert result.created_at is not None
            assert result.updated_at is not None
    
    def test_result_word_count(self, app, sample_job):
        """Test word count calculation and storage."""
        with app.app_context():
            result = JobResult(
                job_id=sample_job.id,
                formatted_transcript="This is a test transcript with seven words"
            )
            result.calculate_word_count()
            db.session.add(result)
            db.session.commit()
            
            # Verify word count in database
            stored_result = db.session.get(JobResult, result.id)
            assert stored_result.word_count == 7
    
    def test_export_format_tracking(self, app, sample_job):
        """Test export format tracking in database."""
        with app.app_context():
            result = JobResult(
                job_id=sample_job.id,
                raw_transcript="Test transcript"
            )
            db.session.add(result)
            db.session.commit()
            
            # Add export formats
            result.add_export_format("json")
            result.add_export_format("txt")
            db.session.commit()
            
            # Verify in database
            stored_result = db.session.get(JobResult, result.id)
            assert stored_result.get_export_status("json") is True
            assert stored_result.get_export_status("txt") is True
            assert stored_result.get_export_status("srt") is False


class TestSpeakerModel:
    """Test Speaker model database operations."""
    
    def test_create_speaker(self, app, sample_job):
        """Test creating speaker in database."""
        with app.app_context():
            speaker = Speaker(
                job_id=sample_job.id,
                speaker_id="speaker_001",
                speaker_label="John Doe",
                total_speech_time=45.5,
                segment_count=10,
                confidence_score=0.88
            )
            db.session.add(speaker)
            db.session.commit()
            
            # Verify speaker was created
            assert speaker.id is not None
            assert speaker.created_at is not None
    
    def test_speaker_queries(self, app, sample_job):
        """Test speaker query methods."""
        with app.app_context():
            # Create multiple speakers
            speakers = []
            for i in range(3):
                speaker = Speaker(
                    job_id=sample_job.id,
                    speaker_id=f"speaker_{i:03d}",
                    speaker_label=f"Speaker {i + 1}",
                    total_speech_time=20.0 * (i + 1)
                )
                speakers.append(speaker)
            
            db.session.add_all(speakers)
            db.session.commit()
            
            # Test find_by_job
            job_speakers = Speaker.find_by_job(sample_job.id)
            assert len(job_speakers) == 3
            
            # Test find_by_speaker_id
            specific_speaker = Speaker.find_by_speaker_id(sample_job.id, "speaker_001")
            assert specific_speaker is not None
            assert specific_speaker.speaker_label == "Speaker 2"
            
            # Test get_speaker_count
            count = Speaker.get_speaker_count(sample_job.id)
            assert count == 3


class TestTranscriptSegmentModel:
    """Test TranscriptSegment model database operations."""
    
    def test_create_segment(self, app, sample_job):
        """Test creating transcript segment in database."""
        with app.app_context():
            segment = TranscriptSegment(
                job_id=sample_job.id,
                segment_order=1,
                start_time=0.0,
                end_time=10.5,
                text="Hello, this is a test segment",
                confidence_score=0.92
            )
            segment.calculate_word_count()
            db.session.add(segment)
            db.session.commit()
            
            # Verify segment was created
            assert segment.id is not None
            assert segment.word_count == 6
            assert segment.duration == 10.5
    
    def test_segment_with_speaker(self, app, sample_job):
        """Test segment with speaker relationship."""
        with app.app_context():
            # Create speaker first
            speaker = Speaker(
                job_id=sample_job.id,
                speaker_id="speaker_001",
                speaker_label="Test Speaker"
            )
            db.session.add(speaker)
            db.session.flush()  # Get speaker ID
            
            # Create segment with speaker
            segment = TranscriptSegment(
                job_id=sample_job.id,
                speaker_id=speaker.id,
                segment_order=1,
                start_time=0.0,
                end_time=5.0,
                text="Speaker test"
            )
            db.session.add(segment)
            db.session.commit()
            
            # Test relationship
            stored_segment = db.session.get(TranscriptSegment, segment.id)
            assert stored_segment.speaker is not None
            assert stored_segment.speaker.speaker_label == "Test Speaker"
    
    def test_segment_queries(self, app, sample_job):
        """Test segment query methods."""
        with app.app_context():
            # Create multiple segments
            segments = []
            for i in range(5):
                segment = TranscriptSegment(
                    job_id=sample_job.id,
                    segment_order=i + 1,
                    start_time=i * 10.0,
                    end_time=(i + 1) * 10.0,
                    text=f"Segment {i + 1} text"
                )
                segments.append(segment)
            
            db.session.add_all(segments)
            db.session.commit()
            
            # Test find_by_job
            job_segments = TranscriptSegment.find_by_job(sample_job.id)
            assert len(job_segments) == 5
            assert job_segments[0].segment_order == 1  # Should be ordered
            
            # Test find_by_time_range
            range_segments = TranscriptSegment.find_by_time_range(
                sample_job.id, 15.0, 35.0
            )
            assert len(range_segments) == 2  # Segments 2 and 3
            
            # Test get_segment_count
            count = TranscriptSegment.get_segment_count(sample_job.id)
            assert count == 5


class TestUsageStatsModel:
    """Test UsageStats model database operations."""
    
    def test_create_usage_stats(self, app):
        """Test creating usage stats in database."""
        from datetime import date
        
        with app.app_context():
            stats = UsageStats(
                usage_date=date.today(),
                audio_minutes_processed=120.5,
                api_calls_made=15,
                successful_jobs=12,
                failed_jobs=3,
                api_cost=25.75,
                storage_used_mb=500.0
            )
            db.session.add(stats)
            db.session.commit()
            
            # Verify stats were created
            assert stats.id is not None
            assert stats.created_at is not None
    
    def test_get_or_create_daily(self, app):
        """Test getting or creating daily stats."""
        from datetime import date
        
        with app.app_context():
            today = date.today()
            
            # First call should create
            stats1 = UsageStats.get_or_create_daily(today)
            assert stats1.usage_date == today
            
            # Second call should return existing
            stats2 = UsageStats.get_or_create_daily(today)
            assert stats1.id == stats2.id
    
    def test_monthly_summary(self, app):
        """Test monthly summary calculation."""
        from datetime import date
        
        with app.app_context():
            # Create stats for multiple days
            base_date = date(2023, 6, 1)
            for i in range(5):
                stats = UsageStats(
                    usage_date=date(2023, 6, i + 1),
                    audio_minutes_processed=30.0,
                    api_calls_made=5,
                    successful_jobs=4,
                    failed_jobs=1,
                    api_cost=7.5
                )
                db.session.add(stats)
            
            db.session.commit()
            
            # Get monthly summary
            summary = UsageStats.get_monthly_summary(2023, 6)
            
            assert summary['year'] == 2023
            assert summary['month'] == 6
            assert summary['total_audio_minutes'] == 150.0  # 5 * 30
            assert summary['total_api_cost'] == 37.5  # 5 * 7.5
            assert summary['total_jobs'] == 25  # 5 * 5
            assert summary['successful_jobs'] == 20  # 5 * 4
            assert summary['success_rate'] == 80.0  # 20/25 * 100
            assert summary['days_with_activity'] == 5


class TestDatabaseIntegration:
    """Test overall database integration."""
    
    def test_cascade_delete(self, app, sample_job):
        """Test cascade deletion of related records."""
        with app.app_context():
            # Create related records
            result = JobResult(job_id=sample_job.id, raw_transcript="Test")
            speaker = Speaker(job_id=sample_job.id, speaker_id="sp1", speaker_label="Speaker 1")
            db.session.add_all([result, speaker])
            db.session.flush()
            
            segment = TranscriptSegment(
                job_id=sample_job.id,
                speaker_id=speaker.id,
                segment_order=1,
                start_time=0.0,
                end_time=5.0,
                text="Test segment"
            )
            db.session.add(segment)
            db.session.commit()
            
            # Verify records exist
            assert JobResult.query.filter_by(job_id=sample_job.id).count() == 1
            assert Speaker.query.filter_by(job_id=sample_job.id).count() == 1
            assert TranscriptSegment.query.filter_by(job_id=sample_job.id).count() == 1
            
            # Delete job
            db.session.delete(sample_job)
            db.session.commit()
            
            # Verify cascade delete worked
            assert JobResult.query.filter_by(job_id=sample_job.id).count() == 0
            assert Speaker.query.filter_by(job_id=sample_job.id).count() == 0
            assert TranscriptSegment.query.filter_by(job_id=sample_job.id).count() == 0
    
    def test_transaction_rollback(self, app):
        """Test transaction rollback on error."""
        with app.app_context():
            try:
                # Start transaction
                job = Job(
                    filename="transaction_test.wav",
                    original_filename="transaction_test.wav",
                    file_size=1000,
                    file_format="wav"
                )
                db.session.add(job)
                db.session.flush()  # Get job ID but don't commit
                
                # Add result
                result = JobResult(job_id=job.id, raw_transcript="Test")
                db.session.add(result)
                
                # Force an error (invalid constraint)
                invalid_job = Job(
                    filename=None,  # This should cause an error
                    original_filename="invalid.wav",
                    file_size=1000,
                    file_format="wav"
                )
                db.session.add(invalid_job)
                
                # This should fail
                db.session.commit()
                
            except Exception:
                db.session.rollback()
            
            # Verify nothing was committed
            assert Job.query.filter_by(filename="transaction_test.wav").count() == 0
            assert JobResult.query.filter_by(raw_transcript="Test").count() == 0
    
    def test_concurrent_access(self, app):
        """Test handling of concurrent database access."""
        with app.app_context():
            # Create a job
            job = Job(
                filename="concurrent_test.wav",
                original_filename="concurrent_test.wav",
                file_size=1000,
                file_format="wav"
            )
            db.session.add(job)
            db.session.commit()
            
            # Simulate concurrent updates
            # Get job in two different sessions
            job1 = Job.query.filter_by(job_id=job.job_id).first()
            job2 = Job.query.filter_by(job_id=job.job_id).first()
            
            # Update progress in both
            job1.progress = 50
            job2.progress = 75
            
            # First commit should succeed
            db.session.merge(job1)
            db.session.commit()
            
            # Second commit should also succeed (last write wins)
            db.session.merge(job2)
            db.session.commit()
            
            # Verify final state
            final_job = Job.query.filter_by(job_id=job.job_id).first()
            assert final_job.progress == 75  # Last write wins