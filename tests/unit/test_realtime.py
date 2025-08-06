"""
Unit tests for real-time WebSocket functionality
Story 1.4: Processing Status Tracking and Real-time Updates
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.app import create_app
from backend.app.routes.realtime import emit_job_status_update, emit_queue_position_update
from backend.app.services.progress_service import ProgressService
from backend.app.models import Job, ProcessingHistory
from backend.app.models.enums import JobStatus


@pytest.fixture
def app():
    """Create test application"""
    app, socketio = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def socketio_client(app):
    """Create Socket.IO test client"""
    from backend.extensions import socketio
    return socketio.test_client(app)


class TestRealtimeRoutes:
    """Test WebSocket route handlers"""
    
    def test_websocket_connection(self, socketio_client):
        """Test WebSocket connection"""
        received = socketio_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'connected'
        assert 'status' in received[0]['args'][0]
        assert received[0]['args'][0]['status'] == 'connected'
    
    def test_job_status_subscription_valid_job(self, app, socketio_client):
        """Test subscribing to valid job status"""
        with app.app_context():
            # Create a test job
            job = Job(
                job_id='test-job-123',
                filename='test.wav',
                original_filename='test.wav',
                file_size=1024,
                file_format='wav',
                status=JobStatus.UPLOADED.value
            )
            
            with patch('backend.app.routes.realtime.Job.find_by_job_id') as mock_find:
                mock_find.return_value = job
                
                # Subscribe to job status
                socketio_client.emit('subscribe_job_status', {'job_id': 'test-job-123'})
                
                # Check received messages
                received = socketio_client.get_received()
                status_update = None
                for msg in received:
                    if msg['name'] == 'job_status_update':
                        status_update = msg['args'][0]
                        break
                
                assert status_update is not None
                assert status_update['job_id'] == 'test-job-123'
                assert status_update['status'] == JobStatus.UPLOADED.value
    
    def test_job_status_subscription_invalid_job(self, socketio_client):
        """Test subscribing to invalid job"""
        with patch('backend.app.routes.realtime.Job.find_by_job_id') as mock_find:
            mock_find.return_value = None
            
            # Subscribe to non-existent job
            socketio_client.emit('subscribe_job_status', {'job_id': 'invalid-job'})
            
            # Check for error message
            received = socketio_client.get_received()
            error_msg = None
            for msg in received:
                if msg['name'] == 'error':
                    error_msg = msg['args'][0]
                    break
            
            assert error_msg is not None
            assert 'Job not found' in error_msg['message']
    
    def test_job_status_subscription_missing_job_id(self, socketio_client):
        """Test subscribing without job_id"""
        socketio_client.emit('subscribe_job_status', {})
        
        # Check for error message
        received = socketio_client.get_received()
        error_msg = None
        for msg in received:
            if msg['name'] == 'error':
                error_msg = msg['args'][0]
                break
        
        assert error_msg is not None
        assert 'job_id is required' in error_msg['message']


class TestProgressService:
    """Test progress estimation and tracking service"""
    
    def test_estimate_processing_time_no_history(self):
        """Test processing time estimation without historical data"""
        with patch.object(ProcessingHistory, 'get_average_processing_time') as mock_history:
            mock_history.return_value = None
            
            # Test small file
            time_estimate = ProgressService.estimate_processing_time(1.0)  # 1 MB
            assert time_estimate >= 30  # Minimum 30 seconds
            assert time_estimate <= 1800  # Maximum 30 minutes
            
            # Test large file
            time_estimate = ProgressService.estimate_processing_time(50.0)  # 50 MB
            assert time_estimate == 1800  # Should hit maximum
    
    def test_estimate_processing_time_with_history(self):
        """Test processing time estimation with historical data"""
        with patch.object(ProcessingHistory, 'get_average_processing_time') as mock_history:
            mock_history.return_value = 120.0  # 2 minutes historical average
            
            time_estimate = ProgressService.estimate_processing_time(5.0)
            # Should return historical average * 1.2 (buffer)
            assert time_estimate == int(120.0 * 1.2)
    
    def test_calculate_estimated_completion(self, app):
        """Test completion time calculation"""
        with app.app_context():
            job = Job(
                job_id='test-job',
                filename='test.wav',
                original_filename='test.wav',
                file_size=2 * 1024 * 1024,  # 2 MB
                file_format='wav'
            )
            
            completion_time = ProgressService.calculate_estimated_completion(job)
            assert completion_time is not None
    
    def test_update_job_progress(self, app):
        """Test job progress update"""
        with app.app_context():
            job = Job(
                job_id='test-job',
                filename='test.wav',
                original_filename='test.wav',
                file_size=1024,
                file_format='wav'
            )
            
            with patch('backend.app.services.progress_service.emit_job_status_update') as mock_emit:
                with patch.object(Job, 'find_by_job_id') as mock_find:
                    mock_find.return_value = job
                    with patch('backend.extensions.db.session.commit'):
                        
                        result = ProgressService.update_job_progress(
                            'test-job', 
                            50, 
                            'processing'
                        )
                        
                        assert result is True
                        assert job.progress == 50
                        assert job.processing_phase == 'processing'
                        mock_emit.assert_called_once()
    
    def test_get_queue_status(self, app):
        """Test queue status retrieval"""
        with app.app_context():
            with patch.object(Job, 'query') as mock_query:
                # Mock the query chain
                mock_filter = Mock()
                mock_filter.count.return_value = 5
                mock_query.filter_by.return_value = mock_filter
                
                queue_status = ProgressService.get_queue_status()
                
                assert 'queue_length' in queue_status
                assert 'processing_jobs' in queue_status
                assert 'generating_jobs' in queue_status
                assert 'total_active' in queue_status


class TestProcessingHistory:
    """Test processing history model and functionality"""
    
    def test_add_processing_record(self, app):
        """Test adding processing history record"""
        with app.app_context():
            with patch('backend.extensions.db.session.add'):
                with patch('backend.extensions.db.session.commit'):
                    record = ProcessingHistory.add_processing_record(
                        file_size=1024 * 1024,  # 1 MB
                        processing_duration=120.0  # 2 minutes
                    )
                    
                    assert record.file_size == 1024 * 1024
                    assert record.processing_duration == 120.0
    
    def test_get_average_processing_time(self, app):
        """Test getting average processing time"""
        with app.app_context():
            # Mock query results
            mock_records = [
                Mock(processing_duration=100.0),
                Mock(processing_duration=120.0),
                Mock(processing_duration=80.0)
            ]
            
            with patch.object(ProcessingHistory, 'query') as mock_query:
                # Mock the query chain
                mock_filter = Mock()
                mock_order = Mock()
                mock_limit = Mock()
                
                mock_query.filter.return_value = mock_filter
                mock_filter.order_by.return_value = mock_order
                mock_order.limit.return_value = mock_limit
                mock_limit.all.return_value = mock_records
                
                avg_time = ProcessingHistory.get_average_processing_time(1.0)
                
                # Should return average of 100, 120, 80 = 100
                assert avg_time == 100.0


class TestEmitFunctions:
    """Test WebSocket emission functions"""
    
    @patch('backend.app.routes.realtime.socketio')
    def test_emit_job_status_update(self, mock_socketio):
        """Test job status update emission"""
        status_data = {
            'status': 'processing',
            'progress': 50
        }
        
        emit_job_status_update('test-job', status_data)
        
        mock_socketio.emit.assert_called_once_with(
            'job_status_update',
            {
                'job_id': 'test-job',
                'status': 'processing',
                'progress': 50
            },
            room='test-job'
        )
    
    @patch('backend.app.routes.realtime.socketio')
    def test_emit_queue_position_update(self, mock_socketio):
        """Test queue position update emission"""
        emit_queue_position_update('test-job', 3, 900)
        
        mock_socketio.emit.assert_called_once_with(
            'queue_position_update',
            {
                'job_id': 'test-job',
                'queue_position': 3,
                'estimated_wait_seconds': 900
            },
            room='test-job'
        )


if __name__ == '__main__':
    pytest.main([__file__])