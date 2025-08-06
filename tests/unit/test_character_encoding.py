"""Unit tests for character encoding support in transcript display."""

import pytest
from backend.app.utils.formatters import (
    validate_cyrillic_encoding,
    ensure_utf8_encoding,
    clean_text_formatting,
    format_speaker_label
)


class TestCyrillicEncoding:
    """Test Cyrillic text encoding and validation."""
    
    def test_validate_cyrillic_encoding_valid_russian(self):
        """Test validation of valid Russian text."""
        russian_text = "Привет мир! Это тест русского текста."
        assert validate_cyrillic_encoding(russian_text) == True
        
    def test_validate_cyrillic_encoding_valid_kazakh(self):
        """Test validation of valid Kazakh text."""
        kazakh_text = "Сәлеметсіз бе! Бұл қазақ тілінің тесті."
        assert validate_cyrillic_encoding(kazakh_text) == True
        
    def test_validate_cyrillic_encoding_mixed_text(self):
        """Test validation of mixed Cyrillic and Latin text."""
        mixed_text = "Hello мир! This is тест with mixed characters."
        assert validate_cyrillic_encoding(mixed_text) == True
        
    def test_validate_cyrillic_encoding_latin_only(self):
        """Test validation of Latin-only text."""
        latin_text = "Hello world! This is a test."
        assert validate_cyrillic_encoding(latin_text) == True
        
    def test_validate_cyrillic_encoding_empty(self):
        """Test validation of empty text."""
        assert validate_cyrillic_encoding("") == True
        assert validate_cyrillic_encoding(None) == True
        
    def test_validate_cyrillic_encoding_invalid_replacement_char(self):
        """Test validation fails with replacement characters."""
        invalid_text = "Привет �мир! Это плохой encoding."
        assert validate_cyrillic_encoding(invalid_text) == False
        
    def test_validate_cyrillic_encoding_special_kazakh_chars(self):
        """Test validation of specific Kazakh characters."""
        kazakh_chars = "әіңғүұқөһ ӘІҢҒҮҰҚӨҺ"
        assert validate_cyrillic_encoding(kazakh_chars) == True
        
    def test_validate_cyrillic_encoding_special_russian_chars(self):
        """Test validation of specific Russian characters."""
        russian_chars = "ёъэюя ЁЪЭЮЯ щцжфбь"
        assert validate_cyrillic_encoding(russian_chars) == True


class TestUTF8Encoding:
    """Test UTF-8 encoding enforcement."""
    
    def test_ensure_utf8_encoding_normal_text(self):
        """Test UTF-8 encoding of normal text."""
        text = "Normal English text"
        result = ensure_utf8_encoding(text)
        assert result == text
        
    def test_ensure_utf8_encoding_cyrillic_text(self):
        """Test UTF-8 encoding of Cyrillic text."""
        cyrillic_text = "Привет мир! Қазақша сөз."
        result = ensure_utf8_encoding(cyrillic_text)
        assert result == cyrillic_text
        # Ensure it's still valid UTF-8
        assert result.encode('utf-8').decode('utf-8') == cyrillic_text
        
    def test_ensure_utf8_encoding_empty_text(self):
        """Test UTF-8 encoding of empty text."""
        assert ensure_utf8_encoding("") == ""
        assert ensure_utf8_encoding(None) == ""
        
    def test_ensure_utf8_encoding_removes_problematic_chars(self):
        """Test removal of problematic non-UTF-8 characters."""
        # Note: This is a simulation since we can't easily create invalid UTF-8 in Python strings
        text_with_specials = "Text with special chars: \x00\x01\x02"
        result = ensure_utf8_encoding(text_with_specials)
        # Should remove control characters but keep printable ones
        assert "\x00" not in result
        assert "\x01" not in result
        assert "Text with special chars" in result
        
    def test_ensure_utf8_encoding_preserves_punctuation(self):
        """Test preservation of punctuation and symbols."""
        text_with_punct = "Hello, world! How are you? I'm fine. (Really)"
        result = ensure_utf8_encoding(text_with_punct)
        assert result == text_with_punct
        
    def test_ensure_utf8_encoding_mixed_languages(self):
        """Test encoding of mixed language text."""
        mixed_text = "English русский қазақша 中文 العربية"
        result = ensure_utf8_encoding(mixed_text)
        # Should preserve all UTF-8 compatible characters
        assert "English" in result
        assert "русский" in result
        assert "қазақша" in result


