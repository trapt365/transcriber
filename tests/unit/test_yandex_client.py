"""Tests for Yandex SpeechKit client."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from backend.app.services.yandex_client import YandexSpeechKitClient, YandexAPIError
from backend.app.utils.exceptions import ExternalAPIError, ProcessingError


class TestYandexSpeechKitClient:
    """Test suite for YandexSpeechKitClient."""
    
    @pytest.fixture
    def client(self):
        """Create test client instance."""
        return YandexSpeechKitClient(
            api_key="test-api-key",
            folder_id="test-folder-id"
        )
    
    @pytest.fixture
    def mock_audio_file(self, tmp_path):
        """Create a mock audio file."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        return audio_file
    
    def test_client_initialization(self):
        """Test client initialization with valid credentials."""
        with patch.object(YandexSpeechKitClient, '_validate_credentials'):
            client = YandexSpeechKitClient("api-key", "folder-id")
            assert client.api_key == "api-key"
            assert client.folder_id == "folder-id"
            assert 'Authorization' in client.session.headers
    
    def test_client_initialization_invalid_credentials(self):
        """Test client initialization with invalid credentials."""
        with pytest.raises(ExternalAPIError):
            YandexSpeechKitClient("", "folder-id")
        
        with pytest.raises(ExternalAPIError):
            YandexSpeechKitClient("api-key", "")
    
    @patch('requests.Session.get')
    def test_validate_credentials_success(self, mock_get):
        """Test successful credential validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Should not raise exception
        client = YandexSpeechKitClient("valid-api-key", "valid-folder-id")
        assert client.api_key == "valid-api-key"
    
    @patch('requests.Session.get')
    def test_validate_credentials_invalid_key(self, mock_get):
        """Test credential validation with invalid API key."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(ExternalAPIError, match="Invalid Yandex API key"):
            YandexSpeechKitClient("invalid-api-key", "folder-id")
    
    @patch('requests.Session.get')
    def test_validate_credentials_invalid_folder(self, mock_get):
        """Test credential validation with invalid folder ID."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        with pytest.raises(ExternalAPIError, match="Invalid Yandex folder ID"):
            YandexSpeechKitClient("api-key", "invalid-folder-id")
    
    @patch('requests.Session.post')
    def test_transcribe_audio_sync_success(self, mock_post, client, mock_audio_file):
        """Test successful synchronous transcription."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chunks': [
                {
                    'alternatives': [
                        {
                            'text': 'Hello world',
                            'confidence': 0.95
                        }
                    ]
                }
            ]
        }
        mock_post.return_value = mock_response
        
        result = client.transcribe_audio_sync(mock_audio_file)
        
        assert result['transcript'] == 'Hello world'
        assert result['confidence'] == 0.95
        assert len(result['segments']) == 1
        assert result['processing_type'] == 'synchronous'
    
    @patch('requests.Session.post')
    def test_transcribe_audio_sync_api_error(self, mock_post, client, mock_audio_file):
        """Test synchronous transcription with API error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': {'message': 'Bad request'}}
        mock_post.return_value = mock_response
        
        with pytest.raises(ExternalAPIError, match="Yandex API error"):
            client.transcribe_audio_sync(mock_audio_file)
    
    def test_transcribe_audio_sync_missing_file(self, client):
        """Test synchronous transcription with missing file."""
        missing_file = Path("/nonexistent/file.wav")
        
        with pytest.raises(ProcessingError, match="Audio file not found"):
            client.transcribe_audio_sync(missing_file)
    
    @patch('requests.Session.post')
    def test_transcribe_audio_async_success(self, mock_post, client, mock_audio_file):
        """Test successful asynchronous transcription start."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'operation-123'}
        mock_post.return_value = mock_response
        
        operation_id = client.transcribe_audio_async(mock_audio_file)
        
        assert operation_id == 'operation-123'
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_transcribe_audio_async_no_operation_id(self, mock_post, client, mock_audio_file):
        """Test asynchronous transcription with missing operation ID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        with pytest.raises(ExternalAPIError, match="No operation ID returned"):
            client.transcribe_audio_async(mock_audio_file)
    
    @patch('requests.Session.get')
    def test_get_operation_status_success(self, mock_get, client):
        """Test successful operation status retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'done': False,
            'metadata': {'progress': 50}
        }
        mock_get.return_value = mock_response
        
        status = client.get_operation_status('operation-123')
        
        assert status['done'] is False
        assert 'metadata' in status
    
    @patch('requests.Session.get')
    def test_get_operation_status_error(self, mock_get, client):
        """Test operation status retrieval with error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Operation not found'
        mock_get.return_value = mock_response
        
        with pytest.raises(ExternalAPIError, match="Operation status request failed"):
            client.get_operation_status('nonexistent-operation')
    
    @patch.object(YandexSpeechKitClient, 'get_operation_status')
    def test_wait_for_completion_success(self, mock_get_status, client):
        """Test successful operation completion waiting."""
        # Simulate operation progression
        mock_get_status.side_effect = [
            {'done': False},  # First check - still running
            {'done': True, 'response': {'chunks': []}}  # Second check - completed
        ]
        
        result = client.wait_for_completion('operation-123', timeout=10)
        
        assert 'transcript' in result
        assert mock_get_status.call_count == 2
    
    @patch.object(YandexSpeechKitClient, 'get_operation_status')
    def test_wait_for_completion_error(self, mock_get_status, client):
        """Test operation completion waiting with error."""
        mock_get_status.return_value = {
            'done': True,
            'error': {'message': 'Processing failed'}
        }
        
        with pytest.raises(ExternalAPIError, match="Operation failed"):
            client.wait_for_completion('operation-123', timeout=10)
    
    @patch.object(YandexSpeechKitClient, 'get_operation_status')
    @patch('time.sleep')
    def test_wait_for_completion_timeout(self, mock_sleep, mock_get_status, client):
        """Test operation completion waiting with timeout."""
        mock_get_status.return_value = {'done': False}
        
        with pytest.raises(ExternalAPIError, match="timed out"):
            client.wait_for_completion('operation-123', timeout=1)
    
    def test_format_sync_result(self, client):
        """Test formatting of synchronous API results."""
        raw_result = {
            'chunks': [
                {
                    'alternatives': [
                        {'text': 'Hello', 'confidence': 0.9},
                        {'text': 'Helo', 'confidence': 0.7}
                    ]
                },
                {
                    'alternatives': [
                        {'text': 'world', 'confidence': 0.95}
                    ]
                }
            ]
        }
        
        config = {'specification': {'languageCode': 'en'}}
        result = client._format_sync_result(raw_result, config)
        
        assert result['transcript'] == 'Hello world'
        assert len(result['segments']) == 2
        assert result['segments'][0]['text'] == 'Hello'
        assert result['segments'][0]['confidence'] == 0.9
        assert result['language_detected'] == 'en'
        assert result['processing_type'] == 'synchronous'
    
    def test_format_async_result(self, client):
        """Test formatting of asynchronous API results."""
        raw_result = {
            'chunks': [
                {
                    'alternatives': [{'text': 'Speaker one text', 'confidence': 0.9}],
                    'speakerTag': '1',
                    'channelTag': 0
                },
                {
                    'alternatives': [{'text': 'Speaker two text', 'confidence': 0.85}],
                    'speakerTag': '2',
                    'channelTag': 10
                }
            ]
        }
        
        result = client._format_async_result(raw_result)
        
        assert result['transcript'] == 'Speaker one text Speaker two text'
        assert len(result['segments']) == 2
        assert len(result['speakers']) == 2
        assert result['speakers'][0]['speaker_id'] == '1'
        assert result['speakers'][1]['speaker_id'] == '2'
        assert result['processing_type'] == 'asynchronous'
    
    def test_parse_error_response(self, client):
        """Test error response parsing."""
        # Mock response with JSON error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {'message': 'Invalid request format'}
        }
        
        error_msg = client._parse_error_response(mock_response)
        assert error_msg == 'Invalid request format'
        
        # Mock response with simple message
        mock_response.json.return_value = {'message': 'Simple error'}
        error_msg = client._parse_error_response(mock_response)
        assert error_msg == 'Simple error'
        
        # Mock response with no JSON
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_response.text = 'Plain text error'
        error_msg = client._parse_error_response(mock_response)
        assert 'HTTP 400' in error_msg
        assert 'Plain text error' in error_msg