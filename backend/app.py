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
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import create_app as factory_create_app
        return factory_create_app()[0]
    except Exception:
        return app

if __name__ == '__main__':
    app.run(debug=True)