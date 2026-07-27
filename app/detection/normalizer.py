import re
import unicodedata
import logging
from dataclasses import dataclass, field
from typing import Optional
import unidecode

logger = logging.getLogger(__name__)

# Zero-width and invisible Unicode characters
INVISIBLE_CHARS = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2060\u2061\u2062\u2063\u2064\u2066\u2067\u2068\u2069\u206a\u206b\u206c\u206d\u206e\u206f\ufeff]"
)

# Cyrillic homoglyphs map (chars that look like Latin letters)
CYRILLIC_HOMOGLYPHS = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
    'х': 'x', 'і': 'i', 'ј': 'j', 'к': 'k', 'м': 'm', 'н': 'h',
    'в': 'b', 'т': 't', 'ѕ': 's', 'і': 'i', 'ѡ': 'w',
}

LATIN_HOMOGLYPHS = {v: k for k, v in CYRILLIC_HOMOGLYPHS.items()}

@dataclass
class NormalizedOutput:
    original: str
    normalized: str
    has_invisible_chars: bool = False
    homoglyphs_found: list[dict] = field(default_factory=list)
    encoding_detected: Optional[str] = None


def normalize(text: str) -> NormalizedOutput:
    if not text or not text.strip():
        return NormalizedOutput(original=text or "", normalized=text or "")

    result = NormalizedOutput(original=text, normalized=text)

    # 1. Detect invisible chars
    result.has_invisible_chars = bool(INVISIBLE_CHARS.search(text))

    # 2. Remove invisible chars for normalized version
    cleaned = INVISIBLE_CHARS.sub("", text)

    # 3. Detect homoglyphs
    result.homoglyphs_found = _detect_homoglyphs(cleaned)

    # 4. Unicode NFKC normalization
    result.normalized = unicodedata.normalize("NFKC", cleaned)

    # 5. Detect encodings
    result.encoding_detected = _detect_encodings(cleaned)

    return result


def _detect_homoglyphs(text: str) -> list[dict]:
    found = []
    for i, char in enumerate(text):
        if char in CYRILLIC_HOMOGLYPHS:
            found.append({
                "char": char,
                "replacement": CYRILLIC_HOMOGLYPHS[char],
                "position": i,
            })
    return found


def _detect_encodings(text: str) -> Optional[str]:
    # Check for base64-like strings (long sequences of alphanumeric + /+ =)
    base64_pattern = re.compile(r'^[A-Za-z0-9+/=]{30,}$')
    hex_pattern = re.compile(r'^[0-9a-fA-F]{30,}$')
    rot13_pattern = re.compile(r'^[A-Za-z]{30,}$')  # clues: combined with context words

    stripped = text.strip()
    lines = stripped.split('\n')
    for line in lines:
        line = line.strip()
        # Check hex first (more restrictive charset)
        if hex_pattern.match(line):
            return "hex"
        if base64_pattern.match(line):
            return "base64"

    return None
