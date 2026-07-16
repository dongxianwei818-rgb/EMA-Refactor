"""步数序列统计与个体化基线计算。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import statistics


def parse_task_date(value: str) -> date:
    return date.fromisoformat(value)


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def build_daily_step_map(records: list[Any]) -> dict[str, int]:
    """按 task_date 聚合；同日多条取最大步数（微信运动当日总量）。"""
    by_date: dict[str, int] = {}
    for rec in records:
        td = rec.task_date
        steps = int(rec.steps)
        by_date[td] = max(by_date.get(td, 0), steps)
    return by_date


def sorted_dates(step_map: dict[str, int]) -> list[str]:
    return sorted(step_map.keys())


def compute_personal_baseline(
    step_map: dict[str, int],
    before_date: str,
    window_days: int = 14,
) -> float | None:
    """个人基线：目标日之前 window_days 内有效日的中位数。"""
    end = parse_task_date(before_date)
    start = end - timedelta(days=window_days)
    values = []
    for td, steps in step_map.items():
        d = parse_task_date(td)
        if start <= d < end:
            values.append(steps)
    if len(values) < 3:
        return statistics.mean(values) if values else None
    return float(statistics.median(values))


def compute_avg_last_n(step_map: dict[str, int], target_date: str, n: int = 7) -> float | None:
    end = parse_task_date(target_date)
    start = end - timedelta(days=n - 1)
    values = []
    for td, steps in step_map.items():
        d = parse_task_date(td)
        if start <= d <= end:
            values.append(steps)
    return round(sum(values) / len(values), 2) if values else None


def compute_fluctuation(step_map: dict[str, int], target_date: str, window_days: int = 14) -> dict[str, Any]:
    end = parse_task_date(target_date)
    start = end - timedelta(days=window_days - 1)
    values = [steps for td, steps in step_map.items() if start <= parse_task_date(td) <= end]
    if len(values) < 2:
        return {"std": None, "cv": None, "regularity_score": None, "label": "insufficient_data"}
    std = float(statistics.stdev(values))
    mean = float(statistics.mean(values))
    cv = round(std / mean, 4) if mean else None
    regularity = round(max(0.0, 1.0 - min(cv or 0, 1.0)), 4)
    label = "regular"
    if cv is not None and cv > 0.45:
        label = "irregular"
    elif cv is not None and cv < 0.2:
        label = "stable"
    return {
        "std": round(std, 2),
        "cv": cv,
        "regularity_score": regularity,
        "label": label,
        "sample_days": len(values),
    }


def count_consecutive_low_days(
    step_map: dict[str, int],
    target_date: str,
    baseline: float | None,
    low_ratio: float = 0.4,
) -> dict[str, Any]:
    if baseline is None or baseline <= 0:
        return {"count": 0, "threshold": None}
    threshold = baseline * low_ratio
    count = 0
    d = parse_task_date(target_date)
    while True:
        td = d.isoformat()
        if td not in step_map:
            break
        if step_map[td] >= threshold:
            break
        count += 1
        d -= timedelta(days=1)
    return {"count": count, "threshold": round(threshold, 2)}


def compute_baseline_deviation(today_steps: int, baseline: float | None) -> dict[str, Any]:
    if baseline is None or baseline <= 0:
        return {
            "absolute_delta": None,
            "relative_delta": None,
            "percent_change": None,
            "label": "unknown",
        }
    delta = today_steps - baseline
    relative = round(delta / baseline, 4)
    pct = round(relative * 100, 2)
    label = "normal"
    if relative <= -0.5:
        label = "sharp_drop"
    elif relative <= -0.25:
        label = "below_baseline"
    elif relative >= 0.25:
        label = "above_baseline"
    return {
        "absolute_delta": int(delta),
        "relative_delta": relative,
        "percent_change": pct,
        "label": label,
    }


def compute_weekend_weekday_rhythm(
    step_map: dict[str, int],
    target_date: str,
    window_days: int = 28,
) -> dict[str, Any]:
    end = parse_task_date(target_date)
    start = end - timedelta(days=window_days - 1)
    weekday_vals: list[int] = []
    weekend_vals: list[int] = []
    for td, steps in step_map.items():
        d = parse_task_date(td)
        if not (start <= d <= end):
            continue
        if is_weekend(d):
            weekend_vals.append(steps)
        else:
            weekday_vals.append(steps)
    wd_avg = round(sum(weekday_vals) / len(weekday_vals), 2) if weekday_vals else None
    we_avg = round(sum(weekend_vals) / len(weekend_vals), 2) if weekend_vals else None
    diff = None
    ratio = None
    label = "unknown"
    if wd_avg is not None and we_avg is not None and wd_avg > 0:
        diff = round(we_avg - wd_avg, 2)
        ratio = round(we_avg / wd_avg, 4)
        if ratio >= 1.15:
            label = "weekend_more_active"
        elif ratio <= 0.85:
            label = "weekend_less_active"
        else:
            label = "balanced"
    return {
        "weekday_avg": wd_avg,
        "weekend_avg": we_avg,
        "difference": diff,
        "weekend_to_weekday_ratio": ratio,
        "label": label,
        "weekday_sample_days": len(weekday_vals),
        "weekend_sample_days": len(weekend_vals),
    }


def activity_level_label(steps: int, baseline: float | None) -> str:
    if baseline and baseline > 0:
        ratio = steps / baseline
        if ratio < 0.4:
            return "very_low"
        if ratio < 0.7:
            return "low"
        if ratio > 1.3:
            return "high"
        return "moderate"
    if steps < 2000:
        return "very_low"
    if steps < 5000:
        return "low"
    if steps > 10000:
        return "high"
    return "moderate"
