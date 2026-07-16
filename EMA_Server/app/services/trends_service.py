"""Trends page data aggregated from server tables."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import BehaviorMeta, EmaQuestion, EmaStep, User
from app.services.risk_service import compute_risk_assessment, load_risk_assessment_from_snapshots


def _date_keys(days: int) -> list[str]:
    keys = []
    for i in range(days - 1, -1, -1):
        keys.append((date.today() - timedelta(days=i)).isoformat())
    return keys


def _format_short_date(date_str: str) -> str:
    parts = date_str.split("-")
    if len(parts) != 3:
        return date_str
    return f"{int(parts[1])}/{int(parts[2])}"


def _questionnaire_days(db: Session, user_id: int, date_keys: list[str]) -> list[dict]:
    records = (
        db.query(EmaQuestion)
        .filter(EmaQuestion.user_id == user_id, EmaQuestion.task_date.in_(date_keys))
        .order_by(EmaQuestion.answered_at.desc())
        .all()
    )
    by_date: dict[str, EmaQuestion] = {}
    for record in records:
        if record.task_date not in by_date:
            by_date[record.task_date] = record

    days = []
    for day in date_keys:
        record = by_date.get(day)
        answers = _questionnaire_answers(record) if record else {}
        days.append(
            {
                "date": day,
                "dateLabel": _format_short_date(day),
                "hasData": record is not None,
                "answers": answers,
            }
        )
    return days


def _questionnaire_answers(record: EmaQuestion | None) -> dict:
    if not record:
        return {}
    return {
        "mood": record.mood,
        "stress": record.stress,
        "anxiety": record.anxiety,
        "sleep": record.sleep,
    }


def _build_metric_trend(days: list[dict], metric_id: str) -> list[dict]:
    points = []
    for day in days:
        value = day["answers"].get(metric_id) if day["hasData"] else None
        num = None if value is None else float(value)
        has_data = num is not None
        points.append(
            {
                "dateLabel": day["dateLabel"],
                "value": int(num) if has_data else None,
                "hasData": has_data,
                "barWidth": round((num / 10) * 100) if has_data else 0,
            }
        )
    return points


def _steps_history(db: Session, user_id: int, date_keys: list[str]) -> list[dict]:
    records = (
        db.query(EmaStep)
        .filter(EmaStep.user_id == user_id, EmaStep.task_date.in_(date_keys))
        .order_by(EmaStep.recorded_at.desc())
        .all()
    )
    by_date: dict[str, int] = {}
    for record in records:
        if record.task_date not in by_date:
            by_date[record.task_date] = record.steps
    return [{"date": day, "steps": by_date.get(day)} for day in date_keys]


def _steps_analytics(db: Session, user_id: int) -> dict[str, Any]:
    records = (
        db.query(EmaStep)
        .filter(EmaStep.user_id == user_id)
        .order_by(EmaStep.task_date.desc(), EmaStep.recorded_at.desc())
        .limit(90)
        .all()
    )
    hist = [{"date": r.task_date, "steps": r.steps} for r in records]
    today = hist[0]["steps"] if hist else 0
    count7 = min(7, len(hist))
    avg7 = round(sum(item["steps"] for item in hist[:count7]) / count7) if count7 else 0
    baseline = round(sum(item["steps"] for item in hist[: min(7, len(hist))]) / min(7, len(hist))) if hist else 0
    if len(hist) >= 3 and not baseline:
        baseline = avg7
    threshold = baseline * 0.4 if baseline else 2000
    low_days = 0
    for item in hist[:14]:
        if item["steps"] < threshold:
            low_days += 1
        else:
            break
    deviation = round(((today - baseline) / baseline) * 100) if baseline and today else 0
    return {
        "today": today,
        "avg7": avg7,
        "baseline": baseline,
        "lowDays": low_days,
        "deviation": deviation,
        "hist": hist,
    }


def _build_steps_trend(hist: list[dict], date_keys: list[str]) -> list[dict]:
    step_map = {item["date"]: item["steps"] for item in hist if item.get("date")}
    max_steps = max((step_map.get(day) or 0 for day in date_keys), default=0) or 1
    trend = []
    for day in date_keys:
        steps = step_map.get(day)
        has_data = steps is not None
        trend.append(
            {
                "dateLabel": _format_short_date(day),
                "steps": steps if has_data else None,
                "hasData": has_data,
                "barWidth": round((steps / max_steps) * 100) if has_data else 0,
            }
        )
    return trend


def _behavior_stats(db: Session, user_id: int) -> dict[str, Any]:
    meta_row = db.query(BehaviorMeta).filter(BehaviorMeta.user_id == user_id).first()
    meta = meta_row.meta_data if meta_row else {}

    def avg_arr(arr: list | None) -> int:
        if not arr:
            return 0
        return round(sum(arr) / len(arr))

    missed_days = 0
    for i in range(1, 15):
        day = (date.today() - timedelta(days=i)).isoformat()
        exists = (
            db.query(EmaQuestion.id)
            .filter(EmaQuestion.user_id == user_id, EmaQuestion.task_date == day)
            .first()
        )
        if not exists:
            missed_days += 1
        else:
            break

    return {
        "missedDays": missed_days,
        "avgDiaryWords": avg_arr(meta.get("diaryWordCounts")),
        "avgVoiceSec": avg_arr(meta.get("voiceDurations")),
        "avgVideoSec": avg_arr(meta.get("videoDurations")),
        "openCount": meta.get("openCount") or 0,
        "recheckinCount": meta.get("recheckinCount") or 0,
    }


def get_trends_overview(db: Session, user: User, days: int = 7) -> dict[str, Any]:
    date_keys = _date_keys(days)
    questionnaire_days = _questionnaire_days(db, user.id, date_keys)
    metrics = [
        {
            "id": metric_id,
            "label": label,
            "points": _build_metric_trend(questionnaire_days, metric_id),
        }
        for metric_id, label in (
            ("mood", "心情"),
            ("stress", "压力"),
            ("anxiety", "焦虑"),
            ("sleep", "睡眠"),
        )
    ]
    steps_hist = _steps_history(db, user.id, date_keys)
    steps_analytics = _steps_analytics(db, user.id)
    steps_trend = _build_steps_trend(steps_hist, date_keys)
    has_data = any(day["hasData"] for day in questionnaire_days) or any(item["hasData"] for item in steps_trend)

    risk = load_risk_assessment_from_snapshots(db, user.id)
    if not risk:
        risk = compute_risk_assessment(db, user, save_snapshot=False)

    return {
        "hasData": has_data,
        "risk": risk,
        "metrics": metrics,
        "stepsTrend": steps_trend,
        "stepsAnalytics": steps_analytics,
        "stats": _behavior_stats(db, user.id),
        "dayCount": days,
    }
