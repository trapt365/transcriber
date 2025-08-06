"""Entry point for running the application directly."""

def create_app_instance():
    """Create app instance with error handling."""
    try:
        from backend.app import create_app
        return create_app()
    except Exception as e:
        print(f"Error creating Flask app: {e}")
        import traceback
        traceback.print_exc()
        # Create a minimal Flask app as fallback
        from flask import Flask
        app = Flask(__name__)
        return app, None

# Create the app instance for Flask CLI discovery
app, socketio = create_app_instance()

def create_app_factory():
    """Factory function for gunicorn."""
    from backend.app import create_app
    return create_app()[0]

if __name__ == '__main__':
    if socketio:
        socketio.run(app, debug=True)
    else:
        app.run(debug=True)