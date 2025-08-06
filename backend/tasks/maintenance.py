"""Maintenance tasks for system cleanup and monitoring."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.celery_app import celery_app
from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.enums import JobStatus
from backend.app.models.usage import UsageRecord
from backend.extensions import db

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_jobs() -> Dict[str, Any]:
    """
    Clean up expired jobs and associated files.
    
    Returns:
        Cleanup result dictionary
    """
    try:
        # Define expiration threshold (7 days for completed jobs, 1 day for failed)
        completed_threshold = datetime.utcnow() - timedelta(days=7)
        failed_threshold = datetime.utcnow() - timedelta(days=1)
        
        # Find expired jobs
        expired_completed = Job.query.filter(
            Job.status == JobStatus.COMPLETED.value,
            Job.updated_at < completed_threshold
        ).all()
        
        expired_failed = Job.query.filter(
            Job.status == JobStatus.FAILED.value,
            Job.updated_at < failed_threshold
        ).all()
        
        expired_jobs = expired_completed + expired_failed
        
        cleaned_count = 0
        cleaned_files = 0
        
        for job in expired_jobs:
            try:
                # Clean up associated files
                if job.file_path and job.file_path.exists():
                    job.file_path.unlink()
                    cleaned_files += 1
                
                # Delete job and associated records
                # Note: Foreign key constraints will handle cascading deletes
                db.session.delete(job)
                cleaned_count += 1
                
            except Exception as job_exc:
                logger.error(f"Failed to clean up job {job.id}: {job_exc}")
                db.session.rollback()
                continue
        
        # Commit all deletions
        db.session.commit()
        
        result = {
            'jobs_cleaned': cleaned_count,
            'files_cleaned': cleaned_files,
            'total_expired': len(expired_jobs),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        db.session.rollback()
        raise


@celery_app.task
def update_processing_metrics() -> Dict[str, Any]:
    """
    Update processing metrics and usage statistics.
    
    Returns:
        Metrics update result dictionary
    """
    try:
        # Calculate current metrics
        total_jobs = Job.query.count()
        completed_jobs = Job.query.filter(Job.status == JobStatus.COMPLETED.value).count()
        failed_jobs = Job.query.filter(Job.status == JobStatus.FAILED.value).count()
        processing_jobs = Job.query.filter(Job.status == JobStatus.PROCESSING.value).count()
        
        # Calculate success rate
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # Calculate average processing time for completed jobs
        completed_results = db.session.query(JobResult.processing_duration).filter(
            JobResult.processing_duration.isnot(None)
        ).all()
        
        avg_processing_time = (
            sum(r.processing_duration for r in completed_results) / len(completed_results)
            if completed_results else 0
        )
        
        # Create or update usage record
        today = datetime.utcnow().date()
        usage_record = UsageRecord.query.filter(UsageRecord.date == today).first()
        
        if not usage_record:
            usage_record = UsageRecord(date=today)
            db.session.add(usage_record)
        
        # Update usage statistics
        usage_record.total_jobs = total_jobs
        usage_record.completed_jobs = completed_jobs
        usage_record.failed_jobs = failed_jobs
        usage_record.success_rate = success_rate
        usage_record.average_processing_time = avg_processing_time
        
        db.session.commit()
        
        result = {
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'processing_jobs': processing_jobs,
            'success_rate': round(success_rate, 2),
            'avg_processing_time': round(avg_processing_time, 2),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Metrics updated: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Metrics update task failed: {exc}")
        db.session.rollback()
        raise


@celery_app.task
def health_check() -> Dict[str, Any]:
    """
    Perform health check of the processing system.
    
    Returns:
        Health check result dictionary
    """
    try:
        # Check database connectivity
        db_healthy = True
        try:
            db.session.execute('SELECT 1')
        except Exception:
            db_healthy = False
        
        # Check for stuck jobs (processing for more than 2 hours)
        stuck_threshold = datetime.utcnow() - timedelta(hours=2)
        stuck_jobs = Job.query.filter(
            Job.status == JobStatus.PROCESSING.value,
            Job.updated_at < stuck_threshold
        ).count()
        
        # Check queue depth (would need Redis connection for actual implementation)
        # This is a placeholder for queue monitoring
        queue_depth = 0  # TODO: Implement actual queue depth checking
        
        # Determine overall health
        is_healthy = db_healthy and stuck_jobs == 0
        
        result = {
            'healthy': is_healthy,
            'database_healthy': db_healthy,
            'stuck_jobs': stuck_jobs,
            'queue_depth': queue_depth,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not is_healthy:
            logger.warning(f"Health check failed: {result}")
        else:
            logger.info(f"Health check passed: {result}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Health check task failed: {exc}")
        raise


@celery_app.task
def recover_stuck_jobs() -> Dict[str, Any]:
    """
    Recover jobs that have been stuck in processing state.
    
    Returns:
        Recovery result dictionary
    """
    try:
        # Find jobs stuck in processing for more than 2 hours
        stuck_threshold = datetime.utcnow() - timedelta(hours=2)
        stuck_jobs = Job.query.filter(
            Job.status == JobStatus.PROCESSING.value,
            Job.updated_at < stuck_threshold
        ).all()
        
        recovered_count = 0
        
        for job in stuck_jobs:
            try:
                # Reset job to failed status
                job.status = JobStatus.FAILED.value
                job.error_message = "Job recovered from stuck state - processing timeout"
                job.updated_at = datetime.utcnow()
                recovered_count += 1
                
            except Exception as job_exc:
                logger.error(f"Failed to recover job {job.id}: {job_exc}")
                continue
        
        db.session.commit()
        
        result = {
            'recovered_jobs': recovered_count,
            'total_stuck': len(stuck_jobs),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if recovered_count > 0:
            logger.warning(f"Recovered stuck jobs: {result}")
        else:
            logger.info(f"No stuck jobs found: {result}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Job recovery task failed: {exc}")
        db.session.rollback()
        raise


__all__ = [
    'cleanup_expired_jobs',
    'update_processing_metrics',
    'health_check',
    'recover_stuck_jobs'
]