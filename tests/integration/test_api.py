"""Integration tests for API endpoints."""

import pytest
import json
from unittest.mock import patch, Mock

from backend.app import create_app
from backend.extensions import db


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['UPLOAD_FOLDER'] = '/tmp/test_uploads'
    app.config['REDIS_URL'] = 'redis://localhost:6379/1'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestBasicEndpoints:
    """Test basic API endpoints."""
    
    def test_index_endpoint(self, client):
        """Test index endpoint."""
        response = client.get('/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Transcriber API'
        assert data['version'] == '0.1.0'
    
    def test_basic_health_endpoint(self, client):
        """Test basic health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'transcriber'
    
    def test_detailed_health_endpoint(self, client):
        """Test detailed health check endpoint."""
        with patch('backend.app.services.health_service.HealthService.get_comprehensive_health') as mock_health:
            mock_health.return_value = {
                'status': 'healthy',
                'service': 'transcriber',
                'components': {
                    'database': {'status': 'healthy'},
                    'filesystem': {'status': 'healthy'}
                }
            }
            
            response = client.get('/health/detailed')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert data['service'] == 'transcriber'
            assert 'components' in data
    
    def test_detailed_health_endpoint_unhealthy(self, client):
        """Test detailed health check when system is unhealthy."""
        with patch('backend.app.services.health_service.HealthService.get_comprehensive_health') as mock_health:
            mock_health.return_value = {
                'status': 'unhealthy',
                'service': 'transcriber',
                'components': {
                    'database': {'status': 'unhealthy', 'error': 'Connection failed'}
                }
            }
            
            response = client.get('/health/detailed')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
    
    def test_detailed_health_endpoint_exception(self, client):
        """Test detailed health check when exception occurs."""
        with patch('backend.app.services.health_service.HealthService.get_comprehensive_health') as mock_health:
            mock_health.side_effect = Exception("Health check failed")
            
            response = client.get('/health/detailed')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
            assert 'Health check failed' in data['error']
    
    def test_nonexistent_endpoint(self, client):
        """Test accessing non-existent endpoint."""
        response = client.get('/nonexistent')
        
        assert response.status_code == 404


class TestHealthServiceIntegration:
    """Test health service integration with real components."""
    
    def test_database_health_check_integration(self, app, client):
        """Test database health check with real SQLite database."""
        with app.app_context():
            response = client.get('/health/detailed')
            
            # Should succeed with in-memory SQLite
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['components']['database']['status'] in ['healthy', 'degraded']
            assert data['components']['database']['connection'] == 'ok'
    
    def test_filesystem_health_check_integration(self, app, client):
        """Test filesystem health check integration."""
        with app.app_context():
            response = client.get('/health/detailed')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Filesystem check should be present
            assert 'filesystem' in data['components']
            fs_status = data['components']['filesystem']['status']
            assert fs_status in ['healthy', 'degraded', 'unhealthy']
    
    @patch('redis.from_url')
    def test_redis_health_check_mock_success(self, mock_redis_from_url, client):
        """Test Redis health check with mocked successful connection."""
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = b'test_value'
        mock_redis_client.info.return_value = {
            'redis_version': '7.0.0',
            'used_memory_human': '1.5M',
            'connected_clients': 2
        }
        mock_redis_from_url.return_value = mock_redis_client
        
        response = client.get('/health/detailed')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['components']['redis']['status'] == 'healthy'
        assert data['components']['redis']['version'] == '7.0.0'
    
    @patch('redis.from_url')
    def test_redis_health_check_mock_failure(self, mock_redis_from_url, client):
        """Test Redis health check with mocked failed connection."""
        mock_redis_from_url.side_effect = Exception("Redis connection failed")
        
        response = client.get('/health/detailed')
        
        # Should still return 200 if only Redis fails (degraded state)
        data = json.loads(response.data)
        assert data['components']['redis']['status'] == 'unhealthy'
        assert 'Redis connection failed' in data['components']['redis']['error']


class TestErrorHandling:
    """Test API error handling."""
    
    def test_404_error_format(self, client):
        """Test 404 error response format."""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        # Flask default 404 handling
    
    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.post('/health')  # Health endpoint only accepts GET
        
        assert response.status_code == 405
    
    def test_content_type_handling(self, client):
        """Test different content types."""
        # JSON request to basic endpoint
        response = client.get('/', headers={'Accept': 'application/json'})
        assert response.status_code == 200
        assert response.content_type.startswith('application/json')
        
        # Default request
        response = client.get('/')
        assert response.status_code == 200


class TestApplicationConfiguration:
    """Test application configuration in different modes."""
    
    def test_testing_configuration(self, app):
        """Test that testing configuration is applied."""
        assert app.config['TESTING'] is True
        assert 'sqlite:///:memory:' in app.config['SQLALCHEMY_DATABASE_URI']
    
    def test_database_tables_created(self, app):
        """Test that all required database tables are created."""
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'jobs', 'job_results', 'speakers', 
                'transcript_segments', 'usage_stats'
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not found in database"
    
    def test_extensions_initialized(self, app):
        """Test that Flask extensions are properly initialized."""
        with app.app_context():
            # Test SQLAlchemy
            assert db.engine is not None
            
            # Test that we can execute queries
            result = db.engine.execute(db.text("SELECT 1")).scalar()
            assert result == 1


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers_basic(self, client):
        """Test basic CORS headers."""
        response = client.get('/')
        
        # Basic request should not have CORS headers unless configured
        # This test assumes no CORS setup for basic requests
        assert response.status_code == 200
    
    def test_options_request(self, client):
        """Test OPTIONS request handling."""
        response = client.options('/')
        
        # Should handle OPTIONS requests
        assert response.status_code in [200, 405]  # Depends on CORS configuration


class TestSecurityHeaders:
    """Test security headers (basic tests)."""
    
    def test_no_server_header_exposure(self, client):
        """Test that server details are not exposed."""
        response = client.get('/')
        
        # Check that we don't expose too much server information
        server_header = response.headers.get('Server', '')
        assert 'Flask' not in server_header or app.config.get('TESTING')


class TestApplicationFactory:
    """Test application factory pattern."""
    
    def test_multiple_app_instances(self):
        """Test that multiple app instances can be created."""
        app1 = create_app()
        app2 = create_app()
        
        assert app1 is not app2
        assert app1.config is not app2.config
    
    def test_app_context_isolation(self):
        """Test that app contexts are isolated."""
        app1 = create_app()
        app2 = create_app()
        
        app1.config['TEST_VALUE'] = 'app1'
        app2.config['TEST_VALUE'] = 'app2'
        
        with app1.app_context():
            from flask import current_app
            assert current_app.config['TEST_VALUE'] == 'app1'
        
        with app2.app_context():
            from flask import current_app
            assert current_app.config['TEST_VALUE'] == 'app2'


class TestDatabaseConnection:
    """Test database connection handling."""
    
    def test_database_connection_within_request(self, app, client):
        """Test database connection during request handling."""
        with patch('backend.extensions.db.engine.execute') as mock_execute:
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result
            
            response = client.get('/health/detailed')
            
            # Database should be accessed during health check
            assert mock_execute.called
            assert response.status_code == 200
    
    def test_database_connection_error_handling(self, app, client):
        """Test database connection error handling."""
        with patch('backend.extensions.db.engine.execute') as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")
            
            response = client.get('/health/detailed')
            
            # Should handle database errors gracefully
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['components']['database']['status'] == 'unhealthy'


class TestRequestLifecycle:
    """Test request lifecycle handling."""
    
    def test_request_context_cleanup(self, app):
        """Test that request contexts are properly cleaned up."""
        with app.test_client() as client:
            # Make multiple requests
            for i in range(5):
                response = client.get('/')
                assert response.status_code == 200
        
        # Test should complete without memory leaks or context issues
    
    def test_application_context_during_request(self, app, client):
        """Test application context availability during request."""
        @app.route('/test-context')
        def test_context():
            from flask import current_app
            return {'app_name': current_app.name}
        
        response = client.get('/test-context')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'app_name' in data