#!/usr/bin/env python3
"""Initialize database tables."""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, '/app')

from backend.app import create_app
from backend.extensions import db

def init_database():
    """Initialize database with all tables."""
    try:
        app, _ = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Database initialized successfully")
            return True
            
    except Exception as exc:
        print(f"❌ Database initialization failed: {exc}")
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)