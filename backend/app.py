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
    """Factory function for Flask CLI and gunicorn."""
    try:
        # Import from the app package (directory), not this module
        from backend.app import create_app as real_create_app
        app_instance, socketio_instance = real_create_app()
        print(f"Successfully created app: {app_instance}")
        return app_instance
    except Exception as e:
        print(f"Failed to create app using factory: {e}")
        import traceback
        traceback.print_exc()
        print("Falling back to basic app")
        return app

if __name__ == '__main__':
    app.run(debug=True)