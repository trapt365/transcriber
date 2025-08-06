"""Processing service interface for audio transcription operations."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.speaker import Speaker
from backend.app.models.segment import TranscriptSegment
from backend.app.utils.exceptions import ProcessingError, ExternalAPIError
from backend.app.services.yandex_client import YandexSpeechKitClient
from backend.app.services.audio_service import audio_service

logger = logging.getLogger(__name__)


class ProcessingServiceInterface(ABC):
    """Abstract interface for audio processing services."""
    
    @abstractmethod
    def process_audio(self, job: Job) -> JobResult:
        """
        Process audio file for transcription.
        
        Args:
            job: Job object containing file and processing configuration
            
        Returns:
            JobResult with transcription results
            
        Raises:
            ProcessingError: If processing fails
            ExternalAPIError: If external API fails
        """
        pass
    
    @abstractmethod
    def get_processing_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current processing status for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Status information dictionary
        """
        pass
    
    @abstractmethod
    def cancel_processing(self, job_id: str) -> bool:
        """
        Cancel ongoing processing job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancellation successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate processing configuration.
        
        Args:
            config: Processing configuration dictionary
            
        Returns:
            True if configuration is valid
            
        Raises:
            ProcessingError: If configuration is invalid
        """
        pass


class YandexProcessingService(ProcessingServiceInterface):
    """Yandex SpeechKit implementation of processing service."""
    
    def __init__(self, api_key: str, folder_id: str):
        """
        Initialize Yandex processing service.
        
        Args:
            api_key: Yandex API key
            folder_id: Yandex folder ID
        """
        self.api_key = api_key
        self.folder_id = folder_id
        self.client = YandexSpeechKitClient(api_key, folder_id)
        self.active_operations = {}  # Track ongoing operations
    
    def process_audio(self, job: Job) -> JobResult:
        """
        Process audio using Yandex SpeechKit.
        
        Args:
            job: Job object containing audio file and configuration
            
        Returns:
            JobResult with transcription results
            
        Raises:
            ProcessingError: If processing fails
            ExternalAPIError: If API communication fails
        """
        if not job.file_path or not job.file_path.exists():
            raise ProcessingError(f"Audio file not found: {job.file_path}")
        
        processing_start = datetime.utcnow()
        
        try:
            # Analyze audio file to determine processing approach
            audio_metadata = audio_service.analyze_audio_file(job.file_path)
            
            # Preprocess audio for optimal API processing
            processed_audio_path = audio_service.preprocess_for_speechkit(job.file_path)
            
            # Prepare transcription configuration
            config = self._prepare_transcription_config(job, audio_metadata)
            
            # Choose sync vs async based on audio duration
            use_async = audio_metadata['duration'] > 60  # 1 minute threshold
            
            if use_async:
                # Asynchronous processing for longer files
                operation_id = self.client.transcribe_audio_async(processed_audio_path, config)
                
                # Store operation for tracking
                self.active_operations[job.id] = operation_id
                
                # Wait for completion with progress tracking
                def progress_callback(status):
                    # This could be enhanced to provide more detailed progress
                    pass
                
                transcription_result = self.client.wait_for_completion(
                    operation_id, 
                    timeout=3600,  # 1 hour timeout
                    progress_callback=progress_callback
                )
            else:
                # Synchronous processing for shorter files
                transcription_result = self.client.transcribe_audio_sync(processed_audio_path, config)
            
            # Calculate processing duration
            processing_end = datetime.utcnow()
            processing_duration = (processing_end - processing_start).total_seconds()
            
            # Create job result
            result = JobResult(
                job_id=job.id,
                raw_transcript=transcription_result['transcript'],
                formatted_transcript=self._format_transcript(transcription_result),
                confidence_score=transcription_result['confidence'],
                processing_duration=processing_duration,
                api_response_metadata={
                    "provider": "yandex",
                    "model": config['specification'].get('model', 'general'),
                    "language": transcription_result.get('language_detected', 'auto'),
                    "processing_type": transcription_result.get('processing_type', 'unknown'),
                    "speaker_count": len(transcription_result.get('speakers', [])),
                    "segment_count": len(transcription_result.get('segments', [])),
                    "audio_duration": audio_metadata['duration'],
                    "audio_format": audio_metadata['format']
                }
            )
            
            # Calculate word count
            result.calculate_word_count()
            
            # Create speaker and segment objects
            speakers = self.create_speakers_from_diarization(job, transcription_result.get('speakers', []))
            segments = self.create_segments_from_transcript(job, transcription_result.get('segments', []))
            
            # Clean up temporary files
            if processed_audio_path.exists():
                processed_audio_path.unlink()
            
            # Remove from active operations
            self.active_operations.pop(job.id, None)
            
            return result
            
        except Exception as exc:
            # Clean up on error
            self.active_operations.pop(job.id, None)
            
            if isinstance(exc, (ProcessingError, ExternalAPIError)):
                raise
            else:
                raise ProcessingError(f"Audio processing failed: {exc}")
    
    def _prepare_transcription_config(self, job: Job, audio_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare Yandex API configuration based on job settings and audio metadata.
        
        Args:
            job: Job object with user preferences
            audio_metadata: Audio file metadata
            
        Returns:
            API configuration dictionary
        """
        # Start with default template
        config = self.client.CONFIG_TEMPLATES['default'].copy()
        
        # Update based on job settings
        if job.language and job.language != 'auto':
            config['specification']['languageCode'] = job.language
        
        if job.model:
            # Map internal model names to Yandex models
            model_mapping = {
                'base': 'general',
                'small': 'general',
                'large': 'general'
            }
            config['specification']['model'] = model_mapping.get(job.model, 'general')
        
        # Adjust based on audio characteristics
        if audio_metadata['sample_rate'] != 16000:
            config['specification']['sampleRateHertz'] = audio_metadata['sample_rate']
        
        # Determine audio format
        if audio_metadata['codec'] == 'pcm_s16le':
            config['specification']['format'] = 'lpcm'
        elif audio_metadata['format'] in ['mp3', 'mpeg']:
            config['specification']['format'] = 'mp3'
        elif audio_metadata['format'] in ['ogg']:
            config['specification']['format'] = 'oggopus'
        
        # Enable speaker diarization for longer files or if requested
        if audio_metadata['duration'] > 30 or job.language in ['ru', 'en']:
            config['recognition_config']['enable_speaker_diarization'] = True
            config['recognition_config']['max_speaker_count'] = min(10, max(2, int(audio_metadata['duration'] / 60)))
        
        return config
    
    def _format_transcript(self, transcription_result: Dict[str, Any]) -> str:
        """
        Format raw transcript with better structure and punctuation.
        
        Args:
            transcription_result: Raw transcription result
            
        Returns:
            Formatted transcript string
        """
        segments = transcription_result.get('segments', [])
        
        if not segments:
            return transcription_result.get('transcript', '')
        
        formatted_parts = []
        current_speaker = None
        
        for segment in segments:
            speaker_id = segment.get('speaker_id')
            text = segment.get('text', '').strip()
            
            if not text:
                continue
            
            # Add speaker labels for diarized content
            if speaker_id and speaker_id != current_speaker:
                if formatted_parts:  # Add line break between speakers
                    formatted_parts.append('\n')
                formatted_parts.append(f"[Speaker {speaker_id}]: ")
                current_speaker = speaker_id
            
            formatted_parts.append(text)
            
            # Add appropriate spacing
            if not text.endswith(('.', '!', '?', ':')):
                formatted_parts.append(' ')
        
        return ''.join(formatted_parts).strip()
    
    def get_processing_status(self, job_id: str) -> Dict[str, Any]:
        """Get processing status from Yandex API."""
        operation_id = self.active_operations.get(job_id)
        
        if not operation_id:
            return {
                "job_id": job_id,
                "status": "unknown",
                "progress": 0,
                "provider": "yandex",
                "error": "No active operation found for job"
            }
        
        try:
            operation_status = self.client.get_operation_status(operation_id)
            
            if operation_status.get('done'):
                if 'error' in operation_status:
                    return {
                        "job_id": job_id,
                        "status": "failed",
                        "progress": 0,
                        "provider": "yandex",
                        "error": operation_status['error'].get('message', 'Unknown error')
                    }
                else:
                    return {
                        "job_id": job_id,
                        "status": "completed",
                        "progress": 100,
                        "provider": "yandex"
                    }
            else:
                # Operation still in progress - estimate progress based on time
                return {
                    "job_id": job_id,
                    "status": "processing",
                    "progress": 50,  # Could be improved with better progress estimation
                    "provider": "yandex",
                    "operation_id": operation_id
                }
                
        except ExternalAPIError as exc:
            return {
                "job_id": job_id,
                "status": "error",
                "progress": 0,
                "provider": "yandex",
                "error": str(exc)
            }
    
    def cancel_processing(self, job_id: str) -> bool:
        """Cancel processing job."""
        operation_id = self.active_operations.get(job_id)
        
        if not operation_id:
            return False  # No active operation to cancel
        
        try:
            # Note: Yandex API might not support operation cancellation
            # This would need to be implemented based on API capabilities
            # For now, we just remove from our tracking
            self.active_operations.pop(job_id, None)
            return True
            
        except Exception as exc:
            logger.error(f"Failed to cancel job {job_id}: {exc}")
            return False
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate Yandex-specific configuration."""
        # Validate language codes
        if 'language' in config:
            supported_languages = ['ru', 'en', 'kz', 'auto']
            if config['language'] not in supported_languages:
                raise ProcessingError(
                    f"Unsupported language: {config['language']}. "
                    f"Supported: {', '.join(supported_languages)}"
                )
        
        # Validate model names
        if 'model' in config:
            supported_models = ['base', 'small', 'large']
            if config['model'] not in supported_models:
                raise ProcessingError(
                    f"Unsupported model: {config['model']}. "
                    f"Supported: {', '.join(supported_models)}"
                )
        
        return True
    
    def create_speakers_from_diarization(self, job: Job, 
                                       diarization_data: List[Dict]) -> List[Speaker]:
        """
        Create Speaker objects from diarization data.
        
        Args:
            job: Job object
            diarization_data: List of speaker diarization information
            
        Returns:
            List of Speaker objects
        """
        speakers = []
        
        for speaker_data in diarization_data:
            speaker = Speaker(
                job_id=job.id,
                speaker_id=speaker_data.get('speaker_id', 'unknown'),
                speaker_label=speaker_data.get('label'),
                confidence_score=speaker_data.get('confidence', 0.0),
                voice_characteristics=speaker_data.get('characteristics', {})
            )
            speakers.append(speaker)
        
        return speakers
    
    def create_segments_from_transcript(self, job: Job, 
                                      transcript_data: List[Dict]) -> List[TranscriptSegment]:
        """
        Create TranscriptSegment objects from transcript data.
        
        Args:
            job: Job object
            transcript_data: List of transcript segment information
            
        Returns:
            List of TranscriptSegment objects
        """
        segments = []
        
        for i, segment_data in enumerate(transcript_data):
            segment = TranscriptSegment(
                job_id=job.id,
                segment_order=i + 1,
                start_time=segment_data.get('start_time', 0.0),
                end_time=segment_data.get('end_time', 0.0),
                text=segment_data.get('text', ''),
                original_text=segment_data.get('original_text'),
                confidence_score=segment_data.get('confidence', 0.0),
                language_detected=segment_data.get('language')
            )
            
            segment.calculate_word_count()
            segments.append(segment)
        
        return segments


class MockProcessingService(ProcessingServiceInterface):
    """Mock processing service for testing and development."""
    
    def __init__(self):
        """Initialize mock processing service."""
        self.processing_jobs = {}  # Track mock processing jobs
    
    def process_audio(self, job: Job) -> JobResult:
        """Mock audio processing."""
        # Simulate processing
        result = JobResult(
            job_id=job.id,
            raw_transcript=f"Mock transcript for {job.original_filename}",
            formatted_transcript=f"Formatted mock transcript for {job.original_filename}",
            confidence_score=0.85,
            processing_duration=5.0,
            api_response_metadata={
                "provider": "mock",
                "mock_mode": True,
                "processed_at": datetime.utcnow().isoformat()
            }
        )
        
        result.calculate_word_count()
        return result
    
    def get_processing_status(self, job_id: str) -> Dict[str, Any]:
        """Get mock processing status."""
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "provider": "mock",
            "mock_mode": True
        }
    
    def cancel_processing(self, job_id: str) -> bool:
        """Mock cancellation - always succeeds."""
        if job_id in self.processing_jobs:
            del self.processing_jobs[job_id]
        return True
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Mock validation - accepts any configuration."""
        return True


def create_processing_service(provider: str = "yandex", **kwargs) -> ProcessingServiceInterface:
    """
    Factory function to create processing service instances.
    
    Args:
        provider: Processing service provider ('yandex' or 'mock')
        **kwargs: Provider-specific configuration
        
    Returns:
        ProcessingServiceInterface implementation
        
    Raises:
        ProcessingError: If provider is unsupported or configuration is invalid
    """
    if provider == "yandex":
        api_key = kwargs.get('api_key')
        folder_id = kwargs.get('folder_id')
        
        if not api_key or not folder_id:
            raise ProcessingError(
                "Yandex processing service requires 'api_key' and 'folder_id'"
            )
        
        return YandexProcessingService(api_key=api_key, folder_id=folder_id)
    
    elif provider == "mock":
        return MockProcessingService()
    
    else:
        raise ProcessingError(f"Unsupported processing provider: {provider}")


# Backward compatibility alias
ProcessingService = YandexProcessingService