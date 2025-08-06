"""Entry point for running the application directly."""

# Simple approach - just create a basic Flask app that works
from flask import Flask

app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'transcriber-basic'}, 200

@app.route('/')
def index():
    return {'message': 'Basic Flask app is running'}, 200

def create_app():
    """Factory function for gunicorn - returns the full app."""
    try:
        from backend.app import create_app as factory_create_app
        app_instance, _ = factory_create_app()
        return app_instance
    except Exception as e:
        print(f"Failed to create app using factory: {e}")
        return app

if __name__ == '__main__':
    app.run(debug=True)