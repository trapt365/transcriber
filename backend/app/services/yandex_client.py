"""Yandex SpeechKit API client for audio transcription."""

import logging
import time
import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from backend.app.utils.exceptions import ExternalAPIError, ProcessingError
from backend.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class YandexSpeechKitClient:
    """Client for Yandex SpeechKit API integration."""
    
    # API endpoints
    SYNC_ENDPOINT = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    ASYNC_ENDPOINT = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
    OPERATION_ENDPOINT = "https://operation.api.cloud.yandex.net/operations"
    
    # Default configuration templates
    CONFIG_TEMPLATES = {
        'default': {
            'specification': {
                'languageCode': 'auto',
                'model': 'general',
                'profanityFilter': False,
                'literature_text': True,
                'format': 'lpcm',
                'sampleRateHertz': 16000,
            },
            'recognition_config': {
                'enable_speaker_diarization': True,
                'max_speaker_count': 10,
                'enable_automatic_punctuation': True,
            }
        },
        'high_quality': {
            'specification': {
                'languageCode': 'auto',
                'model': 'general',
                'profanityFilter': False,
                'literature_text': True,
                'format': 'lpcm',
                'sampleRateHertz': 16000,
            },
            'recognition_config': {
                'enable_speaker_diarization': True,
                'max_speaker_count': 10,
                'enable_automatic_punctuation': True,
                'enable_partial_results': True,
            }
        }
    }
    
    def __init__(self, api_key: str, folder_id: str):
        """
        Initialize Yandex SpeechKit client.
        
        Args:
            api_key: Yandex API key
            folder_id: Yandex folder ID
            
        Raises:
            ExternalAPIError: If credentials are invalid
        """
        self.api_key = api_key
        self.folder_id = folder_id
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Authorization': f'Api-Key {self.api_key}',
            'User-Agent': 'TranscriberApp/1.0'
        })
        
        self._validate_credentials()
    
    def _validate_credentials(self) -> None:
        """
        Validate API credentials by making a test request.
        
        Raises:
            ExternalAPIError: If credentials are invalid
        """
        if not self.api_key:
            raise ExternalAPIError("Yandex API key is required")
        if not self.folder_id:
            raise ExternalAPIError("Yandex folder ID is required")
        
        # Test credentials with a simple operation request
        try:
            response = self.session.get(
                f"{self.OPERATION_ENDPOINT}?folderId={self.folder_id}",
                timeout=10
            )
            
            if response.status_code == 401:
                raise ExternalAPIError("Invalid Yandex API key")
            elif response.status_code == 403:
                raise ExternalAPIError("Invalid Yandex folder ID or insufficient permissions")
            elif response.status_code >= 400:
                raise ExternalAPIError(f"Credential validation failed: {response.text}")
                
        except requests.RequestException as exc:
            raise ExternalAPIError(f"Failed to validate credentials: {exc}")
    
    def transcribe_audio_sync(self, audio_path: Path, 
                            config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transcribe audio using synchronous API (for files < 1 minute).
        
        Args:
            audio_path: Path to audio file
            config: Optional transcription configuration
            
        Returns:
            Transcription result dictionary
            
        Raises:
            ExternalAPIError: If API request fails
            ProcessingError: If audio file is invalid
        """
        if not audio_path.exists():
            raise ProcessingError(f"Audio file not found: {audio_path}")
        
        # Use default config if none provided
        if not config:
            config = self.CONFIG_TEMPLATES['default']
        
        try:
            # Prepare request data
            request_config = {
                'folderId': self.folder_id,
                **config['specification']
            }
            
            # Read audio file
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Make API request
            response = self.session.post(
                self.SYNC_ENDPOINT,
                params=request_config,
                data=audio_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code != 200:
                error_msg = self._parse_error_response(response)
                raise ExternalAPIError(f"Yandex API error: {error_msg}")
            
            result = response.json()
            
            # Process and format result
            return self._format_sync_result(result, config)
            
        except requests.RequestException as exc:
            raise ExternalAPIError(f"API request failed: {exc}")
        except json.JSONDecodeError as exc:
            raise ExternalAPIError(f"Invalid API response format: {exc}")
    
    def transcribe_audio_async(self, audio_path: Path, 
                             config: Optional[Dict[str, Any]] = None) -> str:
        """
        Start asynchronous audio transcription (for files > 1 minute).
        
        Args:
            audio_path: Path to audio file
            config: Optional transcription configuration
            
        Returns:
            Operation ID for monitoring progress
            
        Raises:
            ExternalAPIError: If API request fails
            ProcessingError: If audio file is invalid
        """
        if not audio_path.exists():
            raise ProcessingError(f"Audio file not found: {audio_path}")
        
        # Use default config if none provided
        if not config:
            config = self.CONFIG_TEMPLATES['default']
        
        try:
            # Prepare request data
            request_data = {
                'folderId': self.folder_id,
                'specification': config['specification'],
                'recognition_config': config.get('recognition_config', {})
            }
            
            # Read and encode audio file
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Prepare multipart form data
            files = {
                'data': ('audio.wav', audio_data, 'application/octet-stream')
            }
            
            data = {
                'config': json.dumps(request_data)
            }
            
            # Make API request
            response = self.session.post(
                self.ASYNC_ENDPOINT,
                files=files,
                data=data,
                timeout=60  # 1 minute timeout for starting operation
            )
            
            if response.status_code != 200:
                error_msg = self._parse_error_response(response)
                raise ExternalAPIError(f"Yandex API error: {error_msg}")
            
            result = response.json()
            operation_id = result.get('id')
            
            if not operation_id:
                raise ExternalAPIError("No operation ID returned from API")
            
            logger.info(f"Started async transcription with operation ID: {operation_id}")
            return operation_id
            
        except requests.RequestException as exc:
            raise ExternalAPIError(f"API request failed: {exc}")
        except json.JSONDecodeError as exc:
            raise ExternalAPIError(f"Invalid API response format: {exc}")
    
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Get status of asynchronous operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Operation status dictionary
            
        Raises:
            ExternalAPIError: If API request fails
        """
        try:
            response = self.session.get(
                f"{self.OPERATION_ENDPOINT}/{operation_id}",
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = self._parse_error_response(response)
                raise ExternalAPIError(f"Operation status request failed: {error_msg}")
            
            return response.json()
            
        except requests.RequestException as exc:
            raise ExternalAPIError(f"Operation status request failed: {exc}")
        except json.JSONDecodeError as exc:
            raise ExternalAPIError(f"Invalid operation status response: {exc}")
    
    def wait_for_completion(self, operation_id: str, 
                          timeout: int = 3600,
                          progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Wait for asynchronous operation to complete.
        
        Args:
            operation_id: Operation identifier
            timeout: Maximum wait time in seconds
            progress_callback: Optional callback for progress updates
            
        Returns:
            Final operation result
            
        Raises:
            ExternalAPIError: If operation fails or times out
        """
        start_time = time.time()
        poll_interval = 5  # Start with 5 second intervals
        max_poll_interval = 30
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_operation_status(operation_id)
                
                if status.get('done'):
                    # Operation completed
                    if 'error' in status:
                        error_msg = status['error'].get('message', 'Unknown error')
                        raise ExternalAPIError(f"Operation failed: {error_msg}")
                    
                    result = status.get('response', {})
                    logger.info(f"Operation {operation_id} completed successfully")
                    return self._format_async_result(result)
                
                # Operation still in progress
                if progress_callback:
                    progress_callback(status)
                
                # Progressive backoff for polling
                time.sleep(poll_interval)
                poll_interval = min(poll_interval * 1.2, max_poll_interval)
                
            except ExternalAPIError:
                raise
            except Exception as exc:
                logger.warning(f"Error checking operation status: {exc}")
                time.sleep(poll_interval)
        
        # Timeout reached
        raise ExternalAPIError(f"Operation {operation_id} timed out after {timeout} seconds")
    
    def _parse_error_response(self, response: requests.Response) -> str:
        """
        Parse error response from Yandex API.
        
        Args:
            response: HTTP response object
            
        Returns:
            Error message string
        """
        try:
            error_data = response.json()
            if 'error' in error_data:
                return error_data['error'].get('message', f'HTTP {response.status_code}')
            return error_data.get('message', f'HTTP {response.status_code}')
        except (json.JSONDecodeError, AttributeError):
            return f'HTTP {response.status_code}: {response.text[:200]}'
    
    def _format_sync_result(self, result: Dict[str, Any], 
                          config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format synchronous transcription result.
        
        Args:
            result: Raw API result
            config: Transcription configuration
            
        Returns:
            Formatted result dictionary
        """
        chunks = result.get('chunks', [])
        
        # Extract transcript text
        transcript_parts = []
        segments = []
        
        for i, chunk in enumerate(chunks):
            alternatives = chunk.get('alternatives', [])
            if alternatives:
                best_alternative = alternatives[0]  # Highest confidence
                text = best_alternative.get('text', '')
                confidence = best_alternative.get('confidence', 0.0)
                
                transcript_parts.append(text)
                
                # Create segment
                segment = {
                    'order': i + 1,
                    'start_time': 0.0,  # Sync API doesn't provide timing
                    'end_time': 0.0,
                    'text': text,
                    'confidence': confidence,
                    'speaker_id': None  # Sync API doesn't provide speaker info
                }
                segments.append(segment)
        
        return {
            'transcript': ' '.join(transcript_parts),
            'segments': segments,
            'speakers': [],
            'confidence': sum(s['confidence'] for s in segments) / len(segments) if segments else 0.0,
            'language_detected': config['specification'].get('languageCode', 'auto'),
            'processing_type': 'synchronous'
        }
    
    def _format_async_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format asynchronous transcription result.
        
        Args:
            result: Raw API result
            
        Returns:
            Formatted result dictionary
        """
        chunks = result.get('chunks', [])
        
        # Extract transcript and segments
        transcript_parts = []
        segments = []
        speakers = set()
        
        for i, chunk in enumerate(chunks):
            alternatives = chunk.get('alternatives', [])
            if alternatives:
                best_alternative = alternatives[0]
                text = best_alternative.get('text', '')
                confidence = best_alternative.get('confidence', 0.0)
                
                # Extract timing information
                start_time = chunk.get('channelTag', 0)
                end_time = start_time + len(text) * 0.1  # Rough estimate
                
                # Extract speaker information
                speaker_tag = chunk.get('speakerTag')
                if speaker_tag:
                    speakers.add(speaker_tag)
                
                transcript_parts.append(text)
                
                segment = {
                    'order': i + 1,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text,
                    'confidence': confidence,
                    'speaker_id': speaker_tag
                }
                segments.append(segment)
        
        # Create speaker list
        speaker_list = [
            {
                'speaker_id': speaker_id,
                'label': f'Speaker {speaker_id}',
                'confidence': 0.8  # Default confidence for speaker identification
            }
            for speaker_id in sorted(speakers)
        ]
        
        return {
            'transcript': ' '.join(transcript_parts),
            'segments': segments,
            'speakers': speaker_list,
            'confidence': sum(s['confidence'] for s in segments) / len(segments) if segments else 0.0,
            'language_detected': 'auto',  # Would need to be extracted from actual result
            'processing_type': 'asynchronous'
        }


class YandexAPIError(ExternalAPIError):
    """Specific exception for Yandex API errors."""
    pass


__all__ = ['YandexSpeechKitClient', 'YandexAPIError']