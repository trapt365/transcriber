"""Celery application configuration for audio processing tasks."""

import os
from celery import Celery
from backend.config import get_config

# Get configuration
config = get_config()

# Create Celery instance
celery_app = Celery('transcriber')

# Configure Celery
celery_app.conf.update(
    # Broker and result backend configuration
    broker_url=config.CELERY_BROKER_URL,
    result_backend=config.CELERY_RESULT_BACKEND,
    
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'backend.tasks.audio_processing.*': {'queue': 'transcription'},
        'backend.tasks.maintenance.*': {'queue': 'maintenance'},
    },
    
    # Task configuration
    task_default_queue='transcription',
    task_default_exchange='transcription',
    task_default_exchange_type='direct',
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    
    # Task time limits
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Result configuration
    result_expires=86400,  # 24 hours
    result_persistent=True,
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-expired-jobs': {
            'task': 'backend.tasks.maintenance.cleanup_expired_jobs',
            'schedule': 3600.0,  # Every hour
        },
        'update-processing-metrics': {
            'task': 'backend.tasks.maintenance.update_processing_metrics',
            'schedule': 900.0,  # Every 15 minutes
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['backend.tasks'])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
    return {'status': 'debug_task_completed'}


# Make celery app available for import
__all__ = ['celery_app']