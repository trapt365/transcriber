"""Transcript formatting service for generating formatted transcripts."""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models import Job, JobResult, Speaker, TranscriptSegment
from backend.app.utils.formatters import format_time_mmss, format_time_hhmmss


class TranscriptFormatter:
    """Service for formatting transcripts with speaker labels and timestamps."""
    
    def __init__(self, db_session: Session):
        """Initialize formatter with database session."""
        self.db_session = db_session
    
    def format_transcript(self, job_id: str) -> Dict[str, Any]:
        """
        Format complete transcript for a job with speaker labels and timestamps.
        
        Args:
            job_id: External job identifier
            
        Returns:
            Dict containing formatted transcript data
            
        Raises:
            ValueError: If job not found or transcript data incomplete
        """
        job = Job.find_by_job_id(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        # Check if transcript data is complete
        if not job.has_complete_transcript():
            raise ValueError(f"Incomplete transcript data for job: {job_id}")
        
        # Get complete transcript data with optimized queries
        transcript_data = job.get_complete_transcript_data()
        if not transcript_data:
            raise ValueError(f"No transcript data found for job: {job_id}")
        
        segments = transcript_data['segments']
        speakers = transcript_data['speakers']
        speaker_map = {speaker.id: speaker for speaker in speakers}
        
        # Format segments
        formatted_segments = []
        current_speaker = None
        paragraph_text = ""
        paragraph_start_time = None
        
        for segment in segments:
            speaker = speaker_map.get(segment.speaker_id)
            speaker_label = self._get_speaker_label(speaker)
            
            # Start new paragraph if speaker changes
            if current_speaker != speaker_label:
                if paragraph_text:  # Save previous paragraph
                    formatted_segments.append({
                        'speaker': current_speaker,
                        'text': paragraph_text.strip(),
                        'start_time': paragraph_start_time,
                        'end_time': segments[len(formatted_segments) - 1].end_time if formatted_segments else segment.start_time
                    })
                
                # Start new paragraph
                current_speaker = speaker_label
                paragraph_text = segment.text
                paragraph_start_time = segment.start_time
            else:
                # Continue current paragraph
                paragraph_text += " " + segment.text
        
        # Add final paragraph
        if paragraph_text:
            formatted_segments.append({
                'speaker': current_speaker,
                'text': paragraph_text.strip(),
                'start_time': paragraph_start_time,
                'end_time': segments[-1].end_time
            })
        
        # Generate formatted transcript text
        formatted_text = self._generate_formatted_text(formatted_segments)
        
        # Get job result for metadata
        job_result = JobResult.find_by_job(job.id)
        
        return {
            'job_id': job_id,
            'segments': formatted_segments,
            'formatted_text': formatted_text,
            'preview': formatted_text[:500] if formatted_text else "",
            'speaker_count': len(speakers),
            'total_segments': len(segments),
            'total_duration': segments[-1].end_time if segments else 0,
            'confidence_score': job_result.confidence_score if job_result else None,
            'metadata': {
                'language_detected': job.language,
                'processing_time': job.processing_time,
                'created_at': segments[0].created_at.isoformat() if segments else None
            }
        }
    
    def _get_speaker_label(self, speaker: Optional[Speaker]) -> str:
        """Get formatted speaker label."""
        if not speaker:
            return "Unknown Speaker"
        
        if speaker.speaker_label:
            return speaker.speaker_label
        
        return f"Speaker {speaker.speaker_id}"
    
    def _generate_formatted_text(self, segments: List[Dict[str, Any]]) -> str:
        """Generate formatted transcript text from segments."""
        lines = []
        
        for segment in segments:
            start_time = segment['start_time']
            speaker = segment['speaker']
            text = segment['text']
            
            # Use appropriate time format based on duration
            if start_time >= 3600:  # 1 hour or more
                timestamp = format_time_hhmmss(start_time)
            else:
                timestamp = format_time_mmss(start_time)
            
            # Format: [MM:SS] Speaker Name: Text content
            line = f"[{timestamp}] {speaker}: {text}"
            lines.append(line)
        
        return "\n\n".join(lines)
    
    def save_formatted_transcript(self, job_id: str) -> bool:
        """
        Format and save transcript to JobResult.
        
        Args:
            job_id: External job identifier
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            formatted_data = self.format_transcript(job_id)
            
            job = Job.find_by_job_id(job_id)
            if not job:
                return False
            
            job_result = JobResult.find_by_job(job.id)
            if not job_result:
                return False
            
            # Update formatted transcript
            job_result.formatted_transcript = formatted_data['formatted_text']
            job_result.word_count = len(formatted_data['formatted_text'].split())
            
            self.db_session.commit()
            return True
            
        except Exception:
            self.db_session.rollback()
            return False
    
    def validate_transcript_data(self, job_id: str) -> Dict[str, Any]:
        """
        Validate transcript data completeness and quality.
        
        Args:
            job_id: External job identifier
            
        Returns:
            Dict with validation results
        """
        try:
            job = Job.find_by_job_id(job_id)
            if not job:
                return {
                    'valid': False,
                    'errors': ['Job not found'],
                    'warnings': []
                }
            
            # Use optimized data retrieval
            transcript_data = job.get_complete_transcript_data()
            if not transcript_data:
                return {
                    'valid': False,
                    'errors': ['No transcript data available'],
                    'warnings': []
                }
            
            segments = transcript_data['segments']
            speakers = transcript_data['speakers']
            
            errors = []
            warnings = []
            
            # Check for empty results
            if not segments:
                errors.append("No transcript segments found")
            
            if not speakers:
                warnings.append("No speakers detected")
            
            # Check segment continuity
            if len(segments) > 1:
                for i in range(1, len(segments)):
                    prev_segment = segments[i-1]
                    curr_segment = segments[i]
                    
                    # Check for time overlaps or large gaps
                    if curr_segment.start_time < prev_segment.end_time:
                        warnings.append(f"Segment overlap at {curr_segment.start_time}s")
                    elif curr_segment.start_time - prev_segment.end_time > 5.0:
                        warnings.append(f"Large gap detected at {prev_segment.end_time}s")
            
            # Check for empty text segments
            empty_segments = [s for s in segments if not s.text or not s.text.strip()]
            if empty_segments:
                warnings.append(f"Found {len(empty_segments)} empty text segments")
            
            # Check confidence scores
            low_confidence = [s for s in segments if s.confidence_score and s.confidence_score < 0.5]
            if low_confidence:
                warnings.append(f"Found {len(low_confidence)} segments with low confidence")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'segment_count': len(segments),
                'speaker_count': len(speakers),
                'total_duration': segments[-1].end_time if segments else 0
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }