"""TranscriptSegment model for timestamped transcript segments."""

from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from backend.extensions import db


class TranscriptSegment(db.Model):
    """Model for storing timestamped transcript segments."""
    
    __tablename__ = 'transcript_segments'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    speaker_id = Column(Integer, ForeignKey('speakers.id'), nullable=True)
    
    # Segment ordering
    segment_order = Column(Integer, nullable=False)  # Sequential order in transcript
    
    # Timing information
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)    # End time in seconds
    
    # Content
    text = Column(Text, nullable=False)  # Segment text
    original_text = Column(Text, nullable=True)  # Original text before formatting
    
    # Confidence and quality
    confidence_score = Column(Float, nullable=True)  # Segment confidence 0-1
    word_count = Column(Integer, nullable=True)
    
    # Segment metadata
    is_silence = Column(Boolean, nullable=False, default=False)
    contains_profanity = Column(Boolean, nullable=False, default=False)
    language_detected = Column(String(10), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                       onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="segments")
    speaker = relationship("Speaker", back_populates="segments")
    
    def __repr__(self) -> str:
        """String representation of TranscriptSegment."""
        return f'<TranscriptSegment {self.id}: {self.start_time}s-{self.end_time}s>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary representation."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'speaker_id': self.speaker_id,
            'segment_order': self.segment_order,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'text': self.text,
            'original_text': self.original_text,
            'confidence_score': self.confidence_score,
            'word_count': self.word_count,
            'is_silence': self.is_silence,
            'contains_profanity': self.contains_profanity,
            'language_detected': self.language_detected,
            'speaker_label': self.speaker.speaker_label if self.speaker else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def duration(self) -> float:
        """Calculate segment duration in seconds."""
        return self.end_time - self.start_time
    
    @property
    def formatted_time_range(self) -> str:
        """Format time range as human-readable string."""
        def format_time(seconds: float) -> str:
            minutes = int(seconds // 60)
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:05.2f}"
        
        return f"{format_time(self.start_time)} - {format_time(self.end_time)}"
    
    def calculate_word_count(self) -> int:
        """Calculate and update word count from text."""
        if not self.text:
            self.word_count = 0
            return 0
        
        # Simple word count (can be enhanced later)
        words = self.text.split()
        self.word_count = len(words)
        return self.word_count
    
    def update_text(self, new_text: str, is_formatted: bool = False) -> None:
        """Update segment text with optional formatting tracking."""
        if not is_formatted and not self.original_text:
            self.original_text = self.text
        
        self.text = new_text
        self.calculate_word_count()
        self.updated_at = datetime.utcnow()
    
    def get_srt_format(self, segment_number: int) -> str:
        """Format segment for SRT subtitle format."""
        def format_srt_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
        
        start_time = format_srt_time(self.start_time)
        end_time = format_srt_time(self.end_time)
        
        speaker_prefix = f"{self.speaker.speaker_label}: " if self.speaker else ""
        
        return f"{segment_number}\n{start_time} --> {end_time}\n{speaker_prefix}{self.text}\n"
    
    def get_vtt_format(self) -> str:
        """Format segment for WebVTT format."""
        def format_vtt_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
            else:
                return f"{minutes:02d}:{secs:06.3f}"
        
        start_time = format_vtt_time(self.start_time)
        end_time = format_vtt_time(self.end_time)
        
        speaker_prefix = f"<v {self.speaker.speaker_label}>" if self.speaker else ""
        
        return f"{start_time} --> {end_time}\n{speaker_prefix}{self.text}\n"
    
    @classmethod
    def find_by_job(cls, job_id: int) -> List['TranscriptSegment']:
        """Find all segments for a specific job, ordered by segment_order."""
        return cls.query.filter_by(job_id=job_id).order_by(cls.segment_order).all()
    
    @classmethod
    def find_by_speaker(cls, speaker_id: int) -> List['TranscriptSegment']:
        """Find all segments for a specific speaker."""
        return cls.query.filter_by(speaker_id=speaker_id).order_by(cls.segment_order).all()
    
    @classmethod
    def find_by_time_range(cls, job_id: int, start_time: float, end_time: float) -> List['TranscriptSegment']:
        """Find segments within a specific time range."""
        return cls.query.filter(
            cls.job_id == job_id,
            cls.start_time >= start_time,
            cls.end_time <= end_time
        ).order_by(cls.segment_order).all()
    
    @classmethod
    def get_segment_count(cls, job_id: int) -> int:
        """Get total number of segments for a job."""
        return cls.query.filter_by(job_id=job_id).count()