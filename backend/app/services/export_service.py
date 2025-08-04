"""Export service for generating transcription results in various formats."""

import json
import csv
from abc import ABC, abstractmethod
from io import StringIO
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from backend.app.models.job import Job
from backend.app.models.result import JobResult
from backend.app.models.speaker import Speaker
from backend.app.models.segment import TranscriptSegment
from backend.app.models.enums import ExportFormat
from backend.app.utils.exceptions import ExportError


class ExportServiceInterface(ABC):
    """Abstract interface for export services."""
    
    @abstractmethod
    def export_transcript(self, job: Job, format_type: ExportFormat) -> str:
        """
        Export transcript in specified format.
        
        Args:
            job: Job object with transcript data
            format_type: Export format type
            
        Returns:
            Exported content as string
            
        Raises:
            ExportError: If export fails
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[ExportFormat]:
        """
        Get list of supported export formats.
        
        Returns:
            List of supported ExportFormat values
        """
        pass
    
    @abstractmethod
    def validate_export_data(self, job: Job) -> bool:
        """
        Validate that job has necessary data for export.
        
        Args:
            job: Job object to validate
            
        Returns:
            True if data is valid for export
            
        Raises:
            ExportError: If data is invalid
        """
        pass


class TranscriptExportService(ExportServiceInterface):
    """Default implementation of transcript export service."""
    
    def __init__(self, export_folder: Optional[str] = None):
        """
        Initialize export service.
        
        Args:
            export_folder: Optional folder for saving export files
        """
        self.export_folder = Path(export_folder) if export_folder else None
        if self.export_folder:
            self.export_folder.mkdir(parents=True, exist_ok=True)
    
    def export_transcript(self, job: Job, format_type: ExportFormat) -> str:
        """Export transcript in specified format."""
        self.validate_export_data(job)
        
        if format_type == ExportFormat.JSON:
            return self._export_json(job)
        elif format_type == ExportFormat.TXT:
            return self._export_txt(job)
        elif format_type == ExportFormat.SRT:
            return self._export_srt(job)
        elif format_type == ExportFormat.VTT:
            return self._export_vtt(job)
        elif format_type == ExportFormat.CSV:
            return self._export_csv(job)
        else:
            raise ExportError(f"Unsupported export format: {format_type}")
    
    def get_supported_formats(self) -> List[ExportFormat]:
        """Get supported export formats."""
        return [
            ExportFormat.JSON,
            ExportFormat.TXT,
            ExportFormat.SRT,
            ExportFormat.VTT,
            ExportFormat.CSV
        ]
    
    def validate_export_data(self, job: Job) -> bool:
        """Validate job data for export."""
        if not job:
            raise ExportError("Job object is required")
        
        if not job.results:
            raise ExportError("Job has no transcription results")
        
        result = job.results[0]  # Get first (primary) result
        if not result.formatted_transcript and not result.raw_transcript:
            raise ExportError("Job has no transcript content")
        
        return True
    
    def _export_json(self, job: Job) -> str:
        """Export transcript as JSON."""
        result = job.results[0]
        
        export_data = {
            "job_info": {
                "job_id": job.job_id,
                "filename": job.original_filename,
                "duration": job.duration,
                "language": job.language,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            },
            "transcript": {
                "text": result.formatted_transcript or result.raw_transcript,
                "word_count": result.word_count,
                "confidence_score": result.confidence_score
            },
            "speakers": [],
            "segments": [],
            "metadata": {
                "export_format": "json",
                "exported_at": datetime.utcnow().isoformat(),
                "processing_duration": result.processing_duration
            }
        }
        
        # Add speaker information
        for speaker in job.speakers:
            export_data["speakers"].append({
                "speaker_id": speaker.speaker_id,
                "label": speaker.speaker_label,
                "total_speech_time": speaker.total_speech_time,
                "confidence_score": speaker.confidence_score
            })
        
        # Add segment information
        for segment in job.segments:
            segment_data = {
                "order": segment.segment_order,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "duration": segment.duration,
                "text": segment.text,
                "confidence_score": segment.confidence_score,
                "word_count": segment.word_count
            }
            
            if segment.speaker:
                segment_data["speaker"] = {
                    "id": segment.speaker.speaker_id,
                    "label": segment.speaker.speaker_label
                }
            
            export_data["segments"].append(segment_data)
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def _export_txt(self, job: Job) -> str:
        """Export transcript as plain text."""
        result = job.results[0]
        
        lines = []
        
        # Header
        lines.append(f"Transcript: {job.original_filename}")
        lines.append(f"Job ID: {job.job_id}")
        if job.duration:
            lines.append(f"Duration: {job.duration:.2f} seconds")
        if job.completed_at:
            lines.append(f"Completed: {job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("-" * 50)
        lines.append("")
        
        # If we have segments with speakers, use them
        if job.segments:
            for segment in sorted(job.segments, key=lambda x: x.segment_order):
                if segment.speaker and segment.speaker.speaker_label:
                    speaker_label = segment.speaker.speaker_label
                else:
                    speaker_label = "Unknown Speaker"
                
                timestamp = f"[{segment.start_time:.2f}s - {segment.end_time:.2f}s]"
                lines.append(f"{speaker_label} {timestamp}: {segment.text}")
        else:
            # Fallback to plain transcript
            lines.append(result.formatted_transcript or result.raw_transcript)
        
        lines.append("")
        lines.append("-" * 50)
        lines.append(f"Word count: {result.word_count or 'Unknown'}")
        if result.confidence_score:
            lines.append(f"Confidence: {result.confidence_score:.2%}")
        
        return "\n".join(lines)
    
    def _export_srt(self, job: Job) -> str:
        """Export transcript as SRT subtitle format."""
        if not job.segments:
            raise ExportError("SRT export requires segmented transcript data")
        
        srt_content = []
        
        for i, segment in enumerate(sorted(job.segments, key=lambda x: x.segment_order), 1):
            srt_content.append(segment.get_srt_format(i))
        
        return "\n".join(srt_content)
    
    def _export_vtt(self, job: Job) -> str:
        """Export transcript as WebVTT format."""
        if not job.segments:
            raise ExportError("VTT export requires segmented transcript data")
        
        vtt_lines = ["WEBVTT", ""]
        
        # Add metadata
        vtt_lines.append(f"NOTE Created from: {job.original_filename}")
        vtt_lines.append(f"NOTE Job ID: {job.job_id}")
        if job.completed_at:
            vtt_lines.append(f"NOTE Completed: {job.completed_at.isoformat()}")
        vtt_lines.append("")
        
        # Add segments
        for segment in sorted(job.segments, key=lambda x: x.segment_order):
            vtt_lines.append(segment.get_vtt_format())
        
        return "\n".join(vtt_lines)
    
    def _export_csv(self, job: Job) -> str:
        """Export transcript as CSV format."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header row
        headers = [
            'segment_order', 'start_time', 'end_time', 'duration',
            'speaker_id', 'speaker_label', 'text', 'word_count', 'confidence_score'
        ]
        writer.writerow(headers)
        
        if job.segments:
            # Write segment data
            for segment in sorted(job.segments, key=lambda x: x.segment_order):
                row = [
                    segment.segment_order,
                    segment.start_time,
                    segment.end_time,
                    segment.duration,
                    segment.speaker.speaker_id if segment.speaker else '',
                    segment.speaker.speaker_label if segment.speaker else '',
                    segment.text,
                    segment.word_count or 0,
                    segment.confidence_score or 0.0
                ]
                writer.writerow(row)
        else:
            # Fallback: single row with full transcript
            result = job.results[0]
            row = [
                1, 0.0, job.duration or 0.0, job.duration or 0.0,
                '', '', result.formatted_transcript or result.raw_transcript,
                result.word_count or 0, result.confidence_score or 0.0
            ]
            writer.writerow(row)
        
        return output.getvalue()
    
    def save_export(self, job: Job, format_type: ExportFormat, 
                   content: str = None) -> str:
        """
        Save exported content to file.
        
        Args:
            job: Job object
            format_type: Export format
            content: Optional pre-generated content (will generate if None)
            
        Returns:
            Path to saved file
            
        Raises:
            ExportError: If saving fails
        """
        if not self.export_folder:
            raise ExportError("Export folder not configured")
        
        if content is None:
            content = self.export_transcript(job, format_type)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{job.job_id}_{timestamp}.{format_type.value}"
        file_path = self.export_folder / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update job result with export info
            if job.results:
                result = job.results[0]
                result.add_export_format(format_type.value)
            
            return str(file_path)
            
        except Exception as e:
            raise ExportError(f"Failed to save export file: {str(e)}") from e
    
    def get_export_stats(self, job: Job) -> Dict[str, Any]:
        """
        Get export statistics for a job.
        
        Args:
            job: Job object
            
        Returns:
            Export statistics dictionary
        """
        if not job.results:
            return {"error": "No results available"}
        
        result = job.results[0]
        
        stats = {
            "job_id": job.job_id,
            "transcript_length": len(result.formatted_transcript or result.raw_transcript or ""),
            "word_count": result.word_count or 0,
            "segment_count": len(job.segments) if job.segments else 0,
            "speaker_count": len(job.speakers) if job.speakers else 0,
            "available_formats": [fmt.value for fmt in self.get_supported_formats()],
            "generated_exports": result.export_formats_generated or [],
            "can_export_timed": bool(job.segments),
            "confidence_score": result.confidence_score
        }
        
        return stats


def create_export_service(export_folder: str = None) -> ExportServiceInterface:
    """
    Factory function to create export service instances.
    
    Args:
        export_folder: Optional folder for saving export files
        
    Returns:
        ExportServiceInterface implementation
    """
    return TranscriptExportService(export_folder=export_folder)