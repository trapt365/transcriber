from flask import Flask
from backend.config import get_config


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'transcriber'}, 200
    
    # Basic route
    @app.route('/')
    def index():
        return {'message': 'Transcriber API', 'version': '0.1.0'}, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)