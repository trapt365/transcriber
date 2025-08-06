"""Integration tests for the complete audio processing pipeline."""

import pytest
import tempfile
import json
from io import BytesIO
from unittest.mock import Mock, patch
from pathlib import Path

from backend.app import create_app
from backend.extensions import db
from backend.app.models.job import Job
from backend.app.models.enums import JobStatus
from backend.tasks.audio_processing import process_audio_task


@pytest.mark.integration
class TestProcessingPipelineIntegration:
    """Integration tests for the complete processing pipeline."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application."""
        app, socketio = create_app()
        app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'CELERY_TASK_ALWAYS_EAGER': True,  # Execute tasks synchronously
            'CELERY_TASK_EAGER_PROPAGATES': True,
            'YANDEX_API_KEY': 'test-api-key',
            'YANDEX_FOLDER_ID': 'test-folder-id'
        })
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def sample_job(self, app):
        """Create a sample job for testing."""
        with app.app_context():
            # Create temporary audio file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_file.write(b'fake audio data')
            temp_file.close()
            
            job = Job(
                job_id='test-job-123',
                filename='test.wav',
                original_filename='test.wav',
                file_path=Path(temp_file.name),
                file_size=len(b'fake audio data'),
                file_format='wav',
                status=JobStatus.UPLOADED
            )
            
            db.session.add(job)
            db.session.commit()
            
            yield job
            
            # Cleanup
            try:
                Path(temp_file.name).unlink()
            except FileNotFoundError:
                pass
    
    @patch('backend.app.services.yandex_client.YandexSpeechKitClient')
    @patch('backend.app.services.audio_service.audio_service')
    def test_complete_processing_pipeline_success(self, mock_audio_service, 
                                                 mock_yandex_client_class, 
                                                 app, sample_job):
        """Test complete processing pipeline from job creation to completion."""
        with app.app_context():
            # Mock audio service
            mock_audio_service.analyze_audio_file.return_value = {
                'duration': 30.0,
                'sample_rate': 16000,
                'channels': 1,
                'format': 'wav',
                'codec': 'pcm_s16le',
                'file_size': 1000000
            }
            
            processed_file = Path('/tmp/processed.wav')
            mock_audio_service.preprocess_for_speechkit.return_value = processed_file
            
            # Mock Yandex client
            mock_client = Mock()
            mock_yandex_client_class.return_value = mock_client
            
            mock_client.transcribe_audio_sync.return_value = {
                'transcript': 'Hello world test transcript',
                'confidence': 0.95,
                'segments': [
                    {
                        'order': 1,
                        'start_time': 0.0,
                        'end_time': 2.5,
                        'text': 'Hello world',
                        'confidence': 0.96,
                        'speaker_id': '1'
                    },
                    {
                        'order': 2,
                        'start_time': 2.5,
                        'end_time': 5.0,
                        'text': 'test transcript',
                        'confidence': 0.94,
                        'speaker_id': '1'
                    }
                ],
                'speakers': [
                    {
                        'speaker_id': '1',
                        'label': 'Speaker 1',
                        'confidence': 0.9
                    }
                ],
                'language_detected': 'en',
                'processing_type': 'synchronous'
            }
            
            # Mock file cleanup
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.unlink'):
                
                # Execute the complete pipeline
                result = process_audio_task.apply(args=[sample_job.id]).get()
            
            # Verify result
            assert result['status'] == 'completed'
            assert result['job_id'] == sample_job.id
            
            # Verify job status update
            db.session.refresh(sample_job)
            assert sample_job.status == JobStatus.COMPLETED
            assert sample_job.progress == 100
            
            # Verify processing service calls
            mock_audio_service.analyze_audio_file.assert_called_once()
            mock_audio_service.preprocess_for_speechkit.assert_called_once()
            mock_client.transcribe_audio_sync.assert_called_once()
    
    @patch('backend.app.services.audio_service.audio_service')
    def test_processing_pipeline_audio_analysis_failure(self, mock_audio_service, 
                                                       app, sample_job):
        """Test processing pipeline with audio analysis failure."""
        with app.app_context():
            # Mock audio service to fail
            mock_audio_service.analyze_audio_file.side_effect = Exception("Audio analysis failed")
            
            # Execute the pipeline
            with pytest.raises(Exception, match="Audio analysis failed"):
                process_audio_task.apply(args=[sample_job.id]).get()
            
            # Verify job status (should be updated by failure handler)
            db.session.refresh(sample_job)
            # Note: In real Celery, failure handling would update status
    
    @patch('backend.app.services.yandex_client.YandexSpeechKitClient')
    @patch('backend.app.services.audio_service.audio_service')
    def test_processing_pipeline_api_failure(self, mock_audio_service, 
                                           mock_yandex_client_class, 
                                           app, sample_job):
        """Test processing pipeline with Yandex API failure."""
        with app.app_context():
            # Mock audio service success
            mock_audio_service.analyze_audio_file.return_value = {
                'duration': 30.0,
                'sample_rate': 16000,
                'channels': 1,
                'format': 'wav'
            }
            mock_audio_service.preprocess_for_speechkit.return_value = Path('/tmp/processed.wav')
            
            # Mock Yandex client to fail
            mock_client = Mock()
            mock_yandex_client_class.return_value = mock_client
            mock_client.transcribe_audio_sync.side_effect = Exception("API call failed")
            
            # Execute the pipeline
            with pytest.raises(Exception, match="API call failed"):
                process_audio_task.apply(args=[sample_job.id]).get()
    
    def test_job_upload_and_queue_integration(self, client, app):
        """Test job upload and queueing integration."""
        with app.app_context():
            # Create test audio file
            test_data = b'fake audio file content'
            
            # Mock Celery task
            with patch('backend.app.routes.upload.process_audio_task') as mock_task:
                mock_task.delay.return_value = Mock(id='task-123')
                
                # Upload file
                response = client.post('/api/v1/upload', 
                                     data={'file': (BytesIO(test_data), 'test.wav')},
                                     content_type='multipart/form-data')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'job_id' in data
                
                # Verify task was queued
                mock_task.delay.assert_called_once()
                
                # Verify job was created in database
                job = Job.query.filter_by(job_id=data['job_id']).first()
                assert job is not None
                assert job.status == JobStatus.QUEUED
    
    def test_job_status_tracking_integration(self, client, app, sample_job):
        """Test job status tracking integration."""
        with app.app_context():
            # Get job status via API
            response = client.get(f'/api/v1/jobs/{sample_job.job_id}/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['job_id'] == sample_job.job_id
            assert data['status'] == JobStatus.UPLOADED.value
            
            # Update job status
            sample_job.status = JobStatus.PROCESSING
            sample_job.progress = 50
            db.session.commit()
            
            # Get updated status
            response = client.get(f'/api/v1/jobs/{sample_job.job_id}/status')
            data = json.loads(response.data)
            assert data['status'] == JobStatus.PROCESSING.value
            assert data['progress'] == 50


@pytest.mark.integration
@pytest.mark.redis
class TestRedisIntegration:
    """Integration tests requiring Redis."""
    
    def test_celery_task_queuing(self):
        """Test that tasks can be queued in Redis."""
        # This would require actual Redis connection
        # Skip if Redis is not available
        try:
            import redis
            r = redis.Redis()
            r.ping()
        except (ImportError, redis.ConnectionError):
            pytest.skip("Redis not available")
        
        # Test Celery task queuing
        # This is a placeholder for actual Redis integration tests
        pass
    
    def test_websocket_message_broadcasting(self):
        """Test WebSocket message broadcasting via Redis."""
        # This would test the real-time update functionality
        # Skip if Redis is not available
        try:
            import redis
            r = redis.Redis()
            r.ping()
        except (ImportError, redis.ConnectionError):
            pytest.skip("Redis not available")
        
        # Test WebSocket integration
        # This is a placeholder for actual WebSocket tests
        pass


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration validation."""
    
    def test_config_validation_integration(self):
        """Test configuration validation with real environment."""
        from backend.app.utils.config_validator import ConfigValidator
        
        validator = ConfigValidator('testing')
        
        # This should pass in testing environment
        summary = validator.get_validation_summary()
        
        # Should have minimal requirements for testing
        assert summary['environment'] == 'testing'
        # May have warnings but should not have critical errors
    
    def test_app_startup_with_missing_config(self):
        """Test application startup with missing configuration."""
        import os
        
        # Temporarily remove required config
        original_api_key = os.environ.get('YANDEX_API_KEY')
        if original_api_key:
            del os.environ['YANDEX_API_KEY']
        
        try:
            # Should handle missing config gracefully in non-production
            app, _ = create_app()
            assert app is not None
            
        finally:
            # Restore original config
            if original_api_key:
                os.environ['YANDEX_API_KEY'] = original_api_key