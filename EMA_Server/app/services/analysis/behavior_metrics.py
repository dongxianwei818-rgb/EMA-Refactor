"""行为日志/元信息聚合指标计算。"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta
from typing import Any


def _avg(values: list[float | int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _trend_delta(values: list[float | int], recent_n: int = 3) -> dict[str, Any]:
    """最近 recent_n 次 vs 更早样本的相对变化。"""
    if len(values) < recent_n + 1:
        return {"recent_avg": _avg(values), "delta_ratio": None, "label": "insufficient_data"}
    recent = values[-recent_n:]
    earlier = values[:-recent_n]
    recent_avg = sum(recent) / len(recent)
    earlier_avg = sum(earlier) / len(earlier)
    if earlier_avg <= 0:
        delta_ratio = None
    else:
        delta_ratio = round((recent_avg - earlier_avg) / earlier_avg, 4)
    label = "stable"
    if delta_ratio is not None:
        if delta_ratio <= -0.25:
            label = "declining"
        elif delta_ratio >= 0.25:
            label = "rising"
    return {
        "recent_avg": round(recent_avg, 2),
        "earlier_avg": round(earlier_avg, 2),
        "delta_ratio": delta_ratio,
        "label": label,
    }


def analyze_checkin_timing(
    meta: dict[str, Any],
    log_hours: list[int],
    *,
    late_start: int = 22,
    late_end: int = 5,
) -> dict[str, Any]:
    checkin_times = meta.get("checkinTimes") or []
    hours = [int(c.get("hour")) for c in checkin_times if c.get("hour") is not None]
    hours.extend(log_hours)
    if not hours:
        return {
            "sample_count": 0,
            "mean_hour": None,
            "hour_std": None,
            "late_night_ratio": None,
            "circadian_disruption": False,
            "label": "unknown",
        }

    def is_late(h: int) -> bool:
        return h >= late_start or h < late_end

    late_ratio = sum(1 for h in hours if is_late(h)) / len(hours)
    hour_std = float(statistics.stdev(hours)) if len(hours) > 1 else 0.0
    disrupted = late_ratio >= 0.35 or hour_std >= 4.0
    label = "disrupted" if disrupted else "regular"
    return {
        "sample_count": len(hours),
        "mean_hour": round(sum(hours) / len(hours), 2),
        "hour_std": round(hour_std, 2),
        "late_night_ratio": round(late_ratio, 4),
        "circadian_disruption": disrupted,
        "label": label,
    }


def analyze_compliance(
    session_started: datetime | None,
    session_completed: datetime | None,
    *,
    on_time_minutes: int = 60,
) -> dict[str, Any]:
    if not session_started or not session_completed:
        return {
            "completed": session_completed is not None,
            "duration_sec": None,
            "on_time": None,
            "label": "incomplete" if not session_completed else "unknown",
        }
    duration_sec = int((session_completed - session_started).total_seconds())
    on_time = duration_sec <= on_time_minutes * 60
    label = "on_time" if on_time else "delayed"
    if duration_sec > on_time_minutes * 60 * 2:
        label = "prolonged"
    return {
        "completed": True,
        "duration_sec": duration_sec,
        "on_time": on_time,
        "label": label,
    }


def count_consecutive_missed_days(has_checkin_fn, up_to: date, max_lookback: int = 30) -> dict[str, Any]:
    """连续缺测：从 up_to 前一日往回数无打卡的天数。"""
    count = 0
    d = up_to - timedelta(days=1)
    for _ in range(max_lookback):
        if has_checkin_fn(d.isoformat()):
            break
        count += 1
        d -= timedelta(days=1)
    return {
        "consecutive_days": count,
        "signal_strength": min(count / 7.0, 1.0),
        "elevated": count >= 3,
    }


def analyze_content_expression(meta: dict[str, Any]) -> dict[str, Any]:
    diary = meta.get("diaryWordCounts") or []
    voice = meta.get("voiceDurations") or []
    return {
        "diary_word_count": _trend_delta([int(x) for x in diary if x is not None]),
        "voice_duration_sec": _trend_delta([float(x) for x in voice if x is not None]),
    }


def analyze_skip_rates(
    meta: dict[str, Any],
    db_skip_voice: int,
    db_skip_video: int,
    ema_voice_skip: int,
    ema_video_skip: int,
) -> dict[str, Any]:
    meta_v_skips = int(meta.get("videoSkips") or 0)
    meta_a_skips = int(meta.get("voiceSkips") or 0)
    video_attempts = len(meta.get("videoDurations") or []) + meta_v_skips + ema_video_skip
    voice_attempts = len(meta.get("voiceDurations") or []) + meta_a_skips + ema_voice_skip
    video_skips = max(meta_v_skips, db_skip_video) + ema_video_skip
    voice_skips = max(meta_a_skips, db_skip_voice) + ema_voice_skip
    video_rate = round(video_skips / video_attempts, 4) if video_attempts else None
    voice_rate = round(voice_skips / voice_attempts, 4) if voice_attempts else None
    return {
        "video_skip_count": video_skips,
        "voice_skip_count": voice_skips,
        "video_skip_rate": video_rate,
        "voice_skip_rate": voice_rate,
        "elevated_avoidance": (video_rate or 0) >= 0.5 or (voice_rate or 0) >= 0.5,
    }


def analyze_open_patterns(meta: dict[str, Any], logs_today: int) -> dict[str, Any]:
    open_count = int(meta.get("openCount") or 0)
    recheckin = int(meta.get("recheckinCount") or 0)
    label = "normal"
    if open_count >= 8 or recheckin >= 3:
        label = "high_engagement"
    elif open_count <= 1 and logs_today == 0:
        label = "low_engagement"
    return {
        "open_count": open_count,
        "recheckin_count": recheckin,
        "logs_on_task_date": logs_today,
        "label": label,
    }


def analyze_task_durations(meta: dict[str, Any], log_durations_ms: list[int]) -> dict[str, Any]:
    durations: list[int] = []
    for item in meta.get("taskDurations") or []:
        if isinstance(item, dict) and item.get("ms") is not None:
            durations.append(int(item["ms"]))
        elif isinstance(item, (int, float)):
            durations.append(int(item))
    durations.extend(log_durations_ms)
    if not durations:
        return {"count": 0, "mean_ms": None, "recent_mean_ms": None, "label": "unknown"}
    recent = durations[-5:]
    mean_all = sum(durations) / len(durations)
    mean_recent = sum(recent) / len(recent)
    label = "normal"
    if mean_recent >= mean_all * 1.5 and mean_recent >= 120_000:
        label = "hesitant"
    elif mean_recent <= mean_all * 0.6:
        label = "efficient"
    return {
        "count": len(durations),
        "mean_ms": round(mean_all, 2),
        "recent_mean_ms": round(mean_recent, 2),
        "label": label,
    }


def analyze_missingness_pattern(
    task_date: str,
    has_questionnaire: bool,
    has_diary: bool,
    has_voice: bool,
    has_video: bool,
    voice_skipped: bool,
    video_skipped: bool,
    consecutive_missed: int,
) -> dict[str, Any]:
    missing_tasks: list[str] = []
    if not has_questionnaire:
        missing_tasks.append("questionnaire")
    if not has_diary:
        missing_tasks.append("diary")
    if not has_voice and not voice_skipped:
        missing_tasks.append("voice")
    if not has_video and not video_skipped:
        missing_tasks.append("video")

    partial_avoidance = voice_skipped or video_skipped
    full_miss_today = not has_questionnaire and len(missing_tasks) >= 3

    return {
        "missing_tasks_today": missing_tasks,
        "partial_media_avoidance": partial_avoidance,
        "full_miss_today": full_miss_today,
        "consecutive_missed_days": consecutive_missed,
        "missingness_score": round(
            min(1.0, consecutive_missed / 7.0 + len(missing_tasks) * 0.1 + (0.2 if partial_avoidance else 0)),
            4,
        ),
        "label": "elevated" if consecutive_missed >= 3 or full_miss_today else "normal",
    }
