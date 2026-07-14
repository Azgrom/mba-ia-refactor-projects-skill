"""Timezone-aware UTC helpers (F-013).

`datetime.utcnow()` is deprecated on Python 3.12+ and returns a *naive* datetime
that merely happens to hold UTC. SQLite has no native timezone storage, so values
read back from it can be naive even when written as aware; `ensure_utc` normalizes
on read so comparisons never mix naive and aware datetimes.
"""
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def ensure_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def isoformat(value):
    value = ensure_utc(value)
    return value.isoformat() if value else None
