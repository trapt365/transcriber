"""Processing history model for tracking performance metrics."""

from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Column, Integer, BigInteger, Float, DateTime

from backend.extensions import db


class ProcessingHistory(db.Model):
    """Model for tracking processing performance history."""
    
    __tablename__ = 'processing_history'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Processing metrics
    file_size = Column(BigInteger, nullable=False)  # File size in bytes
    processing_duration = Column(Float, nullable=False)  # Duration in seconds
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        """String representation of ProcessingHistory."""
        return f'<ProcessingHistory {self.id}: {self.file_size}B in {self.processing_duration}s>'
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'file_size': self.file_size,
            'processing_duration': self.processing_duration,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def add_processing_record(cls, file_size: int, processing_duration: float) -> 'ProcessingHistory':
        """Add a new processing history record."""
        record = cls(
            file_size=file_size,
            processing_duration=processing_duration
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    @classmethod
    def get_average_processing_time(cls, file_size_mb: float, sample_size: int = 50) -> Optional[float]:
        """Get average processing time for similar file sizes."""
        # Convert MB to bytes for query
        file_size_bytes = int(file_size_mb * 1024 * 1024)
        
        # Find records within 20% of the file size
        size_range = int(file_size_bytes * 0.2)
        min_size = file_size_bytes - size_range
        max_size = file_size_bytes + size_range
        
        # Get recent records within size range
        records = cls.query.filter(
            cls.file_size >= min_size,
            cls.file_size <= max_size
        ).order_by(cls.created_at.desc()).limit(sample_size).all()
        
        if not records:
            return None
        
        # Calculate average processing time
        total_time = sum(record.processing_duration for record in records)
        return total_time / len(records)
    
    @classmethod
    def cleanup_old_records(cls, keep_days: int = 30) -> int:
        """Clean up old processing history records."""
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        deleted = cls.query.filter(cls.created_at < cutoff_date).delete()
        db.session.commit()
        return deleted