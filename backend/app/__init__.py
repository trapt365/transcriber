"""Main application package."""

import logging
from datetime import datetime
from flask import Flask
from backend.config import get_config
from backend.extensions import init_extensions, socketio
from backend.app.utils.config_validator import validate_config, ConfigValidationError
from backend.app.celery_factory import init_celery


def create_app():
    """Application factory pattern."""
    app = Flask(__name__, 
                template_folder='../../frontend/templates',
                static_folder='../../frontend/static')
    
    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Validate configuration
    try:
        validate_config()
        app.logger.info("Configuration validation passed")
    except ConfigValidationError as exc:
        app.logger.error(f"Configuration validation failed: {exc}")
        # In development, we can continue with warnings
        # In production, this should probably raise the exception
        if app.config.get('FLASK_ENV') == 'production':
            raise
    
    # Initialize extensions
    init_extensions(app)
    
    # Initialize Celery integration
    init_celery(app)
    
    # Import models to ensure they're registered with SQLAlchemy
    from backend.app.models import (
        Job, JobResult, Speaker, TranscriptSegment, UsageStats, ProcessingHistory
    )
    
    # Import services
    from backend.app.services.health_service import HealthService
    
    # Initialize health service
    health_service = HealthService(
        redis_url=app.config.get('REDIS_URL'),
        upload_folder=app.config.get('UPLOAD_FOLDER')
    )
    
    # Register blueprints
    from backend.app.routes.upload import upload_bp
    from backend.app.routes.jobs import jobs_bp
    
    app.register_blueprint(upload_bp)
    app.register_blueprint(jobs_bp)
    
    # Import WebSocket handlers to register them
    from backend.app.routes import realtime
    
    # Health check endpoints
    @app.route('/health')
    def health_check():
        """Basic health check endpoint."""
        return {'status': 'healthy', 'service': 'transcriber'}, 200
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with all components."""
        try:
            health_status = health_service.get_comprehensive_health()
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return health_status, status_code
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'service': 'transcriber',
                'checked_at': datetime.utcnow().isoformat()
            }, 503
    
    # Basic route - redirect to upload page
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('upload.upload_page'))
    
    # Initialize database tables on first request
    @app.before_first_request
    def create_tables():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Failed to create database tables: {e}")
    
    return app, socketio