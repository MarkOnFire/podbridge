"""Utility functions for Editorial Assistant v3.0 API.

Provides timezone-aware datetime handling and common utilities.
"""

from datetime import datetime, timezone
from typing import Optional


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
