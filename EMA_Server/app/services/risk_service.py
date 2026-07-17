"""Risk assessment and snapshot persistence."""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models import models_for
from app.services.baseline_fields import baseline_to_profile_dict
from app.services.session_fields import parse_task_date


LEVEL_META = {
    "unknown": {
        "label": "待评估",
        "className": "risk-unknown",
        "summary": "数据不足，暂无法给出风险评估。",
    },
    "low": {
        "label": "低风险",
        "className": "risk-low",
        "summary": "当前信号整体稳定，请继续保持规律打卡。",
    },
    "medium": {
        "label": "中等关注",
        "className": "risk-medium",
        "summary": "部分指标出现波动，建议关注自身状态并善用资源页。",
    },
    "high": {
        "label": "需重点关注",
        "className": "risk-high",
        "summary": "检测到较高风险信号，建议及时寻求支持或联系心理中心。",
    },
}


def _latest_questionnaire(
    db: Session,
    user_id: int,
    task_date: str | None = None,
    session_id: int | None = None,
    *,
    user=None,
):
    EmaQuestion = models_for(user=user, db=db).EmaQuestion
    query = db.query(EmaQuestion).filter(EmaQuestion.user_id == user_id)
    if task_date:
        query = query.filter(EmaQuestion.task_date == task_date)
    if session_id is not None:
        query = query.filter(EmaQuestion.session_id == session_id)
    return query.order_by(EmaQuestion.answered_at.desc()).first()


def _questionnaire_answers(record) -> dict | None:
    if not record:
        return None
    return {
        "mood": record.mood,
        "stress": record.stress,
        "anxiety": record.anxiety,
        "lonely": record.lonely,
        "sleep": record.sleep,
        "fatigue": record.fatigue,
        "function": record.function,
        "negative": record.negative,
    }


def _score_baseline(profile: dict) -> tuple[int, list]:
    score = 0
    factors = []
    if profile.get("self_harm") == "是":
        score += 4
        factors.append({"label": "基线自伤想法筛查", "value": "阳性", "source": "基线测评"})
    if profile.get("phq9_1") == "几乎每天" or profile.get("phq9_2") == "几乎每天":
        score += 2
        factors.append({"label": "PHQ-9 筛查", "value": "偏高", "source": "基线测评"})
    if profile.get("gad7_1") == "几乎每天" or profile.get("gad7_2") == "几乎每天":
        score += 2
        factors.append({"label": "GAD-7 筛查", "value": "偏高", "source": "基线测评"})
    if profile.get("treatment_now") == "是":
        score += 1
        factors.append({"label": "当前治疗/用药", "value": "是", "source": "基线测评"})
    return score, factors


def _score_recent_ema(answers: dict | None) -> tuple[int, list, list]:
    score = 0
    factors = []
    alerts = []
    if not answers:
        return score, factors, alerts

    mood = answers.get("mood")
    if isinstance(mood, (int, float)) and mood <= 3:
        score += 2
        factors.append({"label": "今日心情", "value": f"{mood}/10", "source": "EMA"})
        alerts.append(
            {
                "id": "low_mood",
                "level": "warn",
                "title": "心情偏低",
                "desc": f"今日心情评分较低（{mood}/10），建议适当休息或寻求支持。",
            }
        )

    stress = answers.get("stress")
    if isinstance(stress, (int, float)) and stress >= 7:
        score += 1
        factors.append({"label": "今日压力", "value": f"{stress}/10", "source": "EMA"})
        alerts.append(
            {
                "id": "high_stress",
                "level": "warn",
                "title": "压力偏高",
                "desc": f"今日压力评分较高（{stress}/10），可尝试呼吸放松等自助练习。",
            }
        )

    if answers.get("negative") == "是":
        score += 3
        factors.append({"label": "消极想法", "value": "是", "source": "EMA"})
        alerts.append(
            {
                "id": "negative_thoughts",
                "level": "danger",
                "title": "出现消极想法",
                "desc": "今日报告出现明显消极想法，如有需要请使用资源页热线或联系心理中心。",
            }
        )

    return score, factors, alerts


def _resolve_level(total: int, critical: bool) -> str:
    if critical or total >= 6:
        return "high"
    if total >= 3:
        return "medium"
    return "low"


def _avg(values: list[float]) -> float:
    if not values:
        return 0
    return sum(values) / len(values)


def _compute_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0
    mid = (len(values) + 1) // 2
    return _avg(values[mid:]) - _avg(values[:mid])


def _future_date_label(offset_days: int) -> str:
    d = date.today() + timedelta(days=offset_days)
    return f"{d.month}/{d.day}"


