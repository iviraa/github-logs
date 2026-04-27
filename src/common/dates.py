"""UTC-only date helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def iso_z(dt: datetime) -> str:
    """Return RFC3339/ISO8601 with trailing Z (the form the GitHub API expects)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def last_n_days_window(now: datetime, days: int) -> tuple[datetime, datetime]:
    """[start, end] window covering the last N full days, ending at `now`."""
    return now - timedelta(days=days), now


def weekly_window(end: date) -> tuple[date, date]:
    """7-day window ending on `end` (inclusive)."""
    return end - timedelta(days=6), end


def date_partition(dt: datetime) -> dict[str, str]:
    """Hive-style partition keys for S3 paths."""
    return {
        "year": f"{dt.year:04d}",
        "month": f"{dt.month:02d}",
        "day": f"{dt.day:02d}",
    }
