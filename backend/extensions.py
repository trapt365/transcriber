"""Flask extensions initialization."""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def init_extensions(app):
    """Initialize Flask extensions with app instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    return app