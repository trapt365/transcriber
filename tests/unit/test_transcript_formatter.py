"""Unit tests for transcript formatting service."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from backend.app.services.transcript_formatter import TranscriptFormatter
from backend.app.utils.formatters import (
    format_time_mmss, 
    format_time_hhmmss,
    format_time_precise,
    clean_text_formatting,
    preserve_paragraph_breaks,
    truncate_text_preview,
    validate_cyrillic_encoding,
    format_speaker_label,
    ensure_utf8_encoding
)


class TestTimeFormatting:
    """Test time formatting functions."""
    
    def test_format_time_mmss(self):
        """Test MM:SS time formatting."""
        assert format_time_mmss(0) == "00:00"
        assert format_time_mmss(45) == "00:45"
        assert format_time_mmss(90) == "01:30"
        assert format_time_mmss(125.7) == "02:05"
        assert format_time_mmss(3599) == "59:59"
        
    def test_format_time_mmss_negative(self):
        """Test MM:SS formatting with negative values."""
        assert format_time_mmss(-10) == "00:00"
        
    def test_format_time_hhmmss(self):
        """Test HH:MM:SS time formatting."""
        assert format_time_hhmmss(0) == "00:00:00"
        assert format_time_hhmmss(45) == "00:00:45"
        assert format_time_hhmmss(90) == "00:01:30"
        assert format_time_hhmmss(3661) == "01:01:01"
        assert format_time_hhmmss(7325.8) == "02:02:05"
        
    def test_format_time_hhmmss_negative(self):
        """Test HH:MM:SS formatting with negative values."""
        assert format_time_hhmmss(-10) == "00:00:00"
        
    def test_format_time_precise(self):
        """Test precise time formatting with milliseconds."""
        assert format_time_precise(0) == "00:00.000"
        assert format_time_precise(45.123) == "00:45.123"
        assert format_time_precise(3661.456) == "01:01:01.456"


class TestTextFormatting:
    """Test text formatting functions."""
    
    def test_clean_text_formatting(self):
        """Test text cleaning and formatting."""
        assert clean_text_formatting("hello world") == "Hello world."
        assert clean_text_formatting("  multiple   spaces  ") == "Multiple spaces."
        assert clean_text_formatting("already ending.") == "Already ending."
        assert clean_text_formatting("question?") == "Question?"
        assert clean_text_formatting("") == ""
        assert clean_text_formatting("   ") == ""
        
    def test_preserve_paragraph_breaks(self):
        """Test paragraph break preservation."""
        segments = [
            "This is first sentence.",
            "This is second sentence in same paragraph.",
            "This is a new paragraph after long text that should create break."
        ]
        result = preserve_paragraph_breaks(segments)
        assert "\n\n" in result
        
    def test_truncate_text_preview(self):
        """Test text truncation for previews."""
        short_text = "Short text"
        assert truncate_text_preview(short_text) == short_text
        
        long_text = "This is a very long text " * 30
        result = truncate_text_preview(long_text, 50)
        assert len(result) <= 51  # 50 + ellipsis
        assert result.endswith("…")
        
    def test_validate_cyrillic_encoding(self):
        """Test Cyrillic text encoding validation."""
        # Valid UTF-8
        assert validate_cyrillic_encoding("Hello world") == True
        assert validate_cyrillic_encoding("Привет мир") == True
        assert validate_cyrillic_encoding("Қазақша мәтін") == True
        
        # Invalid encoding indicators
        assert validate_cyrillic_encoding("Invalid�character") == False
        assert validate_cyrillic_encoding("") == True
        
    def test_format_speaker_label(self):
        """Test speaker label formatting."""
        assert format_speaker_label("speaker1") == "Speaker 1"
        assert format_speaker_label("speaker2", "John Doe") == "John Doe"
        assert format_speaker_label("spk_1") == "Speaker spk_1"
        assert format_speaker_label("1", "  Alice  ") == "Alice"
        
    def test_ensure_utf8_encoding(self):
        """Test UTF-8 encoding enforcement."""
        assert ensure_utf8_encoding("Normal text") == "Normal text"
        assert ensure_utf8_encoding("Cyrillic: Привет") == "Cyrillic: Привет"
        assert ensure_utf8_encoding("") == ""


class TestTranscriptFormatter:
    """Test TranscriptFormatter service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.db_session = Mock()
        self.formatter = TranscriptFormatter(self.db_session)
        
    def create_mock_job(self):
        """Create mock job for testing."""
        job = Mock()
        job.id = 1
        job.job_id = "test-job-123"
        job.language = "ru-RU"
        job.processing_time = 45.5
        return job
        
    def create_mock_speakers(self):
        """Create mock speakers for testing."""
        speaker1 = Mock()
        speaker1.id = 1
        speaker1.speaker_id = "1"
        speaker1.speaker_label = "Alice"
        
        speaker2 = Mock()
        speaker2.id = 2
        speaker2.speaker_id = "2"
        speaker2.speaker_label = None
        
        return [speaker1, speaker2]
        
    def create_mock_segments(self):
        """Create mock transcript segments for testing."""
        segments = []
        
        # Segment 1 - Speaker 1
        seg1 = Mock()
        seg1.id = 1
        seg1.speaker_id = 1
        seg1.start_time = 0.0
        seg1.end_time = 3.5
        seg1.text = "Hello everyone"
        seg1.created_at = datetime.now()
        segments.append(seg1)
        
        # Segment 2 - Speaker 1 continues
        seg2 = Mock()
        seg2.id = 2
        seg2.speaker_id = 1
        seg2.start_time = 3.5
        seg2.end_time = 7.0
        seg2.text = "welcome to the meeting"
        seg2.created_at = datetime.now()
        segments.append(seg2)
        
        # Segment 3 - Speaker 2
        seg3 = Mock()
        seg3.id = 3
        seg3.speaker_id = 2
        seg3.start_time = 8.0
        seg3.end_time = 12.5
        seg3.text = "Thank you for having me"
        seg3.created_at = datetime.now()
        segments.append(seg3)
        
        return segments
        
    def create_mock_job_result(self):
        """Create mock job result for testing."""
        result = Mock()
        result.confidence_score = 0.85
        result.formatted_transcript = None
        return result
        
    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """Set up all mocks for testing."""
        self.mock_job = self.create_mock_job()
        self.mock_speakers = self.create_mock_speakers()
        self.mock_segments = self.create_mock_segments()
        self.mock_result = self.create_mock_job_result()
        
        # Mock model class methods
        monkeypatch.setattr('backend.app.models.Job.find_by_job_id', 
                          lambda job_id: self.mock_job if job_id == "test-job-123" else None)
        monkeypatch.setattr('backend.app.models.TranscriptSegment.find_by_job', 
                          lambda job_id: self.mock_segments if job_id == 1 else [])
        monkeypatch.setattr('backend.app.models.Speaker.find_by_job', 
                          lambda job_id: self.mock_speakers if job_id == 1 else [])
        monkeypatch.setattr('backend.app.models.JobResult.find_by_job', 
                          lambda job_id: self.mock_result if job_id == 1 else None)
        
    def test_format_transcript_success(self):
        """Test successful transcript formatting."""
        result = self.formatter.format_transcript("test-job-123")
        
        assert result['job_id'] == "test-job-123"
        assert len(result['segments']) >= 1
        assert 'formatted_text' in result
        assert result['preview']
        assert result['speaker_count'] == 2
        assert result['total_segments'] == 3
        
    def test_format_transcript_job_not_found(self):
        """Test formatting when job is not found."""
        with pytest.raises(ValueError, match="Job not found"):
            self.formatter.format_transcript("nonexistent-job")
            
    def test_get_speaker_label(self):
        """Test speaker label generation."""
        speaker_with_label = self.mock_speakers[0]
        speaker_without_label = self.mock_speakers[1]
        
        assert self.formatter._get_speaker_label(speaker_with_label) == "Alice"
        assert self.formatter._get_speaker_label(speaker_without_label) == "Speaker 2"
        assert self.formatter._get_speaker_label(None) == "Unknown Speaker"
        
    def test_generate_formatted_text(self):
        """Test formatted text generation."""
        segments = [
            {
                'speaker': 'Alice',
                'text': 'Hello everyone',
                'start_time': 0.0,
                'end_time': 3.5
            },
            {
                'speaker': 'Bob',
                'text': 'Thank you',
                'start_time': 8.0,
                'end_time': 12.5
            }
        ]
        
        result = self.formatter._generate_formatted_text(segments)
        
        assert "[00:00] Alice: Hello everyone" in result
        assert "[00:08] Bob: Thank you" in result
        assert "\n\n" in result  # Double newline separator
        
    def test_validate_transcript_data_success(self):
        """Test transcript data validation with valid data."""
        result = self.formatter.validate_transcript_data("test-job-123")
        
        assert result['valid'] == True
        assert result['segment_count'] == 3
        assert result['speaker_count'] == 2
        assert len(result['errors']) == 0
        
    def test_validate_transcript_data_job_not_found(self):
        """Test validation when job is not found."""
        result = self.formatter.validate_transcript_data("nonexistent-job")
        
        assert result['valid'] == False
        assert "Job not found" in result['errors']
        
    def test_save_formatted_transcript_success(self):
        """Test saving formatted transcript."""
        result = self.formatter.save_formatted_transcript("test-job-123")
        
        assert result == True
        self.db_session.commit.assert_called_once()
        
    def test_save_formatted_transcript_job_not_found(self):
        """Test saving when job is not found."""
        result = self.formatter.save_formatted_transcript("nonexistent-job")
        
        assert result == False
        
    def test_format_transcript_with_long_duration(self):
        """Test formatting with duration > 1 hour (should use HH:MM:SS format)."""
        # Mock segment with long duration
        long_segment = Mock()
        long_segment.id = 1
        long_segment.speaker_id = 1
        long_segment.start_time = 3665.0  # Over 1 hour
        long_segment.end_time = 3670.0
        long_segment.text = "This is a long meeting"
        long_segment.created_at = datetime.now()
        
        # Replace mock segments with long duration segment
        import backend.app.models
        original_find_by_job = backend.app.models.TranscriptSegment.find_by_job
        backend.app.models.TranscriptSegment.find_by_job = lambda job_id: [long_segment] if job_id == 1 else []
        
        try:
            result = self.formatter.format_transcript("test-job-123")
            assert "01:01:05" in result['formatted_text']  # Should use HH:MM:SS format
        finally:
            backend.app.models.TranscriptSegment.find_by_job = original_find_by_job


if __name__ == '__main__':
    pytest.main([__file__])