"""Base task classes for Celery tasks."""

import logging
from typing import Any, Dict, Optional
from celery import Task
from celery.exceptions import Retry, WorkerLostError
from backend.app.models.enums import JobStatus
from backend.app.models.job import Job
from backend.extensions import db

logger = logging.getLogger(__name__)


class BaseProcessingTask(Task):
    """Base class for audio processing tasks with error handling and progress tracking."""
    
    abstract = True
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = False
    
    def __init__(self):
        """Initialize base processing task."""
        super().__init__()
        self.job_id: Optional[str] = None
        self.current_stage: Optional[str] = None
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Task {self.name} failed with exception: {exc}",
            extra={
                'task_id': task_id,
                'job_id': self.job_id,
                'stage': self.current_stage,
                'args': args,
                'kwargs': kwargs,
                'traceback': einfo.traceback
            }
        )
        
        # Update job status if job_id is available
        if self.job_id:
            try:
                job = Job.query.get(self.job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    db.session.commit()
                    
                    # Send failure notification via WebSocket
                    self._send_status_update(
                        job_id=self.job_id,
                        status=JobStatus.FAILED.value,
                        error=str(exc)
                    )
            except Exception as db_exc:
                logger.error(f"Failed to update job status: {db_exc}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(
            f"Task {self.name} completed successfully",
            extra={
                'task_id': task_id,
                'job_id': self.job_id,
                'stage': self.current_stage,
                'result': retval
            }
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(
            f"Task {self.name} retrying due to: {exc}",
            extra={
                'task_id': task_id,
                'job_id': self.job_id,
                'stage': self.current_stage,
                'retry_count': self.request.retries,
                'max_retries': self.max_retries
            }
        )
    
    def update_progress(self, job_id: str, stage: str, progress: int, 
                       message: Optional[str] = None, **kwargs):
        """
        Update job progress and send real-time updates.
        
        Args:
            job_id: Job identifier
            stage: Current processing stage
            progress: Progress percentage (0-100)
            message: Optional progress message
            **kwargs: Additional status data
        """
        self.job_id = job_id
        self.current_stage = stage
        
        try:
            # Update job in database
            job = Job.query.get(job_id)
            if job:
                job.progress = progress
                if message:
                    job.status_message = message
                db.session.commit()
            
            # Send WebSocket update
            status_data = {
                'job_id': job_id,
                'stage': stage,
                'progress': progress,
                'status': JobStatus.PROCESSING.value,
                **kwargs
            }
            
            if message:
                status_data['message'] = message
            
            self._send_status_update(**status_data)
            
        except Exception as exc:
            logger.error(f"Failed to update progress: {exc}")
    
    def _send_status_update(self, **status_data):
        """
        Send status update via WebSocket.
        
        Args:
            **status_data: Status information to broadcast
        """
        try:
            from backend.app.services.progress_service import ProgressService
            progress_service = ProgressService()
            progress_service.send_job_update(**status_data)
        except Exception as exc:
            logger.error(f"Failed to send WebSocket update: {exc}")
    
    def should_retry(self, exc) -> bool:
        """
        Determine if task should be retried based on exception type.
        
        Args:
            exc: Exception that occurred
            
        Returns:
            True if task should be retried
        """
        # Don't retry for certain exception types
        non_retryable = (
            ValueError,  # Invalid input
            FileNotFoundError,  # Missing files
            PermissionError,  # File permission issues
        )
        
        if isinstance(exc, non_retryable):
            return False
        
        # Don't retry if max retries exceeded
        if self.request.retries >= self.max_retries:
            return False
        
        return True


class ProcessingStageEnum:
    """Processing stage constants."""
    
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    UPLOADING_TO_API = "uploading_to_api"
    PROCESSING_API = "processing_api"
    DOWNLOADING_RESULTS = "downloading_results"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__ = ['BaseProcessingTask', 'ProcessingStageEnum']