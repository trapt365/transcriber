"""Job model for managing transcription jobs."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.orm import relationship

from backend.extensions import db
from .enums import JobStatus, AudioFormat


class Job(db.Model):
    """Main job model for tracking transcription jobs."""
    
    __tablename__ = 'jobs'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # External identifier (UUID)
    job_id = Column(String(36), unique=True, nullable=False, 
                   default=lambda: str(uuid.uuid4()))
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_format = Column(String(10), nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to uploaded file
    
    # Processing status
    status = Column(String(20), nullable=False, default=JobStatus.UPLOADED.value)
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, 
                       default=lambda: datetime.utcnow() + timedelta(hours=24))
    
    # Audio metadata
    duration = Column(Float, nullable=True)  # Duration in seconds
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    
    # Processing configuration
    language = Column(String(10), nullable=True, default='auto')
    enable_diarization = Column(Boolean, nullable=False, default=True)
    model = Column(String(50), nullable=True, default='base')
    
    # Relationships
    results = relationship("JobResult", back_populates="job", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="job", cascade="all, delete-orphan")
    segments = relationship("TranscriptSegment", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation of Job."""
        return f'<Job {self.job_id}: {self.status}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary representation."""
        return {
            'job_id': self.job_id,
            'filename': self.original_filename,
            'file_size': self.file_size,
            'file_format': self.file_format,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'language': self.language,
            'enable_diarization': self.enable_diarization,
            'model': self.model
        }
    
    def update_status(self, new_status: JobStatus, error_message: Optional[str] = None) -> bool:
        """Update job status with validation."""
        current_status = JobStatus(self.status)
        
        if not current_status.can_transition_to(new_status):
            return False
        
        self.status = new_status.value
        
        if new_status == JobStatus.PROCESSING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            self.completed_at = datetime.utcnow()
            if new_status == JobStatus.COMPLETED:
                self.progress = 100
        
        if error_message:
            self.error_message = error_message
        
        return True
    
    @property
    def is_expired(self) -> bool:
        """Check if job has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def processing_time(self) -> Optional[float]:
        """Calculate processing time in seconds."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    @classmethod
    def find_by_job_id(cls, job_id: str) -> Optional['Job']:
        """Find job by external job_id."""
        return cls.query.filter_by(job_id=job_id).first()
    
    @classmethod
    def find_expired(cls) -> list['Job']:
        """Find all expired jobs."""
        return cls.query.filter(cls.expires_at < datetime.utcnow()).all()
    
    @classmethod
    def find_by_status(cls, status: JobStatus) -> list['Job']:
        """Find jobs by status."""
        return cls.query.filter_by(status=status.value).all()