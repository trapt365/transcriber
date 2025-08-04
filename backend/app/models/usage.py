"""UsageStats model for tracking API costs and system usage."""

from datetime import datetime, date
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, DateTime, Float, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.extensions import db


class UsageStats(db.Model):
    """Model for tracking system usage and API costs."""
    
    __tablename__ = 'usage_stats'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to Job (optional, for job-specific tracking)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True)
    
    # Date tracking
    usage_date = Column(Date, nullable=False, default=date.today)
    
    # Usage metrics
    audio_minutes_processed = Column(Float, nullable=False, default=0.0)
    api_calls_made = Column(Integer, nullable=False, default=0)
    successful_jobs = Column(Integer, nullable=False, default=0)
    failed_jobs = Column(Integer, nullable=False, default=0)
    
    # Cost tracking
    api_cost = Column(Float, nullable=False, default=0.0)  # Cost in currency units
    cost_currency = Column(String(3), nullable=False, default='USD')
    
    # Storage metrics
    storage_used_mb = Column(Float, nullable=False, default=0.0)
    files_processed = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    avg_processing_time = Column(Float, nullable=True)  # Average processing time in seconds
    peak_concurrent_jobs = Column(Integer, nullable=False, default=0)
    
    # Detailed breakdown
    usage_breakdown = Column(JSON, nullable=True)  # Detailed metrics by hour/category
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                       onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", backref="usage_stats")
    
    def __repr__(self) -> str:
        """String representation of UsageStats."""
        return f'<UsageStats {self.usage_date}: {self.audio_minutes_processed}min, ${self.api_cost}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert usage stats to dictionary representation."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'usage_date': self.usage_date.isoformat() if self.usage_date else None,
            'audio_minutes_processed': self.audio_minutes_processed,
            'api_calls_made': self.api_calls_made,
            'successful_jobs': self.successful_jobs,
            'failed_jobs': self.failed_jobs,
            'total_jobs': self.successful_jobs + self.failed_jobs,
            'success_rate': self.get_success_rate(),
            'api_cost': self.api_cost,
            'cost_currency': self.cost_currency,
            'storage_used_mb': self.storage_used_mb,
            'files_processed': self.files_processed,
            'avg_processing_time': self.avg_processing_time,
            'peak_concurrent_jobs': self.peak_concurrent_jobs,
            'usage_breakdown': self.usage_breakdown,
            'cost_per_minute': self.get_cost_per_minute(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def add_job_stats(self, job: 'Job', api_cost: float = 0.0) -> None:
        """Add statistics from a completed job."""
        if job.duration:
            self.audio_minutes_processed += job.duration / 60.0
        
        self.api_calls_made += 1
        self.files_processed += 1
        
        if job.status == 'completed':
            self.successful_jobs += 1
        elif job.status == 'failed':
            self.failed_jobs += 1
        
        if api_cost > 0:
            self.api_cost += api_cost
        
        if job.file_size:
            self.storage_used_mb += job.file_size / (1024 * 1024)
        
        # Update average processing time
        if job.processing_time:
            current_total_time = (self.avg_processing_time or 0) * (self.successful_jobs - 1)
            self.avg_processing_time = (current_total_time + job.processing_time) / self.successful_jobs
        
        self.updated_at = datetime.utcnow()
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_jobs = self.successful_jobs + self.failed_jobs
        if total_jobs == 0:
            return 0.0
        return (self.successful_jobs / total_jobs) * 100
    
    def get_cost_per_minute(self) -> float:
        """Calculate cost per minute of audio processed."""
        if self.audio_minutes_processed == 0:
            return 0.0
        return self.api_cost / self.audio_minutes_processed
    
    def add_hourly_breakdown(self, hour: int, metrics: Dict[str, Any]) -> None:
        """Add hourly usage breakdown."""
        if not self.usage_breakdown:
            self.usage_breakdown = {}
        
        hour_key = f"hour_{hour:02d}"
        self.usage_breakdown[hour_key] = metrics
        self.updated_at = datetime.utcnow()
    
    def get_efficiency_metrics(self) -> Dict[str, float]:
        """Calculate efficiency metrics."""
        return {
            'jobs_per_hour': self.get_jobs_per_hour(),
            'minutes_per_job': self.get_minutes_per_job(),
            'cost_efficiency': self.get_cost_efficiency(),
            'storage_efficiency': self.get_storage_efficiency()
        }
    
    def get_jobs_per_hour(self) -> float:
        """Calculate average jobs processed per hour."""
        total_jobs = self.successful_jobs + self.failed_jobs
        if total_jobs == 0:
            return 0.0
        
        # Assume 24-hour period for daily stats
        return total_jobs / 24.0
    
    def get_minutes_per_job(self) -> float:
        """Calculate average audio minutes per job."""
        total_jobs = self.successful_jobs + self.failed_jobs
        if total_jobs == 0:
            return 0.0
        return self.audio_minutes_processed / total_jobs
    
    def get_cost_efficiency(self) -> float:
        """Calculate cost efficiency (jobs per dollar)."""
        if self.api_cost == 0:
            return 0.0
        return (self.successful_jobs + self.failed_jobs) / self.api_cost
    
    def get_storage_efficiency(self) -> float:
        """Calculate storage efficiency (minutes per MB)."""
        if self.storage_used_mb == 0:
            return 0.0
        return self.audio_minutes_processed / self.storage_used_mb
    
    @classmethod
    def get_or_create_daily(cls, usage_date: date = None) -> 'UsageStats':
        """Get or create daily usage stats record."""
        if usage_date is None:
            usage_date = date.today()
        
        stats = cls.query.filter_by(usage_date=usage_date, job_id=None).first()
        if not stats:
            stats = cls(usage_date=usage_date)
            db.session.add(stats)
            db.session.commit()
        
        return stats
    
    @classmethod
    def get_monthly_summary(cls, year: int, month: int) -> Dict[str, Any]:
        """Get monthly usage summary."""
        monthly_stats = cls.query.filter(
            func.extract('year', cls.usage_date) == year,
            func.extract('month', cls.usage_date) == month,
            cls.job_id.is_(None)
        ).all()
        
        if not monthly_stats:
            return {}
        
        total_minutes = sum(stat.audio_minutes_processed for stat in monthly_stats)
        total_cost = sum(stat.api_cost for stat in monthly_stats)
        total_jobs = sum(stat.successful_jobs + stat.failed_jobs for stat in monthly_stats)
        total_successful = sum(stat.successful_jobs for stat in monthly_stats)
        
        return {
            'year': year,
            'month': month,
            'total_audio_minutes': total_minutes,
            'total_api_cost': total_cost,
            'total_jobs': total_jobs,
            'successful_jobs': total_successful,
            'success_rate': (total_successful / total_jobs * 100) if total_jobs > 0 else 0,
            'avg_cost_per_minute': total_cost / total_minutes if total_minutes > 0 else 0,
            'days_with_activity': len(monthly_stats)
        }
    
    @classmethod
    def get_date_range_summary(cls, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get usage summary for a date range."""
        range_stats = cls.query.filter(
            cls.usage_date >= start_date,
            cls.usage_date <= end_date,
            cls.job_id.is_(None)
        ).all()
        
        if not range_stats:
            return {}
        
        total_minutes = sum(stat.audio_minutes_processed for stat in range_stats)
        total_cost = sum(stat.api_cost for stat in range_stats)
        total_jobs = sum(stat.successful_jobs + stat.failed_jobs for stat in range_stats)
        
        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_audio_minutes': total_minutes,
            'total_api_cost': total_cost,
            'total_jobs': total_jobs,
            'avg_daily_minutes': total_minutes / len(range_stats),
            'avg_daily_cost': total_cost / len(range_stats),
            'days_analyzed': len(range_stats)
        }