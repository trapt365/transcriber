"""Text formatting utilities for transcripts."""

import re
from typing import List, Optional


def format_time_mmss(seconds: float) -> str:
    """
    Format time in MM:SS format.
    
    Args:
        seconds: Time in seconds (float for precision)
        
    Returns:
        Formatted time string (e.g., "03:45")
    """
    if seconds < 0:
        seconds = 0
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    
    return f"{minutes:02d}:{secs:02d}"


def format_time_hhmmss(seconds: float) -> str:
    """
    Format time in HH:MM:SS format.
    
    Args:
        seconds: Time in seconds (float for precision)
        
    Returns:
        Formatted time string (e.g., "01:03:45")
    """
    if seconds < 0:
        seconds = 0
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_time_precise(seconds: float) -> str:
    """
    Format time with millisecond precision.
    
    Args:
        seconds: Time in seconds (float for precision)
        
    Returns:
        Formatted time string (e.g., "01:03:45.123")
    """
    if seconds < 0:
        seconds = 0
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    else:
        return f"{minutes:02d}:{secs:06.3f}"


def clean_text_formatting(text: str) -> str:
    """
    Clean and format transcript text for readability.
    
    Args:
        text: Raw transcript text
        
    Returns:
        Cleaned and formatted text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Ensure proper sentence ending punctuation
    if text and not text.endswith(('.', '!', '?', '…')):
        # Add period if text doesn't end with punctuation
        text = text.rstrip() + '.'
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    return text


def preserve_paragraph_breaks(segments: List[str]) -> str:
    """
    Preserve natural paragraph breaks in transcript segments.
    
    Args:
        segments: List of text segments
        
    Returns:
        Text with preserved paragraph structure
    """
    if not segments:
        return ""
    
    # Join segments with double newlines to create paragraphs
    paragraphs = []
    current_paragraph = []
    
    for segment in segments:
        cleaned_segment = clean_text_formatting(segment)
        if cleaned_segment:
            current_paragraph.append(cleaned_segment)
            
            # End paragraph on certain punctuation patterns
            if (cleaned_segment.endswith(('.', '!', '?')) and 
                len(' '.join(current_paragraph)) > 100):  # Minimum paragraph length
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
    
    # Add remaining text as final paragraph
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    return '\n\n'.join(paragraphs)


def truncate_text_preview(text: str, max_length: int = 500) -> str:
    """
    Create a truncated preview of text.
    
    Args:
        text: Full text to preview
        max_length: Maximum length of preview
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Try to break at word boundary
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we found a space in the last 20%
        truncated = truncated[:last_space]
    
    return truncated + "…"


def validate_cyrillic_encoding(text: str) -> bool:
    """
    Validate that Cyrillic text is properly encoded.
    
    Args:
        text: Text to validate
        
    Returns:
        True if encoding is valid, False otherwise
    """
    if not text:
        return True
    
    try:
        # Try encoding/decoding as UTF-8
        text.encode('utf-8').decode('utf-8')
        
        # Check for common encoding issues
        if '�' in text:  # Replacement character indicates encoding issues
            return False
        
        # Check for proper Cyrillic character ranges
        cyrillic_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        if cyrillic_chars > 0:
            # If there are Cyrillic chars, ensure they're displayable
            for char in text:
                if '\u0400' <= char <= '\u04FF':
                    try:
                        char.encode('utf-8')
                    except UnicodeEncodeError:
                        return False
        
        return True
        
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


def format_speaker_label(speaker_id: str, speaker_name: Optional[str] = None) -> str:
    """
    Format speaker label for display.
    
    Args:
        speaker_id: Raw speaker ID from API
        speaker_name: Optional human-readable name
        
    Returns:
        Formatted speaker label
    """
    if speaker_name and speaker_name.strip():
        return speaker_name.strip()
    
    # Clean up speaker ID for display
    if speaker_id.startswith('speaker'):
        # Extract number from speaker ID
        numbers = re.findall(r'\d+', speaker_id)
        if numbers:
            return f"Speaker {numbers[0]}"
    
    return f"Speaker {speaker_id}"


def ensure_utf8_encoding(text: str) -> str:
    """
    Ensure text is properly UTF-8 encoded for web display.
    
    Args:
        text: Input text
        
    Returns:
        UTF-8 encoded text safe for web display
    """
    if not text:
        return ""
    
    try:
        # Normalize to UTF-8
        normalized = text.encode('utf-8', errors='replace').decode('utf-8')
        
        # Remove any remaining problematic characters
        cleaned = re.sub(r'[^\w\s\u0400-\u04FF.,!?;:()[\]{}"\'-]', '', normalized)
        
        return cleaned
        
    except Exception:
        # Fallback: replace problematic characters
        return re.sub(r'[^\w\s.,!?;:()[\]{}"\'-]', '?', str(text))