def _build_forecast(current_score: int, critical: bool, missed_days: int, ema_trend: dict) -> dict:
    trend_delta = 0.0
    if ema_trend.get("moodSlope", 0) < -0.5:
        trend_delta += 0.4
    if ema_trend.get("stressSlope", 0) > 0.5:
        trend_delta += 0.5
    if missed_days >= 3:
        trend_delta += 0.6
    if missed_days >= 7:
        trend_delta += 0.4

    trend_label = "平稳"
    if trend_delta >= 0.8:
        trend_label = "上升"
    elif trend_delta <= -0.3 and ema_trend.get("moodSlope", 0) > 0.3:
        trend_label = "下降"

    days = []
    peak = "low"
    for i in range(1, 8):
        projected = current_score + round(trend_delta * i)
        if missed_days >= 3 and i <= 5:
            projected += 1
        projected = max(0, min(15, projected))
        level = _resolve_level(projected, critical and i <= 3)
        if level == "high":
            peak = "high"
        elif level == "medium" and peak != "high":
            peak = "medium"
        meta = LEVEL_META[level]
        days.append(
            {
                "dayIndex": i,
                "dateLabel": _future_date_label(i),
                "score": projected,
                "level": level,
                "levelLabel": meta["label"],
                "levelClass": meta["className"],
                "barWidth": round((projected / 15) * 100),
            }
        )

    peak_meta = LEVEL_META[peak]
    if peak == "high":
        summary = "结合近期信号，未来一周需持续关注，建议主动寻求支持。"
    elif trend_label == "上升":
        summary = "近期波动与行为模式显示，未来一周风险可能缓慢上升，请保持规律打卡。"
    elif trend_label == "下降":
        summary = "近期状态有所改善，预计未来一周风险逐步回落。"
    else:
        summary = "基于当前基线与近期数据，预计未来一周风险整体平稳。"

    return {
        "days": days,
        "trendLabel": trend_label,
        "summary": summary,
        "peakLevelLabel": peak_meta["label"],
        "peakLevelClass": peak_meta["className"],
        "hasForecast": True,
    }


def _recent_ema_trend(db: Session, user_id: int, *, user=None) -> dict:
    EmaQuestion = models_for(user=user, db=db).EmaQuestion
    records = (
        db.query(EmaQuestion)
        .filter(EmaQuestion.user_id == user_id)
        .order_by(EmaQuestion.task_date.asc(), EmaQuestion.answered_at.asc())
        .all()
    )
    by_date = {}
    for record in records:
        by_date[record.task_date] = record
    recent_dates = sorted(by_date.keys())[-7:]
    mood_vals = [by_date[d].mood for d in recent_dates]
    stress_vals = [by_date[d].stress for d in recent_dates]
    return {
        "moodSlope": _compute_slope([float(v) for v in mood_vals]),
        "stressSlope": _compute_slope([float(v) for v in stress_vals]),
        "dataDays": len(recent_dates),
    }


def _count_missed_days(db: Session, user_id: int, *, user=None) -> int:
    EmaQuestion = models_for(user=user, db=db).EmaQuestion
    missed = 0
    for i in range(1, 15):
        day = (date.today() - timedelta(days=i)).isoformat()
        exists = (
            db.query(EmaQuestion.id)
            .filter(EmaQuestion.user_id == user_id, EmaQuestion.task_date == day)
            .first()
        )
        if not exists:
            missed += 1
        else:
            break
    return missed


def _behavior_alerts(db: Session, user_id: int, missed_days: int, *, user=None) -> tuple[int, list]:
    SkipEvent = models_for(user=user, db=db).SkipEvent
    score = 0
    alerts = []
    if missed_days >= 3:
        score += 2
        alerts.append(
            {
                "id": "missed_days",
                "level": "danger" if missed_days >= 5 else "warn",
                "title": "连续缺测",
                "desc": f"已连续 {missed_days} 天未完成 EMA 打卡，缺测模式可能提示状态变化。",
            }
        )
    voice_skips = db.query(SkipEvent).filter(SkipEvent.user_id == user_id, SkipEvent.media_type == "voice").count()
    video_skips = db.query(SkipEvent).filter(SkipEvent.user_id == user_id, SkipEvent.media_type == "video").count()
    if voice_skips >= 3 or video_skips >= 3:
        score += 1
        alerts.append(
            {
                "id": "task_skip",
                "level": "warn",
                "title": "任务跳过偏多",
                "desc": f"语音跳过 {voice_skips} 次，视频跳过 {video_skips} 次。",
            }
        )
    return score, alerts


def _empty_assessment() -> dict[str, Any]:
    meta = LEVEL_META["unknown"]
    return {
        "hasAssessment": False,
        "current": {
            "level": "unknown",
            "levelLabel": meta["label"],
            "levelClass": meta["className"],
            "score": 0,
            "summary": meta["summary"],
            "updatedLabel": "暂无数据",
            "factors": [],
        },
        "forecast": {
            "hasForecast": False,
            "days": [],
            "summary": "",
            "trendLabel": "",
            "peakLevelLabel": "",
            "peakLevelClass": "",
        },
        "alerts": [],
        "alertCount": 0,
    }


