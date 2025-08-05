"""Main application package."""

from datetime import datetime
from flask import Flask
from backend.config import get_config
from backend.extensions import init_extensions


def create_app():
    """Application factory pattern."""
    app = Flask(__name__, 
                template_folder='../../frontend/templates',
                static_folder='../../frontend/static')
    
    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize extensions
    init_extensions(app)
    
    # Import models to ensure they're registered with SQLAlchemy
    from backend.app.models import (
        Job, JobResult, Speaker, TranscriptSegment, UsageStats
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
    
    return app