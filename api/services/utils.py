"""Utility functions for Editorial Assistant v3.0 API.

Provides timezone-aware datetime handling, SRT parsing, and common utilities.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    This function should be used instead of the deprecated datetime.utcnow(),
    which returns naive datetime objects.

    Returns:
        Timezone-aware datetime representing the current UTC time

    Examples:
        >>> now = utc_now()
        >>> now.tzinfo is not None
        True
        >>> now.tzinfo == timezone.utc
        True
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 formatted string.

    Returns:
        ISO 8601 string representation of current UTC time with timezone info

    Examples:
        >>> timestamp = utc_now_iso()
        >>> timestamp.endswith('+00:00') or timestamp.endswith('Z')
        True
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert naive datetime to UTC-aware datetime.

    If the datetime is already timezone-aware, returns it unchanged.
    If the datetime is naive (no timezone), assumes it represents UTC
    and adds UTC timezone information.

    Args:
        dt: Datetime to convert (can be None)

    Returns:
        Timezone-aware datetime or None if input is None

    Examples:
        >>> from datetime import datetime
        >>> naive_dt = datetime(2024, 1, 15, 12, 30, 0)
        >>> aware_dt = ensure_utc(naive_dt)
        >>> aware_dt.tzinfo == timezone.utc
        True

        >>> already_aware = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        >>> ensure_utc(already_aware) == already_aware
        True

        >>> ensure_utc(None) is None
        True
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Naive datetime - assume UTC and add timezone info
        return dt.replace(tzinfo=timezone.utc)

    # Already timezone-aware - return unchanged
    return dt


def parse_iso_datetime(s: str) -> datetime:
    """Parse ISO 8601 datetime string to UTC-aware datetime.

    Handles various ISO 8601 formats and ensures the result is always
    in UTC with timezone information.

    Args:
        s: ISO 8601 formatted datetime string

    Returns:
        Timezone-aware datetime in UTC

    Raises:
        ValueError: If string cannot be parsed as ISO datetime

    Examples:
        >>> dt = parse_iso_datetime("2024-01-15T12:30:00+00:00")
        >>> dt.tzinfo == timezone.utc
        True

        >>> dt = parse_iso_datetime("2024-01-15T12:30:00Z")
        >>> dt.tzinfo == timezone.utc
        True

        >>> dt = parse_iso_datetime("2024-01-15T12:30:00")
        >>> dt.tzinfo == timezone.utc
        True
    """
    try:
        # Try parsing with fromisoformat (handles most ISO formats)
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValueError(f"Invalid ISO datetime string: {s}") from e

    # Ensure result is UTC-aware
    return ensure_utc(dt)


def calculate_transcript_metrics(
    transcript_content: str,
    words_per_minute: int = 150,
    long_form_threshold_minutes: int = 15
) -> dict:
    """Calculate metrics from transcript content for routing decisions.

    Args:
        transcript_content: Raw transcript text
        words_per_minute: Speaking rate estimate (default 150 wpm)
        long_form_threshold_minutes: Minutes threshold for long-form classification

    Returns:
        Dict with word_count, estimated_duration_minutes, is_long_form

    Examples:
        >>> metrics = calculate_transcript_metrics("Hello world " * 1000)
        >>> metrics["word_count"]
        2000
        >>> metrics["estimated_duration_minutes"]  # 2000 / 150 = 13.33
        13.33
        >>> metrics["is_long_form"]
        False

        >>> metrics = calculate_transcript_metrics("Hello world " * 2500)
        >>> metrics["is_long_form"]  # 5000 words / 150 wpm = 33.33 min
        True
    """
    # Count words (simple split on whitespace)
    words = transcript_content.split()
    word_count = len(words)

    # Estimate duration based on speaking rate
    estimated_duration_minutes = round(word_count / words_per_minute, 2)

    # Classify as long-form if exceeds threshold
    is_long_form = estimated_duration_minutes > long_form_threshold_minutes

    return {
        "word_count": word_count,
        "estimated_duration_minutes": estimated_duration_minutes,
        "is_long_form": is_long_form,
    }


def extract_media_id(filename: str) -> str:
    """Extract Media ID from transcript filename.

    Removes processing suffixes but PRESERVES revision identifiers.
    Handles PBS Wisconsin naming conventions:
    - _ForClaude suffix: Stripped (processing artifact)
    - _REV[date] suffix: PRESERVED (distinct Media ID for revised content)

    Revised video files are denoted as original Media ID plus _REV followed by
    the revision date (e.g., _REV20260102). This creates a new, distinct Media ID.

    Args:
        filename: Transcript filename (with or without extension)

    Returns:
        Extracted media ID (base filename without processing suffixes)

    Examples:
        >>> extract_media_id("2WLI1209HD_ForClaude.txt")
        '2WLI1209HD'
        >>> extract_media_id("9UNP2005HD.srt")
        '9UNP2005HD'
        >>> extract_media_id("2BUC0000HDWEB02_REV20251202.srt")
        '2BUC0000HDWEB02_REV20251202'
        >>> extract_media_id("Some_Project_Name.txt")
        'Some_Project_Name'
        >>> extract_media_id("2WLI1209HD_ForClaude_REV20251202.txt")
        '2WLI1209HD_REV20251202'
    """
    # Get filename without path
    base_name = Path(filename).name

    # Remove extension
    stem = Path(base_name).stem

    # Remove only _ForClaude suffix (processing artifact)
    # PRESERVE _REV[date] suffix as it denotes a distinct revised Media ID
    stem = re.sub(r'_ForClaude', '', stem, flags=re.IGNORECASE)

    return stem


# =============================================================================
# SRT Parsing Utilities
# =============================================================================

@dataclass
class SRTCaption:
    """Represents a single SRT caption entry."""
    index: int
    start_ms: int  # Start time in milliseconds
    end_ms: int    # End time in milliseconds
    text: str      # Caption text (may be multiline)

    @property
    def start_timecode(self) -> str:
        """Return start time as SRT timecode (HH:MM:SS,mmm)."""
        return ms_to_srt_timecode(self.start_ms)

    @property
    def end_timecode(self) -> str:
        """Return end time as SRT timecode (HH:MM:SS,mmm)."""
        return ms_to_srt_timecode(self.end_ms)

    @property
    def duration_ms(self) -> int:
        """Return duration in milliseconds."""
        return self.end_ms - self.start_ms

    def to_srt(self) -> str:
        """Convert to SRT format string."""
        return f"{self.index}\n{self.start_timecode} --> {self.end_timecode}\n{self.text}\n"

    def to_vtt(self) -> str:
        """Convert to WebVTT format string (no index, period for ms)."""
        start_vtt = ms_to_vtt_timecode(self.start_ms)
        end_vtt = ms_to_vtt_timecode(self.end_ms)
        return f"{start_vtt} --> {end_vtt}\n{self.text}\n"


def srt_timecode_to_ms(timecode: str) -> int:
    """Convert SRT timecode string to milliseconds.

    Args:
        timecode: SRT format timecode "HH:MM:SS,mmm"

    Returns:
        Total milliseconds

    Examples:
        >>> srt_timecode_to_ms("00:00:01,500")
        1500
        >>> srt_timecode_to_ms("01:30:45,123")
        5445123
        >>> srt_timecode_to_ms("00:02:30,000")
        150000
    """
    # Handle both , and . as millisecond separator
    timecode = timecode.replace('.', ',')
    match = re.match(r'(\d{1,2}):(\d{2}):(\d{2}),(\d{3})', timecode.strip())
    if not match:
        raise ValueError(f"Invalid SRT timecode: {timecode}")

    hours, minutes, seconds, ms = map(int, match.groups())
    total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + ms
    return total_ms


def ms_to_srt_timecode(ms: int) -> str:
    """Convert milliseconds to SRT timecode string.

    Args:
        ms: Total milliseconds

    Returns:
        SRT format timecode "HH:MM:SS,mmm"

    Examples:
        >>> ms_to_srt_timecode(1500)
        '00:00:01,500'
        >>> ms_to_srt_timecode(5445123)
        '01:30:45,123'
        >>> ms_to_srt_timecode(150000)
        '00:02:30,000'
    """
    if ms < 0:
        ms = 0

    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def ms_to_vtt_timecode(ms: int) -> str:
    """Convert milliseconds to WebVTT timecode string.

    Args:
        ms: Total milliseconds

    Returns:
        WebVTT format timecode "HH:MM:SS.mmm"

    Examples:
        >>> ms_to_vtt_timecode(1500)
        '00:00:01.500'
        >>> ms_to_vtt_timecode(5445123)
        '01:30:45.123'
    """
    srt_tc = ms_to_srt_timecode(ms)
    return srt_tc.replace(',', '.')


def ms_to_display_timecode(ms: int, include_hours: bool = False) -> str:
    """Convert milliseconds to display-friendly timecode.

    Args:
        ms: Total milliseconds
        include_hours: Always include hours, even if 0

    Returns:
        Display format "MM:SS" or "H:MM:SS"

    Examples:
        >>> ms_to_display_timecode(150000)
        '02:30'
        >>> ms_to_display_timecode(150000, include_hours=True)
        '0:02:30'
        >>> ms_to_display_timecode(5445000)
        '1:30:45'
    """
    if ms < 0:
        ms = 0

    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0 or include_hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def parse_srt(content: str) -> List[SRTCaption]:
    """Parse SRT file content into list of caption objects.

    Args:
        content: Full SRT file content as string

    Returns:
        List of SRTCaption objects in order

    Raises:
        ValueError: If content cannot be parsed

    Examples:
        >>> srt = '''1
        ... 00:00:01,000 --> 00:00:03,000
        ... Hello world
        ...
        ... 2
        ... 00:00:04,000 --> 00:00:06,000
        ... Second caption
        ... '''
        >>> captions = parse_srt(srt)
        >>> len(captions)
        2
        >>> captions[0].text
        'Hello world'
    """
    captions = []

    # Split into blocks (separated by blank lines)
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')
        if len(lines) < 3:
            continue

        try:
            # Line 1: Index number
            index = int(lines[0].strip())

            # Line 2: Timecodes
            time_match = re.match(
                r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})',
                lines[1].strip()
            )
            if not time_match:
                continue

            start_ms = srt_timecode_to_ms(time_match.group(1))
            end_ms = srt_timecode_to_ms(time_match.group(2))

            # Lines 3+: Caption text
            text = '\n'.join(lines[2:]).strip()

            captions.append(SRTCaption(
                index=index,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text
            ))
        except (ValueError, IndexError):
            # Skip malformed entries
            continue

    return captions


def generate_srt(captions: List[SRTCaption]) -> str:
    """Generate SRT file content from list of captions.

    Args:
        captions: List of SRTCaption objects

    Returns:
        Complete SRT file content as string
    """
    # Renumber captions sequentially
    output_parts = []
    for i, caption in enumerate(captions, 1):
        caption.index = i
        output_parts.append(caption.to_srt())

    return '\n'.join(output_parts)


def generate_vtt(captions: List[SRTCaption]) -> str:
    """Generate WebVTT file content from list of captions.

    Args:
        captions: List of SRTCaption objects

    Returns:
        Complete WebVTT file content as string
    """
    output_parts = ["WEBVTT", ""]

    for caption in captions:
        output_parts.append(caption.to_vtt())

    return '\n'.join(output_parts)


def clean_srt_captions(
    captions: List[SRTCaption],
    min_gap_ms: int = 50,
    max_duration_ms: int = 7000,
    merge_threshold_ms: int = 1000
) -> List[SRTCaption]:
    """Clean and normalize SRT captions.

    Fixes common issues:
    - Removes duplicate consecutive captions
    - Fixes overlapping timecodes
    - Merges very short captions
    - Ensures minimum gap between captions

    Args:
        captions: List of SRTCaption objects
        min_gap_ms: Minimum gap between captions (default 50ms)
        max_duration_ms: Maximum caption duration (default 7000ms)
        merge_threshold_ms: Merge captions shorter than this (default 1000ms)

    Returns:
        Cleaned list of SRTCaption objects
    """
    if not captions:
        return []

    cleaned = []
    prev_caption = None

    for caption in captions:
        # Skip empty captions
        if not caption.text.strip():
            continue

        # Skip duplicates
        if prev_caption and caption.text.strip() == prev_caption.text.strip():
            # Extend previous caption's end time if needed
            if caption.end_ms > prev_caption.end_ms:
                prev_caption.end_ms = caption.end_ms
            continue

        # Fix negative duration
        if caption.end_ms <= caption.start_ms:
            caption.end_ms = caption.start_ms + 1000  # Default 1 second

        # Fix overlaps with previous caption
        if prev_caption and caption.start_ms < prev_caption.end_ms + min_gap_ms:
            # Adjust start time to maintain minimum gap
            caption.start_ms = prev_caption.end_ms + min_gap_ms

        # Merge very short captions with previous if possible
        if (prev_caption and
            caption.duration_ms < merge_threshold_ms and
            caption.start_ms - prev_caption.end_ms < 500):  # Close in time
            # Merge into previous caption
            prev_caption.text = prev_caption.text + '\n' + caption.text
            prev_caption.end_ms = caption.end_ms
            continue

        cleaned.append(caption)
        prev_caption = caption

    # Renumber
    for i, caption in enumerate(cleaned, 1):
        caption.index = i

    return cleaned


def get_srt_duration(captions: List[SRTCaption]) -> int:
    """Get total duration from captions in milliseconds.

    Args:
        captions: List of SRTCaption objects

    Returns:
        End time of last caption in milliseconds
    """
    if not captions:
        return 0
    return max(c.end_ms for c in captions)
