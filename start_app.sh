#!/bin/bash
"""Startup script that initializes database and starts Flask app."""

echo "🚀 Starting transcriber application..."

# Initialize database
echo "📦 Initializing database..."
python3 init_db.py

if [ $? -eq 0 ]; then
    echo "✅ Database initialization completed"
else
    echo "❌ Database initialization failed"
    exit 1
fi

# Start Flask application
echo "🌐 Starting Flask application..."
if [ "$FLASK_ENV" = "development" ]; then
    python -m flask run --host=0.0.0.0 --port=5000 --debug
else
    gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 "wsgi:app"
fi