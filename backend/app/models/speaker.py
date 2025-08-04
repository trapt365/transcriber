"""Speaker model for diarization information."""

from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.extensions import db


class Speaker(db.Model):
    """Model for storing speaker diarization information."""
    
    __tablename__ = 'speakers'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to Job
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    
    # Speaker identification
    speaker_id = Column(String(50), nullable=False)  # API-provided speaker ID
    speaker_label = Column(String(100), nullable=True)  # Human-readable label
    
    # Speaker statistics
    total_speech_time = Column(Float, nullable=True)  # Total speaking time in seconds
    segment_count = Column(Integer, nullable=True)  # Number of segments
    
    # Speaker metadata
    confidence_score = Column(Float, nullable=True)  # Overall speaker confidence
    voice_characteristics = Column(JSON, nullable=True)  # Voice analysis data
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                       onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="speakers")
    segments = relationship("TranscriptSegment", back_populates="speaker")
    
    def __repr__(self) -> str:
        """String representation of Speaker."""
        return f'<Speaker {self.speaker_id}: Job {self.job_id}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert speaker to dictionary representation."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'speaker_id': self.speaker_id,
            'speaker_label': self.speaker_label or f"Speaker {self.speaker_id}",
            'total_speech_time': self.total_speech_time,
            'segment_count': self.segment_count,
            'confidence_score': self.confidence_score,
            'voice_characteristics': self.voice_characteristics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calculate_speech_statistics(self) -> Dict[str, float]:
        """Calculate speech statistics from associated segments."""
        if not self.segments:
            return {'total_time': 0.0, 'segment_count': 0, 'avg_segment_length': 0.0}
        
        total_time = sum(
            segment.end_time - segment.start_time 
            for segment in self.segments 
            if segment.start_time and segment.end_time
        )
        
        segment_count = len(self.segments)
        avg_segment_length = total_time / segment_count if segment_count > 0 else 0.0
        
        # Update model fields
        self.total_speech_time = total_time
        self.segment_count = segment_count
        self.updated_at = datetime.utcnow()
        
        return {
            'total_time': total_time,
            'segment_count': segment_count,
            'avg_segment_length': avg_segment_length
        }
    
    def get_speaking_percentage(self, total_duration: float) -> float:
        """Calculate percentage of total audio this speaker spoke."""
        if not self.total_speech_time or total_duration <= 0:
            return 0.0
        
        return (self.total_speech_time / total_duration) * 100
    
    def set_label(self, label: str) -> None:
        """Set human-readable speaker label."""
        self.speaker_label = label
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def find_by_job(cls, job_id: int) -> List['Speaker']:
        """Find all speakers for a specific job."""
        return cls.query.filter_by(job_id=job_id).order_by(cls.speaker_id).all()
    
    @classmethod
    def find_by_speaker_id(cls, job_id: int, speaker_id: str) -> Optional['Speaker']:
        """Find specific speaker by job and speaker ID."""
        return cls.query.filter_by(job_id=job_id, speaker_id=speaker_id).first()
    
    @classmethod
    def get_speaker_count(cls, job_id: int) -> int:
        """Get total number of speakers for a job."""
        return cls.query.filter_by(job_id=job_id).count()