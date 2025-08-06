"""Tests for Celery tasks."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from backend.tasks.audio_processing import process_audio_task, cancel_processing_task
from backend.tasks.maintenance import cleanup_expired_jobs, update_processing_metrics
from backend.app.models.job import Job
from backend.app.models.enums import JobStatus


class TestAudioProcessingTasks:
    """Test suite for audio processing Celery tasks."""
    
    @pytest.fixture
    def mock_job(self):
        """Create a mock job instance."""
        job = Mock(spec=Job)
        job.id = 1
        job.job_id = "test-job-id"
        job.file_path = Path("/tmp/test.wav")
        job.status = JobStatus.QUEUED
        return job
    
    @pytest.fixture
    def mock_job_result(self):
        """Create a mock job result."""
        result = Mock()
        result.id = 1
        result.confidence_score = 0.95
        result.word_count = 100
        return result
    
    @patch('backend.tasks.audio_processing.Job')
    @patch('backend.tasks.audio_processing.audio_service')
    @patch('backend.tasks.audio_processing.create_processing_service')
    @patch('backend.tasks.audio_processing.db')
    def test_process_audio_task_success(self, mock_db, mock_create_service, 
                                      mock_audio_service, mock_job_model, 
                                      mock_job, mock_job_result):
        """Test successful audio processing task."""
        # Setup mocks
        mock_job_model.query.get.return_value = mock_job
        mock_job.file_path.exists.return_value = True
        
        # Mock audio analysis
        mock_audio_service.analyze_audio_file.return_value = {
            'duration': 60.0,
            'sample_rate': 16000,
            'format': 'wav'
        }
        mock_audio_service.preprocess_for_speechkit.return_value = Path("/tmp/processed.wav")
        
        # Mock processing service
        mock_service = Mock()
        mock_service.process_audio.return_value = mock_job_result
        mock_create_service.return_value = mock_service
        
        # Mock file cleanup
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):
            
            # Execute task (mocking the Celery task decorator)
            with patch.object(process_audio_task, 'update_progress'):
                result = process_audio_task.run(mock_job.id)
        
        # Assertions
        assert result['job_id'] == mock_job.id
        assert result['status'] == 'completed'
        assert mock_job.status == JobStatus.COMPLETED
        assert mock_job.progress == 100
        mock_db.session.commit.assert_called()
    
    @patch('backend.tasks.audio_processing.Job')
    def test_process_audio_task_job_not_found(self, mock_job_model):
        """Test audio processing task with non-existent job."""
        mock_job_model.query.get.return_value = None
        
        with pytest.raises(ValueError, match="Job .* not found"):
            process_audio_task.run(999)
    
    @patch('backend.tasks.audio_processing.Job')
    @patch('backend.tasks.audio_processing.db')
    def test_process_audio_task_file_not_found(self, mock_db, mock_job_model, mock_job):
        """Test audio processing task with missing audio file."""
        mock_job_model.query.get.return_value = mock_job
        mock_job.file_path.exists.return_value = False
        
        with patch.object(process_audio_task, 'update_progress'):
            with pytest.raises(Exception):  # Should be caught and re-raised
                process_audio_task.run(mock_job.id)
    
    @patch('backend.tasks.audio_processing.Job')
    @patch('backend.tasks.audio_processing.audio_service')
    @patch('backend.tasks.audio_processing.db')
    def test_process_audio_task_processing_error(self, mock_db, mock_audio_service, 
                                               mock_job_model, mock_job):
        """Test audio processing task with processing error."""
        mock_job_model.query.get.return_value = mock_job
        mock_job.file_path.exists.return_value = True
        
        # Mock audio service to raise error
        mock_audio_service.analyze_audio_file.side_effect = Exception("Processing failed")
        
        with patch.object(process_audio_task, 'update_progress'):
            with pytest.raises(Exception, match="Processing failed"):
                process_audio_task.run(mock_job.id)
    
    @patch('backend.tasks.audio_processing.Job')
    @patch('backend.tasks.audio_processing.db')
    def test_cancel_processing_task_success(self, mock_db, mock_job_model, mock_job):
        """Test successful processing cancellation."""
        mock_job_model.query.get.return_value = mock_job
        
        with patch.object(cancel_processing_task, 'update_progress'):
            result = cancel_processing_task.run(mock_job.id)
        
        assert result['job_id'] == mock_job.id
        assert result['status'] == 'cancelled'
        assert mock_job.status == JobStatus.CANCELLED
        assert mock_job.error_message == "Processing cancelled by user"
        mock_db.session.commit.assert_called()
    
    @patch('backend.tasks.audio_processing.Job')
    def test_cancel_processing_task_job_not_found(self, mock_job_model):
        """Test processing cancellation with non-existent job."""
        mock_job_model.query.get.return_value = None
        
        with pytest.raises(ValueError, match="Job .* not found"):
            cancel_processing_task.run(999)


class TestMaintenanceTasks:
    """Test suite for maintenance Celery tasks."""
    
    @patch('backend.tasks.maintenance.Job')
    @patch('backend.tasks.maintenance.db')
    @patch('backend.tasks.maintenance.datetime')
    def test_cleanup_expired_jobs_success(self, mock_datetime, mock_db, mock_job_model):
        """Test successful expired jobs cleanup."""
        # Mock datetime
        from datetime import datetime
        mock_now = datetime(2023, 1, 15, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        # Mock expired jobs
        expired_job1 = Mock()
        expired_job1.id = 1
        expired_job1.file_path = None
        
        expired_job2 = Mock()
        expired_job2.id = 2
        expired_job2.file_path = Path("/tmp/test.wav")
        expired_job2.file_path.exists.return_value = True
        expired_job2.file_path.unlink = Mock()
        
        mock_job_model.query.filter.return_value.all.side_effect = [
            [expired_job1],  # Completed jobs
            [expired_job2]   # Failed jobs
        ]
        
        result = cleanup_expired_jobs.run()
        
        assert result['jobs_cleaned'] == 2
        assert result['files_cleaned'] == 1
        assert result['total_expired'] == 2
        
        # Verify database operations
        mock_db.session.delete.assert_any_call(expired_job1)
        mock_db.session.delete.assert_any_call(expired_job2)
        mock_db.session.commit.assert_called()
        
        # Verify file cleanup
        expired_job2.file_path.unlink.assert_called_once()
    
    @patch('backend.tasks.maintenance.Job')
    @patch('backend.tasks.maintenance.db')
    def test_cleanup_expired_jobs_database_error(self, mock_db, mock_job_model):
        """Test cleanup with database error."""
        # Mock jobs query to return some jobs
        expired_job = Mock()
        expired_job.id = 1
        expired_job.file_path = None
        
        mock_job_model.query.filter.return_value.all.side_effect = [
            [expired_job],  # Completed jobs
            []              # Failed jobs
        ]
        
        # Mock database error
        mock_db.session.delete.side_effect = Exception("Database error")
        
        result = cleanup_expired_jobs.run()
        
        # Should handle error gracefully
        assert result['jobs_cleaned'] == 0
        assert result['total_expired'] == 1
        mock_db.session.rollback.assert_called()
    
    @patch('backend.tasks.maintenance.Job')
    @patch('backend.tasks.maintenance.JobResult')
    @patch('backend.tasks.maintenance.UsageRecord')
    @patch('backend.tasks.maintenance.db')
    def test_update_processing_metrics_success(self, mock_db, mock_usage_model, 
                                             mock_result_model, mock_job_model):
        """Test successful processing metrics update."""
        # Mock job counts
        mock_job_model.query.count.return_value = 100
        mock_job_model.query.filter.return_value.count.side_effect = [80, 15, 5]  # completed, failed, processing
        
        # Mock processing duration query
        mock_duration_results = [Mock(processing_duration=30.0), Mock(processing_duration=45.0)]
        mock_db.session.query.return_value.filter.return_value.all.return_value = mock_duration_results
        
        # Mock usage record
        mock_usage_record = Mock()
        mock_usage_model.query.filter.return_value.first.return_value = mock_usage_record
        
        result = update_processing_metrics.run()
        
        assert result['total_jobs'] == 100
        assert result['completed_jobs'] == 80
        assert result['failed_jobs'] == 15
        assert result['processing_jobs'] == 5
        assert result['success_rate'] == 80.0
        assert result['avg_processing_time'] == 37.5  # (30 + 45) / 2
        
        # Verify usage record update
        assert mock_usage_record.total_jobs == 100
        assert mock_usage_record.success_rate == 80.0
        mock_db.session.commit.assert_called()
    
    @patch('backend.tasks.maintenance.Job')
    @patch('backend.tasks.maintenance.UsageRecord')
    @patch('backend.tasks.maintenance.db')
    def test_update_processing_metrics_new_usage_record(self, mock_db, mock_usage_model, 
                                                       mock_job_model):
        """Test metrics update with new usage record creation."""
        # Mock job counts
        mock_job_model.query.count.return_value = 50
        mock_job_model.query.filter.return_value.count.side_effect = [40, 10, 0]
        
        # Mock no existing usage record
        mock_usage_model.query.filter.return_value.first.return_value = None
        
        # Mock duration query with no results
        mock_db.session.query.return_value.filter.return_value.all.return_value = []
        
        result = update_processing_metrics.run()
        
        assert result['total_jobs'] == 50
        assert result['avg_processing_time'] == 0.0  # No duration data
        
        # Verify new usage record creation
        mock_db.session.add.assert_called()
        mock_db.session.commit.assert_called()
    
    @patch('backend.tasks.maintenance.Job')
    @patch('backend.tasks.maintenance.db')
    def test_update_processing_metrics_database_error(self, mock_db, mock_job_model):
        """Test metrics update with database error."""
        mock_job_model.query.count.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            update_processing_metrics.run()
        
        mock_db.session.rollback.assert_called()


class TestBaseProcessingTask:
    """Test suite for base processing task functionality."""
    
    @patch('backend.tasks.base.Job')
    @patch('backend.tasks.base.db')
    def test_base_task_failure_handling(self, mock_db, mock_job_model):
        """Test base task failure handling."""
        from backend.tasks.base import BaseProcessingTask
        
        # Create a test task instance
        task = BaseProcessingTask()
        task.job_id = "test-job-id"
        task.current_stage = "preprocessing"
        
        # Mock job
        mock_job = Mock()
        mock_job_model.query.get.return_value = mock_job
        
        # Mock failure notification
        with patch.object(task, '_send_status_update') as mock_send:
            task.on_failure(
                exc=Exception("Test error"),
                task_id="task-123",
                args=[],
                kwargs={},
                einfo=Mock(traceback="stack trace")
            )
        
        # Verify job status update
        assert mock_job.status == JobStatus.FAILED
        assert mock_job.error_message == "Test error"
        mock_db.session.commit.assert_called()
        
        # Verify WebSocket notification
        mock_send.assert_called_with(
            job_id="test-job-id",
            status=JobStatus.FAILED.value,
            error="Test error"
        )
    
    def test_base_task_should_retry_logic(self):
        """Test base task retry decision logic."""
        from backend.tasks.base import BaseProcessingTask
        
        task = BaseProcessingTask()
        task.request = Mock(retries=1)
        task.max_retries = 3
        
        # Should retry for generic exceptions
        assert task.should_retry(Exception("Generic error")) is True
        
        # Should not retry for specific exceptions
        assert task.should_retry(ValueError("Invalid input")) is False
        assert task.should_retry(FileNotFoundError("File missing")) is False
        assert task.should_retry(PermissionError("Access denied")) is False
        
        # Should not retry if max retries exceeded
        task.request.retries = 3
        assert task.should_retry(Exception("Generic error")) is False