def compute_risk_assessment(
    db: Session,
    user,
    *,
    task_date: str | None = None,
    session_id: int | None = None,
    save_snapshot: bool = False,
    computed_at: datetime | None = None,
) -> dict[str, Any]:
    m = models_for(user=user, db=db)
    baseline = db.query(m.BaselineProfile).filter(m.BaselineProfile.user_id == user.id).first()
    latest_q = _latest_questionnaire(db, user.id, task_date, session_id, user=user)
    if not baseline and not latest_q:
        return _empty_assessment()

    profile = baseline_to_profile_dict(baseline) if baseline else {}
    answers = _questionnaire_answers(latest_q)
    b_score, factors = _score_baseline(profile)
    e_score, ema_factors, ema_alerts = _score_recent_ema(answers)
    missed_days = _count_missed_days(db, user.id, user=user)
    behavior_score, behavior_alerts = _behavior_alerts(db, user.id, missed_days, user=user)

    critical = profile.get("self_harm") == "是" or (answers and answers.get("negative") == "是")
    total = b_score + e_score + behavior_score
    level = _resolve_level(total, critical)
    meta = LEVEL_META[level]
    ema_trend = _recent_ema_trend(db, user.id, user=user)
    forecast = _build_forecast(total, critical, missed_days, ema_trend)
    all_alerts = ema_alerts + behavior_alerts

    updated_label = "暂无数据"
    if latest_q:
        updated_label = f"更新于 {latest_q.task_date} EMA（第 {latest_q.session_id} 轮）"
    elif baseline:
        updated_label = "基于基线测评"

    result = {
        "hasAssessment": True,
        "current": {
            "level": level,
            "levelLabel": meta["label"],
            "levelClass": meta["className"],
            "score": total,
            "summary": meta["summary"],
            "updatedLabel": updated_label,
            "factors": factors + ema_factors,
        },
        "forecast": forecast,
        "alerts": all_alerts,
        "alertCount": len(all_alerts),
        "task_date": task_date or (latest_q.task_date if latest_q else parse_task_date(None)),
        "session_id": session_id if session_id is not None else (latest_q.session_id if latest_q else 1),
    }

    if save_snapshot:
        td = result["task_date"]
        sid = int(result["session_id"])
        at = computed_at or datetime.now()
        _persist_risk_snapshots(db, user.id, td, sid, result, at, user=user)

    return result


def _persist_risk_snapshots(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
    result: dict[str, Any],
    computed_at: datetime,
    *,
    user=None,
) -> None:
    RiskSnapshot = models_for(user=user, db=db).RiskSnapshot
    payloads = [
        ("current", result["current"]),
        ("forecast", result["forecast"]),
        ("alerts", {"alerts": result["alerts"], "alertCount": result["alertCount"]}),
    ]
    for snap_type, data in payloads:
        stmt = mysql_insert(RiskSnapshot).values(
            user_id=user_id,
            task_date=task_date,
            session_id=session_id,
            snapshot_type=snap_type,
            result_data=data,
            computed_at=computed_at,
        )
        stmt = stmt.on_duplicate_key_update(
            result_data=stmt.inserted.result_data,
            computed_at=stmt.inserted.computed_at,
        )
        db.execute(stmt)
    db.commit()


def save_checkin_risk_snapshot(
    db: Session,
    user,
    task_date: str,
    session_id: int,
    computed_at: datetime | None = None,
) -> dict[str, Any]:
    return compute_risk_assessment(
        db,
        user,
        task_date=task_date,
        session_id=session_id,
        save_snapshot=True,
        computed_at=computed_at,
    )


def load_risk_assessment_from_snapshots(
    db: Session,
    user_id: int,
    task_date: str | None = None,
    session_id: int | None = None,
    *,
    user=None,
) -> dict[str, Any] | None:
    RiskSnapshot = models_for(user=user, db=db).RiskSnapshot
    query = db.query(RiskSnapshot).filter(RiskSnapshot.user_id == user_id)
    if task_date:
        query = query.filter(RiskSnapshot.task_date == task_date)
    if session_id is not None:
        query = query.filter(RiskSnapshot.session_id == session_id)

    latest = query.order_by(RiskSnapshot.computed_at.desc()).first()
    if not latest:
        return None

    td = latest.task_date
    sid = latest.session_id
    rows = (
        db.query(RiskSnapshot)
        .filter(
            RiskSnapshot.user_id == user_id,
            RiskSnapshot.task_date == td,
            RiskSnapshot.session_id == sid,
        )
        .all()
    )
    by_type = {row.snapshot_type: row.result_data for row in rows}
    current = by_type.get("current")
    forecast = by_type.get("forecast")
    alerts_payload = by_type.get("alerts") or {}
    if not current:
        return None

    return {
        "hasAssessment": True,
        "current": current,
        "forecast": forecast or {"hasForecast": False, "days": [], "summary": "", "trendLabel": "", "peakLevelLabel": "", "peakLevelClass": ""},
        "alerts": alerts_payload.get("alerts") or [],
        "alertCount": alerts_payload.get("alertCount") or 0,
        "task_date": td,
        "session_id": sid,
    }