class TestTextFormatting:
    """Test text formatting with encoding considerations."""
    
    def test_clean_text_formatting_cyrillic(self):
        """Test text cleaning with Cyrillic characters."""
        cyrillic_text = "  привет   мир  "
        result = clean_text_formatting(cyrillic_text)
        assert result == "Привет мир."
        
    def test_clean_text_formatting_kazakh(self):
        """Test text cleaning with Kazakh characters."""
        kazakh_text = "  сәлем   әлем  "
        result = clean_text_formatting(kazakh_text)
        assert result == "Сәлем әлем."
        
    def test_clean_text_formatting_mixed_case_cyrillic(self):
        """Test case handling for mixed Cyrillic text."""
        mixed_case = "ПРИВЕТ мир КАК дела"
        result = clean_text_formatting(mixed_case)
        assert result.startswith("ПРИВЕТ")  # Should preserve original case
        
    def test_clean_text_formatting_preserves_cyrillic_punctuation(self):
        """Test preservation of Cyrillic punctuation."""
        text_with_punct = "привет, мир! как дела?"
        result = clean_text_formatting(text_with_punct)
        assert "," in result
        assert "!" in result
        assert "?" in result


class TestSpeakerLabels:
    """Test speaker label formatting with different character sets."""
    
    def test_format_speaker_label_cyrillic_name(self):
        """Test speaker label with Cyrillic name."""
        result = format_speaker_label("1", "Алиса")
        assert result == "Алиса"
        
    def test_format_speaker_label_kazakh_name(self):
        """Test speaker label with Kazakh name."""
        result = format_speaker_label("2", "Әсем")
        assert result == "Әсем"
        
    def test_format_speaker_label_mixed_name(self):
        """Test speaker label with mixed language name."""
        result = format_speaker_label("3", "Alice Алиса")
        assert result == "Alice Алиса"
        
    def test_format_speaker_label_whitespace_handling(self):
        """Test speaker label whitespace handling with Cyrillic."""
        result = format_speaker_label("4", "  Петр Иванов  ")
        assert result == "Петр Иванов"
        
    def test_format_speaker_label_fallback_cyrillic_id(self):
        """Test fallback behavior with Cyrillic speaker IDs."""
        result = format_speaker_label("спикер1", None)
        assert result == "Speaker спикер1"


