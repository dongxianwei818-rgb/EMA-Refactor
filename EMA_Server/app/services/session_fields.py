"""Parse session_id and task_date from API / sync payloads."""

import re
from datetime import datetime, timedelta, timezone
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
_TASK_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_session_id(data: dict[str, Any] | None, default: int = 1) -> int:
    if not data:
        return default
    raw = data.get("session_id")
    if raw is None:
        raw = data.get("sessionId")
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value >= 1 else default


def _normalize_task_date(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if _TASK_DATE_RE.match(text):
        return text
    if len(text) >= 10 and _TASK_DATE_RE.match(text[:10]):
        return text[:10]
    return None


def task_date_from_dt(at: datetime) -> str:
    if at.tzinfo is None:
        at = at.replace(tzinfo=CN_TZ)
    return at.strftime("%Y-%m-%d")


def parse_task_date(data: dict[str, Any] | None, at: datetime | None = None) -> str:
    """Return YYYY-MM-DD for the check-in day (答题/提交当天)."""
    if data:
        normalized = _normalize_task_date(data.get("task_date"))
        if normalized:
            return normalized
        normalized = _normalize_task_date(data.get("date"))
        if normalized:
            return normalized
    if at:
        return task_date_from_dt(at)
    return datetime.now(CN_TZ).strftime("%Y-%m-%d")
