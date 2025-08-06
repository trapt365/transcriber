"""Progress estimation and tracking service."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.extensions import db
from backend.app.models import Job, ProcessingHistory

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for managing progress estimation and updates."""
    
    @staticmethod
    def estimate_processing_time(file_size_mb: float) -> int:
        """
        Estimate processing time in seconds based on file size.
        
        Args:
            file_size_mb: File size in megabytes
            
        Returns:
            Estimated processing time in seconds
        """
        try:
            # Get historical average if available
            historical_avg = ProcessingHistory.get_average_processing_time(file_size_mb)
            
            if historical_avg:
                # Use historical data with some buffer
                return int(historical_avg * 1.2)  # 20% buffer
            
            # Fallback to base estimation
            # Base time: ~1-2 minutes per MB for Yandex SpeechKit
            base_time = file_size_mb * 90  # 90 seconds per MB
            
            # Apply minimum and maximum bounds
            min_time = 30  # 30 seconds minimum
            max_time = 1800  # 30 minutes maximum
            
            return max(min_time, min(int(base_time), max_time))
            
        except Exception as e:
            logger.error(f"Error estimating processing time: {str(e)}")
            return 300  # Default to 5 minutes
    
    @staticmethod
    def update_job_progress(job_id: str, progress: int, 
                          processing_phase: str = None,
                          estimated_completion: datetime = None) -> bool:
        """
        Update job progress and emit real-time updates.
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            processing_phase: Current processing phase
            estimated_completion: Updated estimated completion time
            
        Returns:
            True if update was successful
        """
        try:
            job = Job.find_by_job_id(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return False
            
            # Update job fields
            job.progress = progress
            if processing_phase:
                job.processing_phase = processing_phase
            if estimated_completion:
                job.estimated_completion = estimated_completion
            
            db.session.commit()
            
            # Emit real-time update
            status_data = {
                'status': job.status,
                'progress': progress,
                'processing_phase': processing_phase,
                'estimated_completion': estimated_completion.isoformat() if estimated_completion else None,
                'queue_position': job.queue_position,
                'can_cancel': job.can_cancel
            }
            
            from backend.app.routes.realtime import emit_job_status_update
            emit_job_status_update(job_id, status_data)
            
            logger.debug(f"Updated progress for job {job_id}: {progress}%")
            return True
            
        except Exception as e:
            logger.error(f"Error updating job progress: {str(e)}")
            return False
    
    @staticmethod
    def calculate_estimated_completion(job: Job) -> Optional[datetime]:
        """
        Calculate estimated completion time for a job.
        
        Args:
            job: Job instance
            
        Returns:
            Estimated completion datetime or None
        """
        try:
            if not job.file_size:
                return None
            
            file_size_mb = job.file_size / (1024 * 1024)
            processing_time_seconds = ProgressService.estimate_processing_time(file_size_mb)
            
            # If job is already started, adjust based on progress
            if job.started_at and job.progress > 0:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                remaining_progress = (100 - job.progress) / 100
                estimated_remaining = (elapsed / (job.progress / 100)) * remaining_progress
                return datetime.utcnow() + timedelta(seconds=estimated_remaining)
            
            # If not started, estimate from now
            start_time = job.started_at or datetime.utcnow()
            return start_time + timedelta(seconds=processing_time_seconds)
            
        except Exception as e:
            logger.error(f"Error calculating estimated completion: {str(e)}")
            return None
    
    @staticmethod
    def update_queue_position(job_id: str, position: int) -> bool:
        """
        Update job queue position.
        
        Args:
            job_id: Job identifier
            position: Position in queue (1-based)
            
        Returns:
            True if update was successful
        """
        try:
            job = Job.find_by_job_id(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return False
            
            job.queue_position = position
            db.session.commit()
            
            # Emit queue position update
            from backend.app.routes.realtime import emit_queue_position_update
            emit_queue_position_update(job_id, position)
            
            logger.debug(f"Updated queue position for job {job_id}: {position}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating queue position: {str(e)}")
            return False
    
    @staticmethod
    def record_processing_completion(job: Job) -> None:
        """
        Record processing completion for historical analysis.
        
        Args:
            job: Completed job instance
        """
        try:
            if not job.processing_time or not job.file_size:
                return
            
            ProcessingHistory.add_processing_record(
                file_size=job.file_size,
                processing_duration=job.processing_time
            )
            
            logger.debug(f"Recorded processing history for job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Error recording processing completion: {str(e)}")
    
    @staticmethod
    def get_queue_status() -> Dict[str, Any]:
        """
        Get overall queue status information.
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            from backend.app.models.enums import JobStatus
            
            uploaded_count = Job.query.filter_by(status=JobStatus.UPLOADED.value).count()
            processing_count = Job.query.filter_by(status=JobStatus.PROCESSING.value).count()
            generating_count = Job.query.filter_by(status=JobStatus.GENERATING_OUTPUT.value).count()
            
            return {
                'queue_length': uploaded_count,
                'processing_jobs': processing_count,
                'generating_jobs': generating_count,
                'total_active': uploaded_count + processing_count + generating_count
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            return {
                'queue_length': 0,
                'processing_jobs': 0,
                'generating_jobs': 0,
                'total_active': 0
            }