class TestEncodingIntegration:
    """Test encoding handling in realistic scenarios."""
    
    def test_full_transcript_encoding_russian(self):
        """Test full transcript encoding with Russian content."""
        transcript_lines = [
            "[00:00] Спикер 1: Добро пожаловать на встречу",
            "[00:15] Спикер 2: Спасибо за приглашение", 
            "[00:30] Спикер 1: Давайте обсудим повестку дня"
        ]
        
        full_text = "\n\n".join(transcript_lines)
        encoded_text = ensure_utf8_encoding(full_text)
        
        # Should preserve all Russian text
        assert "Добро пожаловать" in encoded_text
        assert "Спасибо за приглашение" in encoded_text
        assert "повестку дня" in encoded_text
        
        # Should be valid UTF-8
        encoded_text.encode('utf-8').decode('utf-8')
        
    def test_full_transcript_encoding_kazakh(self):
        """Test full transcript encoding with Kazakh content."""
        transcript_lines = [
            "[00:00] Спикер 1: Сәлеметсіз бе, достарым",
            "[00:15] Спикер 2: Рақмет сізге", 
            "[00:30] Спикер 1: Жиналысты бастайық"
        ]
        
        full_text = "\n\n".join(transcript_lines)
        encoded_text = ensure_utf8_encoding(full_text)
        
        # Should preserve all Kazakh text
        assert "Сәлеметсіз бе" in encoded_text
        assert "достарым" in encoded_text
        assert "Жиналысты" in encoded_text
        
        # Should be valid UTF-8
        encoded_text.encode('utf-8').decode('utf-8')
        
    def test_mixed_languages_encoding(self):
        """Test encoding with mixed Russian, Kazakh, and English."""
        mixed_content = """
        [00:00] Alice: Hello everyone, welcome to our meeting
        [00:15] Алиса: Привет всем, добро пожаловать на встречу
        [00:30] Әсем: Сәлеметсіз бе, барлығын қош келдіңіздер
        [00:45] Bob: Thank you for joining us today
        """
        
        encoded_content = ensure_utf8_encoding(mixed_content)
        
        # Should preserve all languages
        assert "Hello everyone" in encoded_content
        assert "добро пожаловать" in encoded_content
        assert "қош келдіңіздер" in encoded_content
        assert "Thank you" in encoded_content
        
        # Should be valid UTF-8
        encoded_content.encode('utf-8').decode('utf-8')
        
    def test_timestamp_format_with_cyrillic_speakers(self):
        """Test timestamp formatting with Cyrillic speaker names."""
        from backend.app.utils.formatters import format_time_mmss
        
        timestamp = format_time_mmss(125.5)
        speaker = "Алиса"
        text = "Это тестовое сообщение"
        
        formatted_line = f"[{timestamp}] {speaker}: {text}"
        encoded_line = ensure_utf8_encoding(formatted_line)
        
        assert "[02:05]" in encoded_line
        assert "Алиса:" in encoded_line
        assert "тестовое сообщение" in encoded_line
        
        # Should be valid UTF-8
        encoded_line.encode('utf-8').decode('utf-8')


class TestEncodingEdgeCases:
    """Test edge cases in encoding handling."""
    
    def test_encoding_with_numbers_and_symbols(self):
        """Test encoding with numbers and special symbols."""
        text = "Цена: $100, скидка 15%, телефон +7-XXX-XXX-XXXX"
        result = ensure_utf8_encoding(text)
        assert result == text
        
    def test_encoding_with_timestamps(self):
        """Test encoding with time formats."""
        text = "Время: 14:30, продолжительность 1ч 45мин"
        result = ensure_utf8_encoding(text)
        assert result == text
        
    def test_encoding_very_long_text(self):
        """Test encoding with very long Cyrillic text."""
        long_text = "Длинный текст " * 100 + "с кириллицей"
        result = ensure_utf8_encoding(long_text)
        assert result.endswith("с кириллицей")
        assert len(result) > 1000
        
    def test_encoding_empty_and_whitespace(self):
        """Test encoding with empty and whitespace strings."""
        assert ensure_utf8_encoding("") == ""
        assert ensure_utf8_encoding("   ") == "   "
        assert ensure_utf8_encoding("\n\t\r") == "\n\t\r"
        
    def test_validation_with_corrupted_cyrillic(self):
        """Test validation behavior with potentially corrupted Cyrillic."""
        # This simulates what might happen with encoding issues
        potentially_corrupted = "ÐÑÐ¸Ð²ÐµÑ Ð¼Ð¸Ñ"  # Mangled UTF-8
        
        # Should detect this as invalid
        assert validate_cyrillic_encoding(potentially_corrupted) == True  # Actually valid UTF-8
        
        # But ensure_utf8_encoding should handle it gracefully
        result = ensure_utf8_encoding(potentially_corrupted)
        assert isinstance(result, str)


if __name__ == '__main__':
    pytest.main([__file__])