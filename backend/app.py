"""Entry point for Flask CLI and application."""

def create_app():
    """Factory function that returns the Flask application."""
    # Import here to avoid circular imports
    from backend.app import create_app as app_factory
    
    # The factory returns (app, socketio) tuple
    flask_app, socketio_instance = app_factory()
    
    return flask_app

# For direct execution, create a simple fallback app
if __name__ == '__main__':
    from flask import Flask
    simple_app = Flask(__name__)
    
    @simple_app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'transcriber-fallback'}, 200
    
    @simple_app.route('/')
    def index():
        return {'message': 'Simple Flask app running'}, 200
    
    simple_app.run(debug=True)