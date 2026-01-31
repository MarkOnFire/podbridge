"""Transcript completeness validation.

Detects when an LLM has truncated a long transcript by comparing
the formatter output word count against the source transcript word count.
This catches the common failure mode where models silently stop generating
mid-transcript and report success.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Minimum coverage ratio (formatter output words / source words).
# Below this threshold, the transcript is flagged as likely truncated.
# The formatter legitimately reduces word count by removing filler words
# and SRT timecodes/indices, but should not drop below ~70%.
DEFAULT_COVERAGE_THRESHOLD = 0.70

# Minimum source word count before applying the check.
# Very short transcripts (under 500 words / ~3 min) produce
# misleading ratios and are unlikely truncation targets.
MIN_SOURCE_WORDS_FOR_CHECK = 500


@dataclass
class CompletenessResult:
    """Result of a transcript completeness check."""

    is_complete: bool
    source_word_count: int
    output_word_count: int
    coverage_ratio: float
    threshold: float
    reason: str
    skipped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_complete": self.is_complete,
            "source_word_count": self.source_word_count,
            "output_word_count": self.output_word_count,
            "coverage_ratio": round(self.coverage_ratio, 3),
            "threshold": self.threshold,
            "reason": self.reason,
            "skipped": self.skipped,
        }


def count_content_words(text: str) -> int:
    """Count meaningful words in formatter output.

    Strips markdown formatting, HTML comments (provenance headers,
    review notes), and metadata header blocks so we're comparing
    actual transcript content words only.

    The formatter output structure is:
        <!-- Provenance -->
        **Project:** ...
        **Program:** ...
        ---
        transcript body...
        **Status:** ready_for_editing

    We strip everything before the --- separator (metadata header),
    remove the Status footer, and count the remaining body words.
    """
    # Strip HTML comments (provenance headers, review notes)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Strip everything before (and including) the first --- separator.
    # This removes the metadata header block (Project, Program, etc.)
    parts = re.split(r"^---+\s*$", text, maxsplit=1, flags=re.MULTILINE)
    if len(parts) > 1:
        text = parts[1]
    # Strip markdown bold/italic markers
    text = re.sub(r"\*{1,3}", "", text)
    # Strip markdown headings markers (but keep the text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Strip the Status footer line (after bold markers are removed)
    text = re.sub(r"^Status:\s+.*$", "", text, flags=re.MULTILINE)
    return len(text.split())


def count_source_words(transcript_content: str, is_srt: bool = False) -> int:
    """Count dialogue words in the source transcript.

    For SRT files, strips timecodes and index numbers so we compare
    only the actual spoken content — matching what the formatter
    transforms into prose.
    """
    if is_srt:
        # Remove SRT index numbers (standalone digits on their own line)
        text = re.sub(r"^\d+\s*$", "", transcript_content, flags=re.MULTILINE)
        # Remove SRT timecodes (00:01:23,456 --> 00:01:25,789)
        text = re.sub(r"\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}", "", text)
        return len(text.split())
    return len(transcript_content.split())


def check_completeness(
    formatter_output: str,
    source_transcript: str,
    is_srt: bool = False,
    source_word_count: Optional[int] = None,
    duration_minutes: Optional[float] = None,
    threshold: float = DEFAULT_COVERAGE_THRESHOLD,
    min_source_words: int = MIN_SOURCE_WORDS_FOR_CHECK,
) -> CompletenessResult:
    """Check whether the formatter output covers the full source transcript.

    Compares word counts between source and output to detect truncation.
    The formatter legitimately reduces word count (filler removal, SRT
    formatting cleanup), but should not drop below the threshold.

    Args:
        formatter_output: The formatter_output.md content
        source_transcript: The raw source transcript content
        is_srt: Whether the source is an SRT file
        source_word_count: Pre-computed source word count (overrides counting)
        duration_minutes: Known duration in minutes (included in report)
        threshold: Minimum coverage ratio (default 0.70)
        min_source_words: Minimum source words to apply check (default 500)

    Returns:
        CompletenessResult with pass/fail and details
    """
    # Count dialogue words in source (stripping SRT formatting)
    src_words = source_word_count if source_word_count is not None else count_source_words(source_transcript, is_srt)

    # Skip check for very short transcripts
    if src_words < min_source_words:
        return CompletenessResult(
            is_complete=True,
            source_word_count=src_words,
            output_word_count=0,
            coverage_ratio=1.0,
            threshold=threshold,
            reason=f"Skipped: source too short ({src_words} words < {min_source_words} minimum)",
            skipped=True,
        )

    # Count content words in formatter output
    out_words = count_content_words(formatter_output)

    # Calculate coverage ratio
    coverage = out_words / src_words if src_words > 0 else 0.0

    is_complete = coverage >= threshold

    if is_complete:
        reason = f"Coverage {coverage:.1%} meets threshold {threshold:.0%}"
    else:
        missing_words = src_words - out_words
        missing_pct = (1 - coverage) * 100
        reason = (
            f"TRUNCATION DETECTED: Coverage {coverage:.1%} below threshold {threshold:.0%}. "
            f"Output has {out_words:,} words vs {src_words:,} source words "
            f"(missing ~{missing_words:,} words / ~{missing_pct:.0f}% of content)"
        )
        if duration_minutes:
            reason += f". Source duration: {duration_minutes:.1f} minutes"

    return CompletenessResult(
        is_complete=is_complete,
        source_word_count=src_words,
        output_word_count=out_words,
        coverage_ratio=coverage,
        threshold=threshold,
        reason=reason,
    )
