"""基于五项 EMA 采集特征的融合预测趋势。

问卷 / 日记 / 语音 / 视频 / 步数 → 日度风险分数 → 历史序列 + 未来 7 天预测。
优先读取 *_features；无特征时回退到原始打卡数据。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.risk_service import LEVEL_META


MODALITIES = (
    ("questionnaire", "问卷"),
    ("diary", "日记"),
    ("voice", "语音"),
    ("video", "视频"),
    ("steps", "步数"),
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


def _as_dict(features: Any) -> dict:
    return features if isinstance(features, dict) else {}


def _latest_feature_by_date(records: list) -> dict[str, Any]:
    by_date: dict[str, Any] = {}
    for row in records:
        day = getattr(row, "task_date", None)
        if not day or day in by_date:
            continue
        by_date[day] = row
    return by_date


def _load_feature_map(db: Session, model, user_id: int, date_keys: list[str]) -> dict[str, Any]:
    rows = (
        db.query(model)
        .filter(
            model.user_id == user_id,
            model.task_date.in_(date_keys),
            model.status == "done",
        )
        .order_by(model.created_at.desc())
        .all()
    )
    return _latest_feature_by_date(rows)


def _extract_modality_day(
    modality: str,
    feature_row: Any | None,
    raw_fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """返回单日单模态：elevated / score(0-15) / reasons / hasData。"""
    raw_fallback = raw_fallback or {}
    if feature_row and feature_row.features:
        feats = _as_dict(feature_row.features)
        if modality == "questionnaire":
            comp = _as_dict(feats.get("composite_signals"))
            elevated = bool(comp.get("elevated_distress"))
            ema = _as_dict(feats.get("ema"))
            metrics = _as_dict(ema.get("metrics"))
            distress_vals = []
            for key in ("mood", "stress", "anxiety", "sleep", "fatigue", "lonely", "function", "negative"):
                m = _as_dict(metrics.get(key))
                if m.get("distress_ema") is not None:
                    try:
                        distress_vals.append(float(m["distress_ema"]))
                    except (TypeError, ValueError):
                        pass
            score = int(round((sum(distress_vals) / len(distress_vals)) * 1.5)) if distress_vals else (10 if elevated else 2)
            return {
                "elevated": elevated,
                "score": max(0, min(15, score)),
                "reasons": list(comp.get("reasons") or [])[:3],
                "hasData": True,
            }
        if modality == "diary":
            comp = _as_dict(feats.get("composite_risk_signals") or feats.get("composite_signals"))
            elevated = bool(comp.get("elevated_distress"))
            emotional = _as_dict(feats.get("emotional_words"))
            try:
                emo_score = float(emotional.get("score") or 0)
            except (TypeError, ValueError):
                emo_score = 0.0
            distress_emo = max(-emo_score, 0.0)
            hopeless = _as_dict(feats.get("hopelessness"))
            try:
                hop = float(hopeless.get("score") or 0)
            except (TypeError, ValueError):
                hop = 0.0
            score = int(round(min(15, distress_emo * 8 + hop * 7 + (4 if elevated else 0))))
            return {
                "elevated": elevated,
                "score": max(0, min(15, score)),
                "reasons": list(comp.get("reasons") or [])[:3],
                "hasData": True,
            }
        if modality == "voice":
            comp = _as_dict(feats.get("composite_signals"))
            elevated = bool(comp.get("elevated_distress"))
            semantic = _as_dict(feats.get("semantic"))
            try:
                distress = float(semantic.get("distress_score") or (0.7 if elevated else 0.2))
            except (TypeError, ValueError):
                distress = 0.7 if elevated else 0.2
            score = int(round(distress * 15))
            return {
                "elevated": elevated,
                "score": max(0, min(15, score)),
                "reasons": list(comp.get("reasons") or [])[:3],
                "hasData": True,
            }
        if modality == "video":
            comp = _as_dict(feats.get("composite_signals"))
            elevated = bool(comp.get("elevated_distress"))
            score = 11 if elevated else 3
            if comp.get("depressed_expression_pattern"):
                score = max(score, 12)
            if comp.get("flat_affect"):
                score = max(score, 9)
            return {
                "elevated": elevated,
                "score": max(0, min(15, score)),
                "reasons": list(comp.get("reasons") or [])[:3],
                "hasData": True,
            }
        if modality == "steps":
            comp = _as_dict(feats.get("composite_signals"))
            elevated = bool(
                comp.get("elevated_inactivity_risk") or comp.get("activity_decline")
            )
            score = 10 if elevated else 2
            if comp.get("activity_decline"):
                score = max(score, 8)
            return {
                "elevated": elevated,
                "score": max(0, min(15, score)),
                "reasons": list(comp.get("reasons") or [])[:3],
                "hasData": True,
            }

    # 原始数据回退
    if modality == "questionnaire" and raw_fallback.get("answers"):
        a = raw_fallback["answers"]
        vals = []
        for key, invert in (
            ("mood", True),
            ("stress", False),
            ("anxiety", False),
            ("sleep", True),
        ):
            if a.get(key) is None:
                continue
            try:
                v = float(a[key])
            except (TypeError, ValueError):
                continue
            vals.append(10 - v if invert else v)
        if vals:
            avg = sum(vals) / len(vals)
            score = int(round((avg / 10) * 15))
            return {
                "elevated": avg >= 6,
                "score": max(0, min(15, score)),
                "reasons": ["基于问卷原始评分回退估算"],
                "hasData": True,
            }
    if modality == "steps" and raw_fallback.get("steps") is not None:
        steps = int(raw_fallback["steps"] or 0)
        elevated = steps > 0 and steps < 3000
        score = 9 if elevated else (2 if steps >= 6000 else 5)
        return {
            "elevated": elevated,
            "score": score,
            "reasons": ["基于步数原始数据回退估算"] if steps else [],
            "hasData": steps > 0,
        }
    if modality == "diary" and raw_fallback.get("diaryLen"):
        length = int(raw_fallback["diaryLen"] or 0)
        return {
            "elevated": False,
            "score": 2 if length >= 20 else 4,
            "reasons": ["基于日记字数回退估算"],
            "hasData": length > 0,
        }
    if modality in ("voice", "video") and raw_fallback.get(f"{modality}Sec") is not None:
        sec = float(raw_fallback[f"{modality}Sec"] or 0)
        skipped = bool(raw_fallback.get(f"{modality}Skip"))
        if skipped:
            return {
                "elevated": True,
                "score": 8,
                "reasons": ["当日跳过采集"],
                "hasData": True,
            }
        return {
            "elevated": False,
            "score": 2 if sec >= 20 else 5,
            "reasons": ["基于时长回退估算"],
            "hasData": sec > 0,
        }

    return {"elevated": False, "score": 0, "reasons": [], "hasData": False}


def _raw_fallbacks(db: Session, user_id: int, date_keys: list[str], *, user=None) -> dict[str, dict]:
    m = models_for(user=user, db=db)
    out: dict[str, dict] = {d: {} for d in date_keys}

    q_rows = (
        db.query(m.EmaQuestion)
        .filter(m.EmaQuestion.user_id == user_id, m.EmaQuestion.task_date.in_(date_keys))
        .order_by(m.EmaQuestion.answered_at.desc())
        .all()
    )
    seen_q: set[str] = set()
    for row in q_rows:
        if row.task_date in seen_q:
            continue
        seen_q.add(row.task_date)
        out[row.task_date]["answers"] = {
            "mood": row.mood,
            "stress": row.stress,
            "anxiety": row.anxiety,
            "sleep": row.sleep,
        }

    for model, key in (
        (m.EmaStep, "steps"),
        (m.EmaDiary, "diary"),
        (m.EmaVoice, "voice"),
        (m.EmaVideo, "video"),
    ):
        rows = (
            db.query(model)
            .filter(model.user_id == user_id, model.task_date.in_(date_keys))
            .order_by(model.id.desc())
            .all()
        )
        seen: set[str] = set()
        for row in rows:
            if row.task_date in seen:
                continue
            seen.add(row.task_date)
            if key == "steps":
                out[row.task_date]["steps"] = row.steps
            elif key == "diary":
                out[row.task_date]["diaryLen"] = getattr(row, "length", None) or len(
                    getattr(row, "text", "") or ""
                )
            elif key == "voice":
                out[row.task_date]["voiceSec"] = getattr(row, "duration_sec", 0) or 0
                out[row.task_date]["voiceSkip"] = bool(getattr(row, "skip", False))
            elif key == "video":
                out[row.task_date]["videoSec"] = getattr(row, "duration_sec", 0) or 0
                out[row.task_date]["videoSkip"] = bool(getattr(row, "skip", False))
    return out


def _fuse_day_scores(modality_scores: dict[str, dict]) -> tuple[int, list[str]]:
    weights = {
        "questionnaire": 1.2,
        "diary": 1.0,
        "voice": 1.0,
        "video": 0.9,
        "steps": 0.8,
    }
    total = 0.0
    wsum = 0.0
    reasons: list[str] = []
    for mid, label in MODALITIES:
        item = modality_scores.get(mid) or {}
        if not item.get("hasData"):
            continue
        w = weights[mid]
        total += float(item.get("score") or 0) * w
        wsum += w
        if item.get("elevated"):
            reasons.append(f"{label}信号偏高")
    if wsum <= 0:
        return 0, []
    return int(round(max(0, min(15, total / wsum)))), reasons[:4]


def _build_forecast_from_series(history_scores: list[int]) -> dict[str, Any]:
    scored = [s for s in history_scores if s is not None]
    if not scored:
        return {
            "hasForecast": False,
            "days": [],
            "trendLabel": "—",
            "summary": "完成五项 EMA 采集并生成特征后，将展示融合预测趋势。",
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
        projected = int(round(current + slope * i))
        projected = max(0, min(15, projected))
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
        summary = "综合五项 EMA 特征，未来一周融合风险偏高，建议关注并寻求支持。"
    elif trend_label == "上升":
        summary = "五项特征融合显示风险呈上升趋势，请保持规律打卡并留意身心变化。"
    elif trend_label == "下降":
        summary = "多项模态信号改善，预计未来一周融合风险逐步回落。"
    else:
        summary = "基于近期五项 EMA 特征，预计未来一周融合风险整体平稳。"

    return {
        "hasForecast": True,
        "days": days,
        "trendLabel": trend_label,
        "summary": summary,
        "peakLevelLabel": peak_meta["label"],
        "peakLevelClass": peak_meta["className"],
    }


def build_modality_prediction_trend(
    db: Session,
    user,
    days: int = 7,
) -> dict[str, Any]:
    """聚合五项 EMA 特征，返回历史融合趋势 + 未来 7 天预测。"""
    date_keys = _date_keys(days)
    m = models_for(user=user, db=db)

    feature_maps = {
        "questionnaire": _load_feature_map(db, m.QuestionsFeature, user.id, date_keys),
        "diary": _load_feature_map(db, m.TextFeature, user.id, date_keys),
        "voice": _load_feature_map(db, m.VoiceFeature, user.id, date_keys),
        "video": _load_feature_map(db, m.VideoFeature, user.id, date_keys),
        "steps": _load_feature_map(db, m.StepFeature, user.id, date_keys),
    }
    raw_by_day = _raw_fallbacks(db, user.id, date_keys, user=user)

    history: list[dict[str, Any]] = []
    fused_scores: list[int | None] = []
    modality_latest: dict[str, Any] = {
        mid: {"id": mid, "label": label, "hasData": False, "elevated": False, "score": 0, "reasons": []}
        for mid, label in MODALITIES
    }

    for day in date_keys:
        modality_scores: dict[str, dict] = {}
        for mid, label in MODALITIES:
            item = _extract_modality_day(
                mid,
                feature_maps[mid].get(day),
                raw_by_day.get(day),
            )
            modality_scores[mid] = item
            if item.get("hasData"):
                modality_latest[mid] = {
                    "id": mid,
                    "label": label,
                    "hasData": True,
                    "elevated": bool(item.get("elevated")),
                    "score": int(item.get("score") or 0),
                    "reasons": item.get("reasons") or [],
                    "dateLabel": _short_date(day),
                }
        fused, reasons = _fuse_day_scores(modality_scores)
        has_any = any(v.get("hasData") for v in modality_scores.values())
        fused_scores.append(fused if has_any else None)
        history.append(
            {
                "date": day,
                "dateLabel": _short_date(day),
                "hasData": has_any,
                "score": fused if has_any else None,
                "level": _resolve_level(fused) if has_any else "unknown",
                "levelLabel": LEVEL_META[_resolve_level(fused) if has_any else "unknown"]["label"],
                "levelClass": LEVEL_META[_resolve_level(fused) if has_any else "unknown"]["className"],
                "barWidth": round((fused / 15) * 100) if has_any else 0,
                "reasons": reasons,
                "modalities": {
                    mid: {
                        "elevated": modality_scores[mid].get("elevated"),
                        "score": modality_scores[mid].get("score"),
                        "hasData": modality_scores[mid].get("hasData"),
                    }
                    for mid, _ in MODALITIES
                },
            }
        )

    valid_scores = [s for s in fused_scores if s is not None]
    forecast = _build_forecast_from_series(valid_scores)
    has_prediction = bool(valid_scores)

    current_score = valid_scores[-1] if valid_scores else 0
    current_level = _resolve_level(current_score) if has_prediction else "unknown"
    current_meta = LEVEL_META[current_level]

    elevated_count = sum(1 for v in modality_latest.values() if v.get("elevated"))
    return {
        "hasPrediction": has_prediction,
        "summary": (
            f"综合问卷、日记、语音、视频、步数五项特征，当前融合风险指数 {current_score}。"
            if has_prediction
            else "完成 EMA 五项采集后，将基于特征提取结果展示预测趋势。"
        ),
        "currentScore": current_score if has_prediction else None,
        "currentLevelLabel": current_meta["label"],
        "currentLevelClass": current_meta["className"],
        "elevatedModalityCount": elevated_count,
        "modalities": [modality_latest[mid] for mid, _ in MODALITIES],
        "history": history,
        "forecast": forecast,
    }
