"""Trends page data aggregated from server tables."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.behavior_prediction_service import build_behavior_prediction_trend
from app.services.modality_prediction_service import build_modality_prediction_trend
from app.services.risk_service import compute_risk_assessment


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
    EmaQuestion = models_for(db=db).EmaQuestion
    records = (
        db.query(EmaQuestion)
        .filter(EmaQuestion.user_id == user_id, EmaQuestion.task_date.in_(date_keys))
        .order_by(EmaQuestion.answered_at.desc())
        .all()
    )
    by_date: dict[str, Any] = {}
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


def _questionnaire_answers(record: Any | None) -> dict:
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
    EmaStep = models_for(db=db).EmaStep
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
    EmaStep = models_for(db=db).EmaStep
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


def _behavior_stats(db: Session, user_id: int, *, user=None) -> dict[str, Any]:
    """从 behavior_meta + EMA 业务表挖掘打卡概况指标。"""
    m = models_for(user=user, db=db)
    meta_row = db.query(m.BehaviorMeta).filter(m.BehaviorMeta.user_id == user_id).first()
    meta = dict(meta_row.meta_data) if meta_row and meta_row.meta_data else {}

    def avg_arr(arr: list | None) -> int:
        if not arr:
            return 0
        nums = [float(x) for x in arr if x is not None]
        if not nums:
            return 0
        return round(sum(nums) / len(nums))

    def avg_or_fallback(meta_key: str, table_avg: int) -> int:
        meta_avg = avg_arr(meta.get(meta_key))
        return meta_avg if meta_avg > 0 else table_avg

    missed_days = 0
    for i in range(1, 15):
        day = (date.today() - timedelta(days=i)).isoformat()
        exists = (
            db.query(m.EmaQuestion.id)
            .filter(m.EmaQuestion.user_id == user_id, m.EmaQuestion.task_date == day)
            .first()
        )
        if not exists:
            missed_days += 1
        else:
            break

    # 语音 / 视频时长（表优先回退：meta 为空时用业务表）
    voice_rows = (
        db.query(m.EmaVoice.duration_sec, m.EmaVoice.skip)
        .filter(m.EmaVoice.user_id == user_id)
        .order_by(m.EmaVoice.id.desc())
        .limit(60)
        .all()
    )
    video_rows = (
        db.query(m.EmaVideo.duration_sec, m.EmaVideo.skip)
        .filter(m.EmaVideo.user_id == user_id)
        .order_by(m.EmaVideo.id.desc())
        .limit(60)
        .all()
    )
    voice_secs = [int(r.duration_sec or 0) for r in voice_rows if not r.skip and (r.duration_sec or 0) > 0]
    video_secs = [int(r.duration_sec or 0) for r in video_rows if not r.skip and (r.duration_sec or 0) > 0]
    voice_skip_table = sum(1 for r in voice_rows if r.skip)
    video_skip_table = sum(1 for r in video_rows if r.skip)

    # 日记字数
    diary_rows = (
        db.query(m.EmaDiary.length)
        .filter(m.EmaDiary.user_id == user_id)
        .order_by(m.EmaDiary.id.desc())
        .limit(60)
        .all()
    )
    diary_lens = [int(r.length or 0) for r in diary_rows if (r.length or 0) > 0]

    # 步数
    step_rows = (
        db.query(m.EmaStep.task_date, m.EmaStep.steps)
        .filter(m.EmaStep.user_id == user_id)
        .order_by(m.EmaStep.task_date.desc(), m.EmaStep.recorded_at.desc())
        .limit(90)
        .all()
    )
    step_by_day: dict[str, int] = {}
    for row in step_rows:
        if row.task_date not in step_by_day:
            step_by_day[row.task_date] = int(row.steps or 0)
    step_vals = list(step_by_day.values())
    avg_steps = round(sum(step_vals) / len(step_vals)) if step_vals else 0
    recent7 = step_vals[:7]
    avg_steps_7 = round(sum(recent7) / len(recent7)) if recent7 else 0

    # 问卷/整轮打卡耗时（checkin_sessions）
    sessions = (
        db.query(m.CheckinSession)
        .filter(
            m.CheckinSession.user_id == user_id,
            m.CheckinSession.completed_at.isnot(None),
            m.CheckinSession.started_at.isnot(None),
        )
        .order_by(m.CheckinSession.id.desc())
        .limit(60)
        .all()
    )
    session_secs: list[int] = []
    for s in sessions:
        try:
            sec = int((s.completed_at - s.started_at).total_seconds())
        except Exception:
            continue
        if 0 < sec < 24 * 3600:
            session_secs.append(sec)
    avg_questionnaire_sec = round(sum(session_secs) / len(session_secs)) if session_secs else 0

    # 任务耗时（behavior_meta.taskDurations，毫秒）
    task_ms: list[float] = []
    for item in meta.get("taskDurations") or []:
        if isinstance(item, dict) and item.get("ms") is not None:
            try:
                task_ms.append(float(item["ms"]))
            except (TypeError, ValueError):
                pass
        elif isinstance(item, (int, float)):
            task_ms.append(float(item))
    avg_task_sec = round((sum(task_ms) / len(task_ms)) / 1000) if task_ms else 0

    # 问卷提交次数 / 打卡天数
    q_count = db.query(m.EmaQuestion.id).filter(m.EmaQuestion.user_id == user_id).count()
    checkin_days = (
        db.query(m.EmaQuestion.task_date)
        .filter(m.EmaQuestion.user_id == user_id)
        .distinct()
        .count()
    )
    completed_sessions = (
        db.query(m.CheckinSession.id)
        .filter(
            m.CheckinSession.user_id == user_id,
            m.CheckinSession.completed_at.isnot(None),
        )
        .count()
    )

    voice_skips = int(meta.get("voiceSkips") or 0) or voice_skip_table
    video_skips = int(meta.get("videoSkips") or 0) or video_skip_table
    skip_events_voice = (
        db.query(m.SkipEvent.id)
        .filter(m.SkipEvent.user_id == user_id, m.SkipEvent.media_type == "voice")
        .count()
    )
    skip_events_video = (
        db.query(m.SkipEvent.id)
        .filter(m.SkipEvent.user_id == user_id, m.SkipEvent.media_type == "video")
        .count()
    )
    if skip_events_voice > voice_skips:
        voice_skips = skip_events_voice
    if skip_events_video > video_skips:
        video_skips = skip_events_video

    avg_diary = avg_or_fallback("diaryWordCounts", avg_arr(diary_lens))
    avg_voice = avg_or_fallback("voiceDurations", avg_arr(voice_secs))
    avg_video = avg_or_fallback("videoDurations", avg_arr(video_secs))

    return {
        "missedDays": missed_days,
        "avgDiaryWords": avg_diary,
        "avgVoiceSec": avg_voice,
        "avgVideoSec": avg_video,
        "avgQuestionnaireSec": avg_questionnaire_sec,
        "avgTaskSec": avg_task_sec,
        "avgSteps": avg_steps,
        "avgSteps7": avg_steps_7,
        "openCount": int(meta.get("openCount") or 0),
        "recheckinCount": int(meta.get("recheckinCount") or 0),
        "voiceSkips": voice_skips,
        "videoSkips": video_skips,
        "questionnaireCount": int(q_count),
        "checkinDays": int(checkin_days),
        "completedSessions": int(completed_sessions),
        "diaryCount": len(diary_lens) or len(meta.get("diaryWordCounts") or []),
        "voiceCount": len(voice_secs) or len(meta.get("voiceDurations") or []),
        "videoCount": len(video_secs) or len(meta.get("videoDurations") or []),
        "stepDays": len(step_vals),
    }


def get_trends_overview(db: Session, user, days: int = 7) -> dict[str, Any]:
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

    # 趋势页实时重算，避免沿用快照中的旧分档阈值
    risk = compute_risk_assessment(db, user, save_snapshot=False)

    modality_forecast = build_modality_prediction_trend(db, user, days=days)
    behavior_forecast = build_behavior_prediction_trend(db, user, days=days)

    return {
        "hasData": has_data,
        "risk": risk,
        "modalityForecast": modality_forecast,
        "behaviorForecast": behavior_forecast,
        "metrics": metrics,
        "stepsTrend": steps_trend,
        "stepsAnalytics": steps_analytics,
        "stats": _behavior_stats(db, user.id, user=user),
        "dayCount": days,
    }
