"""Tests for the text normalizer."""

import pytest
from app.detection.normalizer import normalize, NormalizedOutput


class TestNormalize:
    def test_normal_text(self):
        result = normalize("Hola, como estas?")
        assert result.original == "Hola, como estas?"
        assert result.normalized == "Hola, como estas?"
        assert result.has_invisible_chars is False
        assert result.homoglyphs_found == []
        assert result.encoding_detected is None

    def test_empty_text(self):
        result = normalize("")
        assert result.normalized == ""

    def test_whitespace_only(self):
        result = normalize("   ")
        assert result.normalized == "   "

    def test_unicode_normalization(self):
        """NFKC normalization should decompose compatible characters."""
        text = "Café"  # é is U+00E9, should normalize to itself (already NFC)
        result = normalize(text)
        assert "é" in result.normalized

    def test_invisible_chars_detection(self):
        """Zero-width space should be detected."""
        text = "Hello\u200bWorld"
        result = normalize(text)
        assert result.has_invisible_chars is True
        # The invisible char should be removed in normalized version
        assert "\u200b" not in result.normalized

    def test_zero_width_non_joiner(self):
        text = "Test\u200cIng"
        result = normalize(text)
        assert result.has_invisible_chars is True
        assert "\u200c" not in result.normalized

    def test_bidirectional_marks(self):
        text = "Hello\u200eWorld"
        result = normalize(text)
        assert result.has_invisible_chars is True
        assert "\u200e" not in result.normalized

    def test_bom_detection(self):
        text = "\ufeffHello"
        result = normalize(text)
        assert result.has_invisible_chars is True
        assert "\ufeff" not in result.normalized

    def test_homoglyph_detection(self):
        """Cyrillic 'а' (U+0430) looks like Latin 'a'."""
        text = "hellо"  # last 'o' is Cyrillic small o (U+043E)
        result = normalize(text)
        assert len(result.homoglyphs_found) > 0

    def test_homoglyph_positions(self):
        text = "аtest"  # Cyrillic 'а' at position 0
        result = normalize(text)
        assert len(result.homoglyphs_found) >= 1
        assert result.homoglyphs_found[0]["position"] == 0

    def test_base64_detection(self):
        """Long base64-like string should be detected."""
        text = "SGVsbG8gV29ybGQgVGhpcyBpcyBhIHRlc3QgbWVzc2FnZSBmb3IgZGV0ZWN0aW9u"
        result = normalize(text)
        assert result.encoding_detected == "base64"

    def test_hex_detection(self):
        """Long hex string should be detected."""
        text = "48656c6c6f20576f726c64205468697320697320612074657374"
        result = normalize(text)
        assert result.encoding_detected == "hex"

    def test_short_base64_not_detected(self):
        """Short strings should not trigger encoding detection."""
        text = "SGVsbG8="
        result = normalize(text)
        assert result.encoding_detected is None

    def test_no_false_encoding_on_normal_text(self):
        result = normalize("This is just a normal sentence.")
        assert result.encoding_detected is None

    def test_multiple_features(self):
        """Test text with invisible chars AND homoglyphs."""
        text = "а\u200btest"  # Cyrillic 'а' + zero-width space
        result = normalize(text)
        assert result.has_invisible_chars is True
        assert len(result.homoglyphs_found) > 0
