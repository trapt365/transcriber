"""Processing service interface for audio transcription operations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.speaker import Speaker
from backend.app.models.segment import TranscriptSegment
from backend.app.utils.exceptions import ProcessingError, ExternalAPIError


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
        self._validate_credentials()
    
    def _validate_credentials(self) -> None:
        """Validate API credentials."""
        if not self.api_key:
            raise ProcessingError("Yandex API key is required")
        if not self.folder_id:
            raise ProcessingError("Yandex folder ID is required")
    
    def process_audio(self, job: Job) -> JobResult:
        """
        Process audio using Yandex SpeechKit.
        
        Implementation will be added in future stories.
        Currently returns a mock result for testing.
        """
        # TODO: Implement actual Yandex SpeechKit integration
        # This is a placeholder implementation for the architecture story
        
        if not job.file_path or not job.file_path.exists():
            raise ProcessingError(f"Audio file not found: {job.file_path}")
        
        # Mock processing result
        result = JobResult(
            job_id=job.id,
            raw_transcript="Mock transcript - implementation pending",
            formatted_transcript="Mock formatted transcript",
            confidence_score=0.95,
            processing_duration=10.5,
            api_response_metadata={
                "provider": "yandex_mock",
                "model": job.model or "base",
                "language": job.language or "auto"
            }
        )
        
        result.calculate_word_count()
        return result
    
    def get_processing_status(self, job_id: str) -> Dict[str, Any]:
        """Get processing status from Yandex API."""
        # TODO: Implement actual status checking
        return {
            "job_id": job_id,
            "status": "processing",
            "progress": 50,
            "estimated_completion": datetime.utcnow().isoformat(),
            "provider": "yandex"
        }
    
    def cancel_processing(self, job_id: str) -> bool:
        """Cancel processing job."""
        # TODO: Implement actual cancellation
        return True
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate Yandex-specific configuration."""
        required_fields = ['language', 'model']
        
        for field in required_fields:
            if field not in config:
                raise ProcessingError(f"Missing required configuration field: {field}")
        
        # Validate language codes
        supported_languages = ['ru', 'en', 'kz', 'auto']
        if config['language'] not in supported_languages:
            raise ProcessingError(
                f"Unsupported language: {config['language']}. "
                f"Supported: {', '.join(supported_languages)}"
            )
        
        # Validate model names
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