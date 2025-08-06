"""Enums for database models and application logic."""

from enum import Enum


class JobStatus(Enum):
    """Job processing status enumeration."""
    
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    GENERATING_OUTPUT = "generating_output"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    @classmethod
    def valid_transitions(cls) -> dict:
        """Return valid status transitions."""
        return {
            cls.UPLOADED: [cls.QUEUED, cls.FAILED, cls.CANCELLED],
            cls.QUEUED: [cls.PROCESSING, cls.FAILED, cls.CANCELLED],
            cls.PROCESSING: [cls.GENERATING_OUTPUT, cls.FAILED, cls.CANCELLED],
            cls.GENERATING_OUTPUT: [cls.COMPLETED, cls.FAILED],
            cls.COMPLETED: [],  # Terminal state
            cls.FAILED: [],  # Terminal state
            cls.CANCELLED: []  # Terminal state
        }
    
    def can_transition_to(self, new_status: 'JobStatus') -> bool:
        """Check if transition to new status is valid."""
        valid_next = self.valid_transitions().get(self, [])
        return new_status in valid_next


class AudioFormat(Enum):
    """Supported audio formats."""
    
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    M4A = "m4a"
    OGG = "ogg"


class ExportFormat(Enum):
    """Export format options."""
    
    JSON = "json"
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"
    CSV = "csv"