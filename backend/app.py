"""Entry point for running the application directly."""

from backend.app import create_app

# Create the app instance for Flask CLI discovery
app, socketio = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True)