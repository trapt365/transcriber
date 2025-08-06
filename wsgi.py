"""WSGI entry point for the Flask application."""

from backend.app import create_app

# Create the Flask application instance
app, socketio = create_app()

if __name__ == "__main__":
    # For development
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)