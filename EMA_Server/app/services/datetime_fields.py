"""Parse and format client/server datetime fields."""

from datetime import datetime, timedelta, timezone
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
_DT_FORMAT = "%Y-%m-%d %H:%M:%S"


def ms_to_datetime(at_ms: int | None) -> datetime | None:
    if at_ms is None:
        return None
    return datetime.fromtimestamp(int(at_ms) / 1000, CN_TZ).replace(tzinfo=None)


def datetime_to_ms(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CN_TZ)
    return int(dt.timestamp() * 1000)


def format_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime(_DT_FORMAT)


def parse_datetime_value(raw: Any) -> datetime | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    if isinstance(raw, (int, float)):
        return ms_to_datetime(int(raw))
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        return ms_to_datetime(int(text))
    for fmt in (_DT_FORMAT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(text.replace("Z", ""), fmt.replace("Z", ""))
        except ValueError:
            continue
    if len(text) >= 19:
        try:
            return datetime.strptime(text[:19], _DT_FORMAT)
        except ValueError:
            pass
    raise ValueError(f"无法解析时间: {raw}")


def parse_client_at(data: dict[str, Any] | None = None, *, at_ms: int | None = None) -> datetime:
    if data:
        for key in ("client_at", "answered_at", "written_at", "recorded_at", "started_at", "completed_at", "computed_at", "referred_at"):
            parsed = parse_datetime_value(data.get(key))
            if parsed:
                return parsed
        for key in ("client_at_ms", "at", "clientAtMs", "answered_at_ms", "written_at_ms", "recorded_at_ms", "started_at_ms", "completed_at_ms", "computed_at_ms"):
            parsed = ms_to_datetime(data.get(key))
            if parsed:
                return parsed
    parsed = ms_to_datetime(at_ms)
    if parsed:
        return parsed
    return datetime.now()


def parse_optional_at(data: dict[str, Any] | None = None, *keys: str) -> datetime | None:
    if not data:
        return None
    for key in keys:
        parsed = parse_datetime_value(data.get(key))
        if parsed:
            return parsed
        ms_key = f"{key}_ms" if not key.endswith("_ms") else key
        parsed = ms_to_datetime(data.get(ms_key))
        if parsed:
            return parsed
    return None
