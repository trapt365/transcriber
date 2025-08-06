"""Celery integration factory for Flask application."""

import logging
from flask import Flask
from backend.celery_app import celery_app

logger = logging.getLogger(__name__)


def init_celery(app: Flask) -> None:
    """
    Initialize Celery with Flask application context.
    
    Args:
        app: Flask application instance
    """
    # Update Celery configuration with Flask config
    celery_app.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND'),
    )
    
    # Create task context that provides Flask app context
    class ContextTask(celery_app.Task):
        """Make celery tasks work with Flask app context."""
        
        abstract = True
        
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery_app.Task = ContextTask
    
    logger.info("Celery integration initialized")


def create_celery_worker_app(app: Flask = None):
    """
    Create Celery app for worker processes.
    
    Args:
        app: Optional Flask app instance
        
    Returns:
        Configured Celery app
    """
    if app is None:
        from backend.app import create_app
        app, _ = create_app()
    
    init_celery(app)
    return celery_app


__all__ = ['init_celery', 'create_celery_worker_app']