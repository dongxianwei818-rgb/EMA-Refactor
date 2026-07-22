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
                "level": "warn" if mood > 2 else "danger",
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
                "level": "warn" if stress < 9 else "danger",
                "title": "压力偏高",
                "desc": f"今日压力评分较高（{stress}/10），可尝试呼吸放松等自助练习。",
            }
        )

    anxiety = answers.get("anxiety")
    if isinstance(anxiety, (int, float)) and anxiety >= 7:
        score += 1
        factors.append({"label": "今日焦虑", "value": f"{anxiety}/10", "source": "EMA"})
        alerts.append(
            {
                "id": "high_anxiety",
                "level": "warn" if anxiety < 9 else "danger",
                "title": "焦虑偏高",
                "desc": f"今日焦虑评分较高（{anxiety}/10），建议关注情绪调节与放松练习。",
            }
        )

    sleep = answers.get("sleep")
    if isinstance(sleep, (int, float)) and sleep <= 3:
        score += 1
        factors.append({"label": "今日睡眠", "value": f"{sleep}/10", "source": "EMA"})
        alerts.append(
            {
                "id": "poor_sleep",
                "level": "warn",
                "title": "睡眠质量偏低",
                "desc": f"今日睡眠评分较低（{sleep}/10），睡眠不足可能放大压力与情绪波动。",
            }
        )

    fatigue = answers.get("fatigue")
    if isinstance(fatigue, (int, float)) and fatigue >= 7:
        score += 1
        factors.append({"label": "今日疲惫", "value": f"{fatigue}/10", "source": "EMA"})
        alerts.append(
            {
                "id": "high_fatigue",
                "level": "warn",
                "title": "疲惫感偏高",
                "desc": f"今日疲惫评分较高（{fatigue}/10），建议保证休息并降低当日负担。",
            }
        )

    lonely = answers.get("lonely")
    if isinstance(lonely, (int, float)) and lonely >= 7:
        score += 1
        factors.append({"label": "今日孤独", "value": f"{lonely}/10", "source": "EMA"})
        alerts.append(
            {
                "id": "high_lonely",
                "level": "warn",
                "title": "孤独感偏高",
                "desc": f"今日孤独感评分较高（{lonely}/10），可尝试联系信任的人或使用资源页支持。",
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


def _as_feat_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _latest_done_feature(db: Session, model, user_id: int):
    return (
        db.query(model)
        .filter(model.user_id == user_id, model.status == "done")
        .order_by(model.task_date.desc(), model.created_at.desc())
        .first()
    )


def _alert(
    alert_id: str,
    level: str,
    title: str,
    desc: str,
    *,
    category: str = "综合",
    source: str = "",
    metric: str = "",
) -> dict[str, str]:
    return {
        "id": alert_id,
        "level": level,
        "levelLabel": "重点关注" if level == "danger" else ("提示" if level == "info" else "需留意"),
        "title": title,
        "desc": desc,
        "category": category,
        "source": source,
        "metric": metric,
    }


def _normalize_alert(item: dict) -> dict:
    level = item.get("level") or "warn"
    return {
        "id": item.get("id") or "",
        "level": level,
        "levelLabel": item.get("levelLabel")
        or ("重点关注" if level == "danger" else ("提示" if level == "info" else "需留意")),
        "title": item.get("title") or "异常信号",
        "desc": item.get("desc") or "",
        "category": item.get("category") or "综合",
        "source": item.get("source") or "",
        "metric": item.get("metric") or "",
    }


def _mine_feature_alerts(db: Session, user_id: int, *, user=None) -> list[dict]:
    """从五项 EMA 特征表 + behavior_features 挖掘异常预警。"""
    m = models_for(user=user, db=db)
    alerts: list[dict] = []

    # 问卷特征
    qf = _latest_done_feature(db, m.QuestionsFeature, user_id)
    if qf and qf.features:
        feats = _as_feat_dict(qf.features)
        comp = _as_feat_dict(feats.get("composite_signals"))
        if comp.get("elevated_distress"):
            reasons = "；".join((comp.get("reasons") or [])[:2])
            alerts.append(
                _alert(
                    "q_elevated_distress",
                    "danger",
                    "问卷痛苦信号升高",
                    reasons or f"问卷特征显示痛苦信号升高（{qf.task_date}）。",
                    category="问卷特征",
                    source="questions_features",
                    metric=qf.task_date,
                )
            )

    # 日记文本特征
    tf = _latest_done_feature(db, m.TextFeature, user_id)
    if tf and tf.features:
        feats = _as_feat_dict(tf.features)
        comp = _as_feat_dict(feats.get("composite_risk_signals") or feats.get("composite_signals"))
        hopeless = _as_feat_dict(feats.get("hopelessness"))
        try:
            hop_score = float(hopeless.get("score") or 0)
        except (TypeError, ValueError):
            hop_score = 0.0
        if hop_score >= 0.34:
            alerts.append(
                _alert(
                    "diary_hopelessness",
                    "danger",
                    "日记无助/无望表达",
                    f"日记文本检测到较高无助感信号（{tf.task_date}），建议关注并寻求支持。",
                    category="日记特征",
                    source="text_features",
                    metric=f"无助感 {hop_score:.2f}",
                )
            )
        elif comp.get("elevated_distress"):
            reasons = "；".join((comp.get("reasons") or [])[:2])
            alerts.append(
                _alert(
                    "diary_elevated_distress",
                    "warn",
                    "日记情绪信号偏高",
                    reasons or f"日记特征显示情绪痛苦偏高（{tf.task_date}）。",
                    category="日记特征",
                    source="text_features",
                    metric=tf.task_date,
                )
            )

    # 语音特征
    vf = _latest_done_feature(db, m.VoiceFeature, user_id)
    if vf and vf.features:
        feats = _as_feat_dict(vf.features)
        comp = _as_feat_dict(feats.get("composite_signals"))
        if comp.get("elevated_distress"):
            reasons = "；".join((comp.get("reasons") or [])[:2])
            alerts.append(
                _alert(
                    "voice_elevated_distress",
                    "warn",
                    "语音痛苦信号偏高",
                    reasons or f"语音特征显示痛苦/压力信号偏高（{vf.task_date}）。",
                    category="语音特征",
                    source="voice_features",
                    metric=vf.task_date,
                )
            )
        if comp.get("skipped"):
            alerts.append(
                _alert(
                    "voice_skipped_signal",
                    "warn",
                    "语音任务回避",
                    f"近期语音采集被跳过（{vf.task_date}），回避本身可能是状态信号。",
                    category="语音特征",
                    source="voice_features",
                    metric=vf.task_date,
                )
            )

    # 视频特征
    vid = _latest_done_feature(db, m.VideoFeature, user_id)
    if vid and vid.features:
        feats = _as_feat_dict(vid.features)
        comp = _as_feat_dict(feats.get("composite_signals"))
        if comp.get("depressed_expression_pattern"):
            alerts.append(
                _alert(
                    "video_depressed_expression",
                    "danger",
                    "视频表情低落模式",
                    f"视频特征检测到低落表情模式（{vid.task_date}），建议结合问卷与日记综合关注。",
                    category="视频特征",
                    source="video_features",
                    metric=vid.task_date,
                )
            )
        elif comp.get("flat_affect"):
            alerts.append(
                _alert(
                    "video_flat_affect",
                    "warn",
                    "视频情感表达平坦",
                    f"视频特征提示情感表达偏平坦（{vid.task_date}）。",
                    category="视频特征",
                    source="video_features",
                    metric=vid.task_date,
                )
            )
        elif comp.get("elevated_distress"):
            reasons = "；".join((comp.get("reasons") or [])[:2])
            alerts.append(
                _alert(
                    "video_elevated_distress",
                    "warn",
                    "视频痛苦信号偏高",
                    reasons or f"视频特征显示痛苦信号偏高（{vid.task_date}）。",
                    category="视频特征",
                    source="video_features",
                    metric=vid.task_date,
                )
            )

    # 步数特征
    sf = _latest_done_feature(db, m.StepFeature, user_id)
    if sf and sf.features:
        feats = _as_feat_dict(sf.features)
        comp = _as_feat_dict(feats.get("composite_signals"))
        if comp.get("elevated_inactivity_risk") or comp.get("activity_decline"):
            reasons = "；".join((comp.get("reasons") or [])[:2])
            alerts.append(
                _alert(
                    "steps_activity_decline",
                    "warn",
                    "活动量下降",
                    reasons or f"步数特征显示活动量下降或不活跃风险升高（{sf.task_date}）。",
                    category="步数特征",
                    source="step_features",
                    metric=sf.task_date,
                )
            )

    # 行为特征
    bf = _latest_done_feature(db, m.BehaviorFeature, user_id)
    if bf and bf.features:
        feats = _as_feat_dict(bf.features)
        comp = _as_feat_dict(feats.get("composite_signals"))
        timing = _as_feat_dict(feats.get("checkin_timing"))
        missed = _as_feat_dict(feats.get("consecutive_missed_days"))
        skip_rates = _as_feat_dict(feats.get("skip_rates"))
        expression = _as_feat_dict(feats.get("content_expression"))
        compliance = _as_feat_dict(feats.get("compliance"))
        open_patterns = _as_feat_dict(feats.get("open_patterns"))
        task_duration = _as_feat_dict(feats.get("task_duration"))
        enrichment = _as_feat_dict(feats.get("context_enrichment"))

        if comp.get("elevated_engagement_risk"):
            reasons = "；".join((comp.get("reasons") or [])[:2])
            alerts.append(
                _alert(
                    "behavior_engagement_risk",
                    "danger" if missed.get("elevated") else "warn",
                    "使用行为风险升高",
                    reasons or f"行为特征综合信号偏高（{bf.task_date}）。",
                    category="行为特征",
                    source="behavior_features",
                    metric=bf.task_date,
                )
            )
        if comp.get("avoidance_pattern") or skip_rates.get("elevated_avoidance"):
            voice_rate = skip_rates.get("voice_skip_rate")
            video_rate = skip_rates.get("video_skip_rate")
            rate_bits = []
            if voice_rate is not None:
                rate_bits.append(f"语音跳过率 {float(voice_rate):.0%}")
            if video_rate is not None:
                rate_bits.append(f"视频跳过率 {float(video_rate):.0%}")
            alerts.append(
                _alert(
                    "behavior_avoidance",
                    "warn",
                    "媒体任务回避模式",
                    f"语音/视频跳过或回避模式偏高（{bf.task_date}），可能提示负担感或隐私顾虑。",
                    category="行为特征",
                    source="behavior_features",
                    metric=" · ".join(rate_bits) or bf.task_date,
                )
            )
        if timing.get("circadian_disruption"):
            alerts.append(
                _alert(
                    "behavior_circadian",
                    "warn",
                    "打卡昼夜节律紊乱",
                    f"打卡时间偏晚或分散（{bf.task_date}），可能存在昼夜节律紊乱。",
                    category="行为特征",
                    source="behavior_features",
                    metric=f"时段标准差 {timing.get('hour_std') or '—'}",
                )
            )
        diary_trend = _as_feat_dict(expression.get("diary_word_count"))
        voice_trend = _as_feat_dict(expression.get("voice_duration_sec"))
        if diary_trend.get("label") == "declining" or voice_trend.get("label") == "declining":
            parts = []
            if diary_trend.get("label") == "declining":
                parts.append("日记字数下降")
            if voice_trend.get("label") == "declining":
                parts.append("语音时长下降")
            alerts.append(
                _alert(
                    "behavior_expression_decline",
                    "warn",
                    "表达活跃度下降",
                    f"{'、'.join(parts)}（{bf.task_date}），表达意愿可能减弱。",
                    category="行为特征",
                    source="behavior_features",
                    metric=bf.task_date,
                )
            )
        if compliance.get("label") in ("delayed", "prolonged", "incomplete"):
            label_map = {
                "delayed": "未按时完成打卡",
                "prolonged": "完成打卡耗时过长",
                "incomplete": "打卡未完成",
            }
            dur = compliance.get("duration_sec")
            alerts.append(
                _alert(
                    "behavior_low_adherence",
                    "warn",
                    "打卡依从性下降",
                    f"{label_map.get(compliance.get('label'), '依从性下降')}（{bf.task_date}）。",
                    category="行为特征",
                    source="behavior_features",
                    metric=f"耗时 {dur} 秒" if dur else bf.task_date,
                )
            )
        if open_patterns.get("label") == "high_engagement" and int(missed.get("consecutive_days") or 0) >= 2:
            alerts.append(
                _alert(
                    "behavior_open_but_miss",
                    "warn",
                    "高频打开但持续缺测",
                    f"打开活跃但连续缺测（{bf.task_date}），可能存在矛盾性关注/回避。",
                    category="行为特征",
                    source="behavior_features",
                    metric=str(open_patterns.get("label") or ""),
                )
            )
        if task_duration.get("label") == "hesitant":
            alerts.append(
                _alert(
                    "behavior_task_hesitant",
                    "warn",
                    "任务耗时增加",
                    f"近期任务耗时偏长（{bf.task_date}），可能存在迟疑或负担感。",
                    category="行为特征",
                    source="behavior_features",
                    metric=bf.task_date,
                )
            )
        consistency = enrichment.get("multimodal_consistency")
        try:
            consistency_f = float(consistency) if consistency is not None else None
        except (TypeError, ValueError):
            consistency_f = None
        if consistency_f is not None and consistency_f >= 0.8:
            alerts.append(
                _alert(
                    "behavior_multimodal_consistent",
                    "danger",
                    "多模态风险信号一致",
                    f"行为回避与问卷/步数等 distress 信号高度一致（{bf.task_date}），建议重点关注。",
                    category="行为特征",
                    source="behavior_features",
                    metric=f"一致性 {consistency_f:.2f}",
                )
            )

    return alerts


def _mine_checkin_stats_alerts(db: Session, user_id: int, *, user=None) -> list[dict]:
    """从打卡业务表 / behavior_meta 挖掘时长、步数、补卡等异常。"""
    m = models_for(user=user, db=db)
    alerts: list[dict] = []

    meta_row = db.query(m.BehaviorMeta).filter(m.BehaviorMeta.user_id == user_id).first()
    meta = dict(meta_row.meta_data) if meta_row and meta_row.meta_data else {}

    recheckin = int(meta.get("recheckinCount") or 0)
    if recheckin >= 3:
        alerts.append(
            _alert(
                "recheckin_high",
                "warn",
                "补打卡偏多",
                f"累计补打卡 {recheckin} 次，规律性打卡可能受到影响。",
                category="打卡行为",
                source="behavior_meta",
                metric=f"{recheckin} 次",
            )
        )

    # 整轮问卷/打卡耗时过长
    sessions = (
        db.query(m.CheckinSession)
        .filter(
            m.CheckinSession.user_id == user_id,
            m.CheckinSession.completed_at.isnot(None),
            m.CheckinSession.started_at.isnot(None),
        )
        .order_by(m.CheckinSession.id.desc())
        .limit(20)
        .all()
    )
    session_secs: list[int] = []
    incomplete = (
        db.query(m.CheckinSession.id)
        .filter(
            m.CheckinSession.user_id == user_id,
            m.CheckinSession.completed_at.is_(None),
        )
        .count()
    )
    for s in sessions:
        try:
            sec = int((s.completed_at - s.started_at).total_seconds())
        except Exception:
            continue
        if 0 < sec < 24 * 3600:
            session_secs.append(sec)
    if session_secs:
        avg_q = round(sum(session_secs) / len(session_secs))
        latest_q = session_secs[0]
        if latest_q >= 45 * 60:
            alerts.append(
                _alert(
                    "questionnaire_too_long",
                    "warn",
                    "最近问卷耗时过长",
                    f"最近一轮打卡耗时约 {latest_q // 60} 分钟，可能存在拖延或负担感。",
                    category="问卷打卡",
                    source="checkin_sessions",
                    metric=f"{latest_q} 秒",
                )
            )
        elif avg_q >= 30 * 60:
            alerts.append(
                _alert(
                    "questionnaire_avg_long",
                    "warn",
                    "平均问卷时长偏高",
                    f"近 {len(session_secs)} 轮平均耗时约 {avg_q // 60} 分钟，建议关注依从负担。",
                    category="问卷打卡",
                    source="checkin_sessions",
                    metric=f"均值 {avg_q} 秒",
                )
            )
    if incomplete >= 2:
        alerts.append(
            _alert(
                "checkin_incomplete",
                "warn",
                "存在未完成打卡轮次",
                f"有 {incomplete} 轮打卡未完成，中断模式可能提示负担或回避。",
                category="问卷打卡",
                source="checkin_sessions",
                metric=f"{incomplete} 轮",
            )
        )

    # 语音/视频时长过短（非跳过）
    voice = (
        db.query(m.EmaVoice)
        .filter(m.EmaVoice.user_id == user_id, m.EmaVoice.skip.is_(False))
        .order_by(m.EmaVoice.id.desc())
        .limit(10)
        .all()
    )
    video = (
        db.query(m.EmaVideo)
        .filter(m.EmaVideo.user_id == user_id, m.EmaVideo.skip.is_(False))
        .order_by(m.EmaVideo.id.desc())
        .limit(10)
        .all()
    )
    voice_secs = [int(r.duration_sec or 0) for r in voice if (r.duration_sec or 0) > 0]
    video_secs = [int(r.duration_sec or 0) for r in video if (r.duration_sec or 0) > 0]
    if voice_secs:
        avg_v = round(sum(voice_secs) / len(voice_secs))
        if voice_secs[0] < 8 or avg_v < 10:
            alerts.append(
                _alert(
                    "voice_too_short",
                    "warn",
                    "语音表达过短",
                    f"最近语音约 {voice_secs[0]} 秒（近均 {avg_v} 秒），表达内容偏少。",
                    category="语音采集",
                    source="ema_voice",
                    metric=f"{voice_secs[0]} 秒",
                )
            )
    if video_secs:
        avg_vid = round(sum(video_secs) / len(video_secs))
        if video_secs[0] < 5 or avg_vid < 8:
            alerts.append(
                _alert(
                    "video_too_short",
                    "warn",
                    "视频表达过短",
                    f"最近视频约 {video_secs[0]} 秒（近均 {avg_vid} 秒），可视信号可能不足。",
                    category="视频采集",
                    source="ema_video",
                    metric=f"{video_secs[0]} 秒",
                )
            )

    # 近 14 日均步数过低
    step_rows = (
        db.query(m.EmaStep.task_date, m.EmaStep.steps)
        .filter(m.EmaStep.user_id == user_id)
        .order_by(m.EmaStep.task_date.desc(), m.EmaStep.recorded_at.desc())
        .limit(40)
        .all()
    )
    by_day: dict[str, int] = {}
    for row in step_rows:
        if row.task_date not in by_day:
            by_day[row.task_date] = int(row.steps or 0)
    vals = list(by_day.values())[:14]
    if len(vals) >= 3:
        avg14 = round(sum(vals) / len(vals))
        if avg14 < 2500:
            alerts.append(
                _alert(
                    "steps_avg_low",
                    "warn",
                    "近两周平均步数偏低",
                    f"近 {len(vals)} 日平均步数约 {avg14} 步，活动水平持续偏低。",
                    category="步数活动",
                    source="ema_step",
                    metric=f"均值 {avg14} 步",
                )
            )

    # 最近视频跳过（与语音对称）
    latest_video_skip = (
        db.query(m.EmaVideo)
        .filter(m.EmaVideo.user_id == user_id, m.EmaVideo.skip.is_(True))
        .order_by(m.EmaVideo.id.desc())
        .first()
    )
    if latest_video_skip:
        alerts.append(
            _alert(
                "video_skipped_signal",
                "warn",
                "视频任务回避",
                f"近期视频采集被跳过（{latest_video_skip.task_date}），回避本身可能是状态信号。",
                category="视频采集",
                source="ema_video",
                metric=latest_video_skip.task_date,
            )
        )

    return alerts


def _mine_trend_alerts(db: Session, user_id: int, ema_trend: dict, *, user=None) -> list[dict]:
    """基于近期问卷走势与步数等原始表挖掘预警。"""
    alerts: list[dict] = []
    if ema_trend.get("dataDays", 0) >= 3:
        if ema_trend.get("moodSlope", 0) <= -1.0:
            alerts.append(
                _alert(
                    "trend_mood_decline",
                    "warn",
                    "心情持续走低",
                    "近一周心情评分呈明显下降趋势，建议留意情绪变化并保持规律打卡。",
                    category="问卷走势",
                    source="ema_questions",
                    metric=f"斜率 {ema_trend.get('moodSlope'):.2f}",
                )
            )
        if ema_trend.get("stressSlope", 0) >= 1.0:
            alerts.append(
                _alert(
                    "trend_stress_rise",
                    "warn",
                    "压力持续升高",
                    "近一周压力评分呈明显上升趋势，可尝试减压练习或寻求支持。",
                    category="问卷走势",
                    source="ema_questions",
                    metric=f"斜率 {ema_trend.get('stressSlope'):.2f}",
                )
            )
        if ema_trend.get("anxietySlope", 0) >= 1.0:
            alerts.append(
                _alert(
                    "trend_anxiety_rise",
                    "warn",
                    "焦虑持续升高",
                    "近一周焦虑评分呈明显上升趋势，建议关注情绪调节。",
                    category="问卷走势",
                    source="ema_questions",
                    metric=f"斜率 {ema_trend.get('anxietySlope'):.2f}",
                )
            )
        if ema_trend.get("sleepSlope", 0) <= -1.0:
            alerts.append(
                _alert(
                    "trend_sleep_decline",
                    "warn",
                    "睡眠质量持续下降",
                    "近一周睡眠评分呈下降趋势，睡眠不足可能放大压力与情绪波动。",
                    category="问卷走势",
                    source="ema_questions",
                    metric=f"斜率 {ema_trend.get('sleepSlope'):.2f}",
                )
            )

    EmaStep = models_for(user=user, db=db).EmaStep
    recent_steps = (
        db.query(EmaStep)
        .filter(EmaStep.user_id == user_id)
        .order_by(EmaStep.task_date.desc(), EmaStep.recorded_at.desc())
        .limit(7)
        .all()
    )
    if recent_steps:
        seen: set[str] = set()
        vals: list[int] = []
        for row in recent_steps:
            if row.task_date in seen:
                continue
            seen.add(row.task_date)
            vals.append(int(row.steps or 0))
        if vals:
            today_steps = vals[0]
            avg7 = sum(vals) / len(vals)
            if today_steps > 0 and today_steps < 2000:
                alerts.append(
                    _alert(
                        "steps_very_low",
                        "warn",
                        "今日步数过低",
                        f"今日步数仅 {today_steps} 步，活动量偏低可能与情绪低落相关。",
                        category="步数活动",
                        source="ema_step",
                        metric=f"{today_steps} 步",
                    )
                )
            elif avg7 > 0 and today_steps < avg7 * 0.4 and today_steps < 4000:
                alerts.append(
                    _alert(
                        "steps_sharp_drop",
                        "warn",
                        "步数较基线骤降",
                        f"今日步数（{today_steps}）显著低于近 7 日均值（约 {int(avg7)}），活动模式出现波动。",
                        category="步数活动",
                        source="ema_step",
                        metric=f"{today_steps} / 均 {int(avg7)}",
                    )
                )

    EmaDiary = models_for(user=user, db=db).EmaDiary
    diary = (
        db.query(EmaDiary)
        .filter(EmaDiary.user_id == user_id)
        .order_by(EmaDiary.id.desc())
        .first()
    )
    if diary:
        length = int(getattr(diary, "length", 0) or len(getattr(diary, "text", "") or ""))
        if 0 < length < 15:
            alerts.append(
                _alert(
                    "diary_too_short",
                    "warn",
                    "日记表达过短",
                    f"最近一篇日记仅 {length} 字，表达内容偏少，可关注表达意愿变化。",
                    category="日记采集",
                    source="ema_diary",
                    metric=f"{length} 字",
                )
            )

    return alerts


def _dedupe_alerts(alerts: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in alerts:
        normalized = _normalize_alert(item)
        aid = normalized.get("id") or ""
        if aid in seen:
            continue
        seen.add(aid)
        out.append(normalized)
    level_rank = {"danger": 0, "warn": 1, "info": 2}
    out.sort(key=lambda a: (level_rank.get(a.get("level") or "warn", 9), a.get("category") or ""))
    return out


def collect_anomaly_alerts(
    db: Session,
    user,
    *,
    answers: dict | None = None,
    missed_days: int | None = None,
    ema_trend: dict | None = None,
) -> list[dict]:
    """汇总个体异常预警（问卷/行为/特征表/走势/打卡统计）。"""
    if answers is None:
        latest_q = _latest_questionnaire(db, user.id, user=user)
        answers = _questionnaire_answers(latest_q)
    if missed_days is None:
        missed_days = _count_missed_days(db, user.id, user=user)
    if ema_trend is None:
        ema_trend = _recent_ema_trend(db, user.id, user=user)

    _, _, ema_alerts = _score_recent_ema(answers)
    for item in ema_alerts:
        item.setdefault("category", "当日问卷")
        item.setdefault("source", "ema_questions")
    _, behavior_alerts = _behavior_alerts(db, user.id, missed_days, user=user)
    for item in behavior_alerts:
        item.setdefault("category", "打卡行为")
        item.setdefault("source", "behavior / skip_events")
    feature_alerts = _mine_feature_alerts(db, user.id, user=user)
    trend_alerts = _mine_trend_alerts(db, user.id, ema_trend, user=user)
    stats_alerts = _mine_checkin_stats_alerts(db, user.id, user=user)
    return _dedupe_alerts(ema_alerts + behavior_alerts + feature_alerts + trend_alerts + stats_alerts)


def refresh_risk_alerts(db: Session, user, risk: dict[str, Any] | None) -> dict[str, Any] | None:
    """用最新挖掘结果刷新风险评估中的 alerts（供趋势页实时展示）。"""
    if not risk or not risk.get("hasAssessment"):
        return risk
    alerts = collect_anomaly_alerts(db, user)
    risk = dict(risk)
    risk["alerts"] = alerts
    risk["alertCount"] = len(alerts)
    risk["alertDangerCount"] = sum(1 for a in alerts if a.get("level") == "danger")
    risk["alertWarnCount"] = sum(1 for a in alerts if a.get("level") == "warn")
    return risk


def _resolve_level(total: int, critical: bool) -> str:
    """风险等级：0–4 低 / 5–9 中 / 10–15 高；critical 信号强制高风险。"""
    if critical or total >= 10:
        return "high"
    if total >= 5:
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
    anxiety_vals = [by_date[d].anxiety for d in recent_dates]
    sleep_vals = [by_date[d].sleep for d in recent_dates]
    return {
        "moodSlope": _compute_slope([float(v) for v in mood_vals]),
        "stressSlope": _compute_slope([float(v) for v in stress_vals]),
        "anxietySlope": _compute_slope([float(v) for v in anxiety_vals]),
        "sleepSlope": _compute_slope([float(v) for v in sleep_vals]),
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
            _alert(
                "missed_days",
                "danger" if missed_days >= 5 else "warn",
                "连续缺测",
                f"已连续 {missed_days} 天未完成 EMA 打卡，缺测模式可能提示状态变化。",
                category="打卡行为",
                source="ema_questions",
                metric=f"{missed_days} 天",
            )
        )
    voice_skips = db.query(SkipEvent).filter(SkipEvent.user_id == user_id, SkipEvent.media_type == "voice").count()
    video_skips = db.query(SkipEvent).filter(SkipEvent.user_id == user_id, SkipEvent.media_type == "video").count()
    if voice_skips >= 3 or video_skips >= 3:
        score += 1
        alerts.append(
            _alert(
                "task_skip",
                "warn",
                "任务跳过偏多",
                f"语音跳过 {voice_skips} 次，视频跳过 {video_skips} 次。",
                category="打卡行为",
                source="skip_events",
                metric=f"语音 {voice_skips} / 视频 {video_skips}",
            )
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
        "alertDangerCount": 0,
        "alertWarnCount": 0,
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
    e_score, ema_factors, _ = _score_recent_ema(answers)
    missed_days = _count_missed_days(db, user.id, user=user)
    behavior_score, _ = _behavior_alerts(db, user.id, missed_days, user=user)

    critical = profile.get("self_harm") == "是" or (answers and answers.get("negative") == "是")
    total = b_score + e_score + behavior_score
    level = _resolve_level(total, critical)
    meta = LEVEL_META[level]
    ema_trend = _recent_ema_trend(db, user.id, user=user)
    forecast = _build_forecast(total, critical, missed_days, ema_trend)
    all_alerts = collect_anomaly_alerts(
        db,
        user,
        answers=answers,
        missed_days=missed_days,
        ema_trend=ema_trend,
    )

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
        "alertDangerCount": sum(1 for a in all_alerts if a.get("level") == "danger"),
        "alertWarnCount": sum(1 for a in all_alerts if a.get("level") == "warn"),
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
        ("alerts", {
            "alerts": result["alerts"],
            "alertCount": result["alertCount"],
            "alertDangerCount": result.get("alertDangerCount") or 0,
            "alertWarnCount": result.get("alertWarnCount") or 0,
        }),
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
        "alertDangerCount": alerts_payload.get("alertDangerCount") or 0,
        "alertWarnCount": alerts_payload.get("alertWarnCount") or 0,
        "task_date": td,
        "session_id": sid,
    }
