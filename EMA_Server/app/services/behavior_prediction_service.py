"""基于 behavior_features 的使用行为预测趋势。

打卡依从 / 缺测 / 回避跳过 / 昼夜节律 / 表达活跃等 → 日度风险分数 → 历史 + 未来 7 天预测。
优先读取 behavior_features；无特征时回退 behavior_meta / 缺测统计。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.risk_service import LEVEL_META


BEHAVIOR_SIGNALS = (
    ("adherence", "依从性"),
    ("missingness", "缺测模式"),
    ("avoidance", "回避跳过"),
    ("circadian", "昼夜节律"),
    ("expression", "表达活跃"),
)


def _short_date(date_str: str) -> str:
    parts = date_str.split("-")
    if len(parts) != 3:
        return date_str
    return f"{int(parts[1])}/{int(parts[2])}"


def _date_keys(days: int) -> list[str]:
    return [(date.today() - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _future_date_label(offset_days: int) -> str:
    d = date.today() + timedelta(days=offset_days)
    return f"{d.month}/{d.day}"


def _resolve_level(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _clamp_score(score: float) -> int:
    return int(round(max(0, min(15, score))))


def _latest_feature_by_date(records: list) -> dict[str, Any]:
    by_date: dict[str, Any] = {}
    for row in records:
        day = getattr(row, "task_date", None)
        if not day or day in by_date:
            continue
        by_date[day] = row
    return by_date


def _load_behavior_features(db: Session, user_id: int, date_keys: list[str], *, user=None) -> dict[str, Any]:
    BehaviorFeature = models_for(user=user, db=db).BehaviorFeature
    rows = (
        db.query(BehaviorFeature)
        .filter(
            BehaviorFeature.user_id == user_id,
            BehaviorFeature.task_date.in_(date_keys),
            BehaviorFeature.status == "done",
        )
        .order_by(BehaviorFeature.created_at.desc())
        .all()
    )
    return _latest_feature_by_date(rows)


def _score_adherence(compliance: dict) -> tuple[int, bool, list[str]]:
    label = compliance.get("label") or ""
    if label == "incomplete":
        return 12, True, ["打卡未完成"]
    if label == "prolonged":
        return 10, True, ["完成耗时过长"]
    if label == "delayed":
        return 8, True, ["未按时完成"]
    if label in ("on_time", "timely", "normal"):
        return 2, False, []
    return 4, False, []


def _score_missingness(missed: dict, missingness: dict) -> tuple[int, bool, list[str]]:
    reasons: list[str] = []
    consecutive = int(missed.get("consecutive_days") or 0)
    elevated = bool(missed.get("elevated") or missingness.get("label") == "elevated")
    score = min(15, consecutive * 3)
    if missingness.get("label") == "elevated":
        score = max(score, 10)
        reasons.append("缺测/回避模式偏高")
    if missed.get("elevated") or consecutive >= 2:
        reasons.append(f"连续缺测 {consecutive} 天")
        score = max(score, 6 if consecutive < 3 else 9)
    if not elevated and consecutive == 0:
        score = 1
    return _clamp_score(score), elevated, reasons


def _score_avoidance(skip_rates: dict, missingness: dict) -> tuple[int, bool, list[str]]:
    elevated = bool(
        skip_rates.get("elevated_avoidance") or missingness.get("partial_media_avoidance")
    )
    reasons: list[str] = []
    score = 2
    if skip_rates.get("elevated_avoidance"):
        score = 11
        reasons.append("语音/视频跳过率偏高")
    elif missingness.get("partial_media_avoidance"):
        score = 8
        reasons.append("存在媒体任务部分回避")
    try:
        voice_rate = float(skip_rates.get("voice_skip_rate") or 0)
        video_rate = float(skip_rates.get("video_skip_rate") or 0)
        score = max(score, int(round(max(voice_rate, video_rate) * 12)))
    except (TypeError, ValueError):
        pass
    return _clamp_score(score), elevated, reasons


def _score_circadian(timing: dict) -> tuple[int, bool, list[str]]:
    disrupted = bool(timing.get("circadian_disruption"))
    if disrupted:
        return 9, True, ["打卡时间分散或偏晚"]
    label = timing.get("label") or ""
    if label in ("late", "irregular"):
        return 7, True, ["打卡节律不稳定"]
    return 2, False, []


def _score_expression(expression: dict) -> tuple[int, bool, list[str]]:
    diary = _as_dict(expression.get("diary_word_count"))
    voice = _as_dict(expression.get("voice_duration_sec"))
    reasons: list[str] = []
    score = 2
    elevated = False
    if diary.get("label") == "declining":
        score = max(score, 8)
        elevated = True
        reasons.append("日记字数下降")
    if voice.get("label") == "declining":
        score = max(score, 8)
        elevated = True
        reasons.append("语音时长下降")
    if diary.get("label") == "rising" or voice.get("label") == "rising":
        score = min(score, 3)
    return _clamp_score(score), elevated, reasons


def _extract_signal_scores(feats: dict) -> dict[str, dict]:
    timing = _as_dict(feats.get("checkin_timing"))
    compliance = _as_dict(feats.get("compliance"))
    missed = _as_dict(feats.get("consecutive_missed_days"))
    expression = _as_dict(feats.get("content_expression"))
    skip_rates = _as_dict(feats.get("skip_rates"))
    missingness = _as_dict(feats.get("missingness_pattern"))

    adherence_s, adherence_e, adherence_r = _score_adherence(compliance)
    miss_s, miss_e, miss_r = _score_missingness(missed, missingness)
    avoid_s, avoid_e, avoid_r = _score_avoidance(skip_rates, missingness)
    circ_s, circ_e, circ_r = _score_circadian(timing)
    expr_s, expr_e, expr_r = _score_expression(expression)

    return {
        "adherence": {"score": adherence_s, "elevated": adherence_e, "reasons": adherence_r, "hasData": True},
        "missingness": {"score": miss_s, "elevated": miss_e, "reasons": miss_r, "hasData": True},
        "avoidance": {"score": avoid_s, "elevated": avoid_e, "reasons": avoid_r, "hasData": True},
        "circadian": {"score": circ_s, "elevated": circ_e, "reasons": circ_r, "hasData": True},
        "expression": {"score": expr_s, "elevated": expr_e, "reasons": expr_r, "hasData": True},
    }


def _fuse_behavior_day(feats: dict) -> tuple[int, bool, list[str], dict[str, dict]]:
    signals = _extract_signal_scores(feats)
    comp = _as_dict(feats.get("composite_signals"))
    weights = {
        "adherence": 1.1,
        "missingness": 1.3,
        "avoidance": 1.2,
        "circadian": 0.9,
        "expression": 0.9,
    }
    total = 0.0
    wsum = 0.0
    reasons: list[str] = list(comp.get("reasons") or [])[:4]
    for sid, _ in BEHAVIOR_SIGNALS:
        item = signals[sid]
        w = weights[sid]
        total += item["score"] * w
        wsum += w
        if item["elevated"] and item["reasons"]:
            for r in item["reasons"]:
                if r not in reasons:
                    reasons.append(r)

    fused = _clamp_score(total / wsum) if wsum else 0
    elevated = bool(comp.get("elevated_engagement_risk")) or fused >= 8
    if elevated and fused < 8:
        fused = max(fused, 9)
    if comp.get("missingness_signal"):
        fused = max(fused, 8)
    if comp.get("avoidance_pattern"):
        fused = max(fused, 8)
    if comp.get("low_adherence"):
        fused = max(fused, 7)

    open_patterns = _as_dict(feats.get("open_patterns"))
    task_duration = _as_dict(feats.get("task_duration"))
    if open_patterns.get("label") == "low_engagement":
        fused = min(15, fused + 1)
    if task_duration.get("label") == "hesitant":
        fused = min(15, fused + 1)
        if "任务耗时增加" not in reasons:
            reasons.append("近期任务耗时增加")

    return fused, elevated, reasons[:5], signals


def _fallback_from_meta(db: Session, user_id: int, *, user=None) -> dict[str, Any] | None:
    """无按日 behavior_features 时，用 behavior_meta + 连续缺测做单点回退。"""
    m = models_for(user=user, db=db)
    meta_row = db.query(m.BehaviorMeta).filter(m.BehaviorMeta.user_id == user_id).first()
    if not meta_row or not meta_row.meta_data:
        return None
    meta = dict(meta_row.meta_data)
    EmaQuestion = m.EmaQuestion
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

    voice_durs = meta.get("voiceDurations") or []
    diary_lens = meta.get("diaryWordCounts") or []
    open_count = int(meta.get("openCount") or 0)
    recheckin = int(meta.get("recheckinCount") or 0)

    signals = {
        "adherence": {
            "score": 7 if recheckin >= 3 else 3,
            "elevated": recheckin >= 3,
            "reasons": ["补卡次数偏多"] if recheckin >= 3 else [],
            "hasData": True,
        },
        "missingness": {
            "score": _clamp_score(missed_days * 3),
            "elevated": missed_days >= 2,
            "reasons": [f"连续缺测 {missed_days} 天"] if missed_days >= 2 else [],
            "hasData": True,
        },
        "avoidance": {
            "score": 5,
            "elevated": False,
            "reasons": [],
            "hasData": bool(voice_durs),
        },
        "circadian": {"score": 3, "elevated": False, "reasons": [], "hasData": open_count > 0},
        "expression": {
            "score": 6 if (diary_lens and diary_lens[-1] < 20) else 3,
            "elevated": bool(diary_lens and diary_lens[-1] < 20),
            "reasons": ["近期日记较短"] if diary_lens and diary_lens[-1] < 20 else [],
            "hasData": bool(diary_lens or voice_durs),
        },
    }
    fused = _clamp_score(
        (
            signals["adherence"]["score"] * 1.1
            + signals["missingness"]["score"] * 1.3
            + signals["avoidance"]["score"] * 1.0
            + signals["circadian"]["score"] * 0.8
            + signals["expression"]["score"] * 0.9
        )
        / 5.1
    )
    elevated = missed_days >= 2 or recheckin >= 3
    reasons = []
    for item in signals.values():
        reasons.extend(item["reasons"])
    return {
        "score": fused,
        "elevated": elevated,
        "reasons": reasons[:5] or ["基于使用行为元数据回退估算"],
        "signals": signals,
    }


def _build_forecast_from_series(history_scores: list[int]) -> dict[str, Any]:
    scored = [s for s in history_scores if s is not None]
    if not scored:
        return {
            "hasForecast": False,
            "days": [],
            "trendLabel": "—",
            "summary": "完成打卡并生成行为特征后，将展示行为预测趋势。",
            "peakLevelLabel": LEVEL_META["unknown"]["label"],
            "peakLevelClass": LEVEL_META["unknown"]["className"],
        }

    current = scored[-1]
    if len(scored) >= 3:
        slope = (scored[-1] - scored[0]) / max(1, len(scored) - 1)
    else:
        slope = 0.0

    trend_label = "平稳"
    if slope >= 0.6:
        trend_label = "上升"
    elif slope <= -0.6:
        trend_label = "下降"

    days = []
    peak = "low"
    for i in range(1, 8):
        projected = _clamp_score(current + slope * i)
        level = _resolve_level(projected)
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
        summary = "使用行为特征显示未来一周参与/回避风险偏高，建议关注打卡规律与媒体任务完成情况。"
    elif trend_label == "上升":
        summary = "行为信号呈上升趋势，请留意缺测、跳过与打卡节律变化。"
    elif trend_label == "下降":
        summary = "近期依从与表达活跃有所改善，预计行为风险逐步回落。"
    else:
        summary = "基于近期 behavior_features，预计未来一周行为风险整体平稳。"

    return {
        "hasForecast": True,
        "days": days,
        "trendLabel": trend_label,
        "summary": summary,
        "peakLevelLabel": peak_meta["label"],
        "peakLevelClass": peak_meta["className"],
    }


def build_behavior_prediction_trend(
    db: Session,
    user,
    days: int = 7,
) -> dict[str, Any]:
    """聚合 behavior_features，返回历史行为风险趋势 + 未来 7 天预测。"""
    date_keys = _date_keys(days)
    feature_map = _load_behavior_features(db, user.id, date_keys, user=user)

    history: list[dict[str, Any]] = []
    fused_scores: list[int | None] = []
    signal_latest: dict[str, Any] = {
        sid: {
            "id": sid,
            "label": label,
            "hasData": False,
            "elevated": False,
            "score": 0,
            "reasons": [],
        }
        for sid, label in BEHAVIOR_SIGNALS
    }

    for day in date_keys:
        row = feature_map.get(day)
        if row and row.features:
            fused, elevated, reasons, signals = _fuse_behavior_day(_as_dict(row.features))
            fused_scores.append(fused)
            history.append(
                {
                    "date": day,
                    "dateLabel": _short_date(day),
                    "hasData": True,
                    "score": fused,
                    "level": _resolve_level(fused),
                    "levelLabel": LEVEL_META[_resolve_level(fused)]["label"],
                    "levelClass": LEVEL_META[_resolve_level(fused)]["className"],
                    "barWidth": round((fused / 15) * 100),
                    "elevated": elevated,
                    "reasons": reasons,
                    "signals": {
                        sid: {
                            "score": signals[sid]["score"],
                            "elevated": signals[sid]["elevated"],
                            "hasData": True,
                        }
                        for sid, _ in BEHAVIOR_SIGNALS
                    },
                }
            )
            for sid, label in BEHAVIOR_SIGNALS:
                item = signals[sid]
                signal_latest[sid] = {
                    "id": sid,
                    "label": label,
                    "hasData": True,
                    "elevated": bool(item["elevated"]),
                    "score": int(item["score"]),
                    "reasons": item.get("reasons") or [],
                    "dateLabel": _short_date(day),
                }
        else:
            fused_scores.append(None)
            history.append(
                {
                    "date": day,
                    "dateLabel": _short_date(day),
                    "hasData": False,
                    "score": None,
                    "level": "unknown",
                    "levelLabel": LEVEL_META["unknown"]["label"],
                    "levelClass": LEVEL_META["unknown"]["className"],
                    "barWidth": 0,
                    "elevated": False,
                    "reasons": [],
                    "signals": {},
                }
            )

    valid_scores = [s for s in fused_scores if s is not None]
    has_prediction = bool(valid_scores)

    # 全程无日度特征时，用 meta 回退一天
    if not has_prediction:
        fallback = _fallback_from_meta(db, user.id, user=user)
        if fallback:
            has_prediction = True
            today = date.today().isoformat()
            fused = fallback["score"]
            valid_scores = [fused]
            for sid, label in BEHAVIOR_SIGNALS:
                item = fallback["signals"][sid]
                signal_latest[sid] = {
                    "id": sid,
                    "label": label,
                    "hasData": bool(item.get("hasData")),
                    "elevated": bool(item.get("elevated")),
                    "score": int(item.get("score") or 0),
                    "reasons": item.get("reasons") or [],
                    "dateLabel": _short_date(today),
                }
            # 替换今天这一行
            for i, day in enumerate(date_keys):
                if day == today:
                    history[i] = {
                        "date": day,
                        "dateLabel": _short_date(day),
                        "hasData": True,
                        "score": fused,
                        "level": _resolve_level(fused),
                        "levelLabel": LEVEL_META[_resolve_level(fused)]["label"],
                        "levelClass": LEVEL_META[_resolve_level(fused)]["className"],
                        "barWidth": round((fused / 15) * 100),
                        "elevated": fallback["elevated"],
                        "reasons": fallback["reasons"],
                        "signals": {
                            sid: {
                                "score": fallback["signals"][sid]["score"],
                                "elevated": fallback["signals"][sid]["elevated"],
                                "hasData": fallback["signals"][sid]["hasData"],
                            }
                            for sid, _ in BEHAVIOR_SIGNALS
                        },
                    }
                    break
            else:
                history[-1] = {
                    "date": today,
                    "dateLabel": _short_date(today),
                    "hasData": True,
                    "score": fused,
                    "level": _resolve_level(fused),
                    "levelLabel": LEVEL_META[_resolve_level(fused)]["label"],
                    "levelClass": LEVEL_META[_resolve_level(fused)]["className"],
                    "barWidth": round((fused / 15) * 100),
                    "elevated": fallback["elevated"],
                    "reasons": fallback["reasons"],
                    "signals": {},
                }

    forecast = _build_forecast_from_series(valid_scores)
    current_score = valid_scores[-1] if valid_scores else 0
    current_level = _resolve_level(current_score) if has_prediction else "unknown"
    current_meta = LEVEL_META[current_level]
    elevated_count = sum(1 for v in signal_latest.values() if v.get("elevated"))

    return {
        "hasPrediction": has_prediction,
        "summary": (
            f"综合打卡依从、缺测、回避、节律与表达等行为特征，当前行为风险指数 {current_score}。"
            if has_prediction
            else "完成打卡并生成 behavior_features 后，将展示行为特征预测趋势。"
        ),
        "currentScore": current_score if has_prediction else None,
        "currentLevelLabel": current_meta["label"],
        "currentLevelClass": current_meta["className"],
        "elevatedSignalCount": elevated_count,
        "signals": [signal_latest[sid] for sid, _ in BEHAVIOR_SIGNALS],
        "history": history,
        "forecast": forecast,
    }
