import pytest
from backend.app import create_app


@pytest.fixture
def app():
    """Create test application."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestApp:
    """Test Flask application."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'transcriber'
    
    def test_index_route(self, client):
        """Test index route."""
        response = client.get('/')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['message'] == 'Transcriber API'
        assert data['version'] == '0.1.0'
    
    def test_app_factory(self):
        """Test application factory creates app with correct config."""
        app = create_app()
        assert app is not None
        assert app.config is not None