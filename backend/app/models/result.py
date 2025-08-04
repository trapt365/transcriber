"""JobResult model for storing transcription results."""

from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.extensions import db


class JobResult(db.Model):
    """Model for storing transcription results."""
    
    __tablename__ = 'job_results'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to Job
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    
    # Transcription results
    raw_transcript = Column(Text, nullable=True)  # Raw text from STT API
    formatted_transcript = Column(Text, nullable=True)  # Formatted/cleaned text
    
    # Confidence and quality metrics
    confidence_score = Column(Float, nullable=True)  # Overall confidence 0-1
    word_count = Column(Integer, nullable=True)
    
    # API response metadata
    api_response_metadata = Column(JSON, nullable=True)  # Raw API response
    processing_duration = Column(Float, nullable=True)  # Processing time in seconds
    
    # Export tracking
    export_formats_generated = Column(JSON, nullable=True)  # List of generated formats
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                       onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="results")
    
    def __repr__(self) -> str:
        """String representation of JobResult."""
        return f'<JobResult {self.id}: Job {self.job_id}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'raw_transcript': self.raw_transcript,
            'formatted_transcript': self.formatted_transcript,
            'confidence_score': self.confidence_score,
            'word_count': self.word_count,
            'processing_duration': self.processing_duration,
            'export_formats_generated': self.export_formats_generated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_export_status(self, format_name: str) -> bool:
        """Check if specific export format has been generated."""
        if not self.export_formats_generated:
            return False
        return format_name in self.export_formats_generated
    
    def add_export_format(self, format_name: str) -> None:
        """Add export format to generated list."""
        if not self.export_formats_generated:
            self.export_formats_generated = []
        
        if format_name not in self.export_formats_generated:
            self.export_formats_generated.append(format_name)
            self.updated_at = datetime.utcnow()
    
    def calculate_word_count(self) -> int:
        """Calculate and update word count from formatted transcript."""
        if not self.formatted_transcript:
            self.word_count = 0
            return 0
        
        # Simple word count (can be enhanced later)
        words = self.formatted_transcript.split()
        self.word_count = len(words)
        return self.word_count
    
    @classmethod
    def find_by_job(cls, job_id: int) -> Optional['JobResult']:
        """Find result by job ID."""
        return cls.query.filter_by(job_id=job_id).first()
    
    @classmethod
    def find_with_export_format(cls, format_name: str) -> list['JobResult']:
        """Find results that have generated specific export format."""
        return cls.query.filter(
            cls.export_formats_generated.contains([format_name])
        ).all()