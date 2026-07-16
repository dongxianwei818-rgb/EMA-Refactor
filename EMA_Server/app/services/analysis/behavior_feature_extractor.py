"""从 behavior_logs / behavior_meta 提取小程序使用行为特性至 behavior_features。"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    BaselineProfile,
    BehaviorFeature,
    BehaviorLog,
    BehaviorMeta,
    CheckinSession,
    EmaDiary,
    EmaQuestion,
    EmaVideo,
    EmaVoice,
    QuestionsFeature,
    SkipEvent,
    StepFeature,
)
from app.services.analysis.behavior_metrics import (
    analyze_checkin_timing,
    analyze_compliance,
    analyze_content_expression,
    analyze_missingness_pattern,
    analyze_open_patterns,
    analyze_skip_rates,
    analyze_task_durations,
    count_consecutive_missed_days,
)
from app.services.datetime_fields import format_datetime

logger = logging.getLogger(__name__)


class BehaviorFeatureExtractor:
    """
    小程序使用行为特性提取器。

    从 behavior_logs + behavior_meta 提取：
    1. 打卡时间/昼夜节律  2. 按时完成/依从性  3. 连续缺测
    4. 文本字数变化  5. 语音时长变化  6. 视频跳过率
    7. 打开次数  8. 任务耗时

    缺测模式本身作为心理信号；可结合 ema_*、questions_features 等提高精度。
    """

    def __init__(
        self,
        db: Session,
        on_time_minutes: int | None = None,
        late_hour_start: int | None = None,
        late_hour_end: int | None = None,
    ) -> None:
        self.db = db
        settings = get_settings()
        self.on_time_minutes = (
            on_time_minutes if on_time_minutes is not None else settings.behavior_on_time_minutes
        )
        self.late_hour_start = late_hour_start if late_hour_start is not None else settings.behavior_late_hour_start
        self.late_hour_end = late_hour_end if late_hour_end is not None else settings.behavior_late_hour_end

    # ------------------------------------------------------------------ public

    def process_session(self, user_id: int, task_date: str, session_id: int = 1) -> BehaviorFeature:
        features = self.extract_for_session(user_id, task_date, session_id)
        return self.save_features(user_id, task_date, session_id, features)

    def extract_for_session(self, user_id: int, task_date: str, session_id: int = 1) -> dict[str, Any]:
        meta_row = self.db.query(BehaviorMeta).filter(BehaviorMeta.user_id == user_id).first()
        meta = dict(meta_row.meta_data) if meta_row and meta_row.meta_data else {}

        logs = self._logs_for_date(user_id, task_date)
        log_hours = [int(l.hour) for l in logs if l.hour is not None]
        log_durations = self._task_durations_from_logs(logs)

        checkin = (
            self.db.query(CheckinSession)
            .filter(
                CheckinSession.user_id == user_id,
                CheckinSession.task_date == task_date,
                CheckinSession.session_id == session_id,
            )
            .first()
        )

        context = self._load_context(user_id, task_date, session_id)
        missed = count_consecutive_missed_days(
            lambda d: self._has_questionnaire(user_id, d),
            parse_task_date(task_date),
        )

        checkin_timing = analyze_checkin_timing(
            meta, log_hours, late_start=self.late_hour_start, late_end=self.late_hour_end
        )
        compliance = analyze_compliance(
            checkin.started_at if checkin else None,
            checkin.completed_at if checkin else None,
            on_time_minutes=self.on_time_minutes,
        )
        expression = analyze_content_expression(meta)
        skip_rates = analyze_skip_rates(
            meta,
            self._skip_count(user_id, "voice"),
            self._skip_count(user_id, "video"),
            self._ema_media_skip_count(user_id, task_date, session_id, EmaVoice),
            self._ema_media_skip_count(user_id, task_date, session_id, EmaVideo),
        )
        open_patterns = analyze_open_patterns(meta, len(logs))
        task_duration = analyze_task_durations(meta, log_durations)
        missingness = analyze_missingness_pattern(
            task_date,
            has_questionnaire=context["has_questionnaire"],
            has_diary=context["has_diary"],
            has_voice=context["has_voice"],
            has_video=context["has_video"],
            voice_skipped=context["voice_skipped"],
            video_skipped=context["video_skipped"],
            consecutive_missed=missed["consecutive_days"],
        )

        enrichment = self._build_context_enrichment(context, missingness, skip_rates)
        composite = self._build_composite_signals(
            checkin_timing,
            compliance,
            missed,
            expression,
            skip_rates,
            open_patterns,
            task_duration,
            missingness,
            enrichment,
            context,
        )

        return {
            "user_id": user_id,
            "task_date": task_date,
            "session_id": session_id,
            "meta_snapshot": {
                "open_count": meta.get("openCount"),
                "recheckin_count": meta.get("recheckinCount"),
                "diary_samples": len(meta.get("diaryWordCounts") or []),
                "voice_samples": len(meta.get("voiceDurations") or []),
                "video_samples": len(meta.get("videoDurations") or []),
            },
            "logs_on_date": len(logs),
            "checkin_timing": checkin_timing,
            "compliance": compliance,
            "consecutive_missed_days": missed,
            "content_expression": expression,
            "skip_rates": skip_rates,
            "open_patterns": open_patterns,
            "task_duration": task_duration,
            "missingness_pattern": missingness,
            "context_enrichment": enrichment,
            "composite_signals": composite,
            "extracted_at": format_datetime(datetime.now()),
        }

    def save_features(
        self,
        user_id: int,
        task_date: str,
        session_id: int,
        features: dict[str, Any],
    ) -> BehaviorFeature:
        now = datetime.now()
        row = (
            self.db.query(BehaviorFeature)
            .filter(
                BehaviorFeature.user_id == user_id,
                BehaviorFeature.task_date == task_date,
                BehaviorFeature.session_id == session_id,
            )
            .first()
        )
        if row:
            row.features = features
            row.status = "done"
            row.computed_at = now
        else:
            row = BehaviorFeature(
                user_id=user_id,
                task_date=task_date,
                session_id=session_id,
                status="done",
                features=features,
                computed_at=now,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def process_pending_sessions(self, user_id: int | None = None, limit: int = 100) -> int:
        q = (
            self.db.query(CheckinSession)
            .filter(CheckinSession.completed_at.isnot(None))
            .order_by(CheckinSession.id.desc())
        )
        if user_id is not None:
            q = q.filter(CheckinSession.user_id == user_id)
        count = 0
        for session in q.limit(limit * 3):
            if count >= limit:
                break
            exists = (
                self.db.query(BehaviorFeature)
                .filter(
                    BehaviorFeature.user_id == session.user_id,
                    BehaviorFeature.task_date == session.task_date,
                    BehaviorFeature.session_id == session.session_id,
                    BehaviorFeature.status == "done",
                )
                .first()
            )
            if exists:
                continue
            try:
                self.process_session(session.user_id, session.task_date, session.session_id)
                count += 1
            except Exception:
                logger.exception(
                    "behavior feature extract failed user=%s date=%s",
                    session.user_id,
                    session.task_date,
                )
        return count

    # ------------------------------------------------------------------ helpers

    def _logs_for_date(self, user_id: int, task_date: str) -> list[BehaviorLog]:
        start = datetime.combine(parse_task_date(task_date), datetime.min.time())
        end = start + timedelta(days=1)
        return (
            self.db.query(BehaviorLog)
            .filter(
                BehaviorLog.user_id == user_id,
                BehaviorLog.client_at >= start,
                BehaviorLog.client_at < end,
            )
            .all()
        )

    @staticmethod
    def _task_durations_from_logs(logs: list[BehaviorLog]) -> list[int]:
        durations: list[int] = []
        for log in logs:
            if log.action != "task_duration":
                continue
            extra = log.extra or {}
            if extra.get("ms") is not None:
                durations.append(int(extra["ms"]))
        return durations

    def _has_questionnaire(self, user_id: int, task_date: str) -> bool:
        return (
            self.db.query(EmaQuestion.id)
            .filter(EmaQuestion.user_id == user_id, EmaQuestion.task_date == task_date)
            .first()
            is not None
        )

    def _skip_count(self, user_id: int, media_type: str) -> int:
        return (
            self.db.query(SkipEvent)
            .filter(SkipEvent.user_id == user_id, SkipEvent.media_type == media_type)
            .count()
        )

    def _ema_media_skip_count(self, user_id: int, task_date: str, session_id: int, model) -> int:
        row = (
            self.db.query(model)
            .filter(
                model.user_id == user_id,
                model.task_date == task_date,
                model.session_id == session_id,
                model.skip.is_(True),
            )
            .first()
        )
        return 1 if row else 0

    def _load_context(self, user_id: int, task_date: str, session_id: int) -> dict[str, Any]:
        q = (
            self.db.query(EmaQuestion)
            .filter(
                EmaQuestion.user_id == user_id,
                EmaQuestion.task_date == task_date,
                EmaQuestion.session_id == session_id,
            )
            .first()
        )
        diary = (
            self.db.query(EmaDiary)
            .filter(
                EmaDiary.user_id == user_id,
                EmaDiary.task_date == task_date,
                EmaDiary.session_id == session_id,
            )
            .first()
        )
        voice = (
            self.db.query(EmaVoice)
            .filter(
                EmaVoice.user_id == user_id,
                EmaVoice.task_date == task_date,
                EmaVoice.session_id == session_id,
            )
            .first()
        )
        video = (
            self.db.query(EmaVideo)
            .filter(
                EmaVideo.user_id == user_id,
                EmaVideo.task_date == task_date,
                EmaVideo.session_id == session_id,
            )
            .first()
        )
        questions_feature = (
            self.db.query(QuestionsFeature)
            .filter(
                QuestionsFeature.user_id == user_id,
                QuestionsFeature.task_date == task_date,
                QuestionsFeature.session_id == session_id,
                QuestionsFeature.status == "done",
            )
            .first()
        )
        step_feature = (
            self.db.query(StepFeature)
            .filter(
                StepFeature.user_id == user_id,
                StepFeature.task_date == task_date,
                StepFeature.session_id == session_id,
                StepFeature.status == "done",
            )
            .first()
        )
        baseline = self.db.query(BaselineProfile).filter(BaselineProfile.user_id == user_id).first()

        return {
            "questionnaire": q,
            "has_questionnaire": q is not None,
            "has_diary": diary is not None,
            "has_voice": voice is not None and not (voice.skip if voice else True),
            "has_video": video is not None and not (video.skip if video else True),
            "voice_skipped": voice.skip if voice else False,
            "video_skipped": video.skip if video else False,
            "questions_feature": questions_feature,
            "step_feature": step_feature,
            "baseline": baseline,
        }

    def _build_context_enrichment(
        self,
        context: dict[str, Any],
        missingness: dict[str, Any],
        skip_rates: dict[str, Any],
    ) -> dict[str, Any]:
        q = context.get("questionnaire")
        q_data = None
        if q:
            q_data = {"mood": q.mood, "fatigue": q.fatigue, "function": q.function}

        qf_summary = None
        qf = context.get("questions_feature")
        if qf and qf.features:
            comp = qf.features.get("composite_signals") or {}
            qf_summary = {
                "elevated_distress": comp.get("elevated_distress"),
                "sustained_low_mood": comp.get("sustained_low_mood"),
            }

        step_summary = None
        sf = context.get("step_feature")
        if sf and sf.features:
            comp = sf.features.get("composite_signals") or {}
            step_summary = {"activity_decline": comp.get("activity_decline")}

        cross = self._behavior_multimodal_consistency(missingness, skip_rates, q, qf, sf)

        return {
            "questionnaire": q_data,
            "questions_feature": qf_summary,
            "step_feature": step_summary,
            "multimodal_consistency": cross,
        }

    @staticmethod
    def _behavior_multimodal_consistency(
        missingness: dict[str, Any],
        skip_rates: dict[str, Any],
        questionnaire: EmaQuestion | None,
        questions_feature: QuestionsFeature | None,
        step_feature: StepFeature | None,
    ) -> float | None:
        if not questionnaire and missingness.get("consecutive_missed_days", 0) < 2:
            return None
        distress = 0.0
        if questionnaire:
            distress += ((10 - questionnaire.mood) / 10.0 + questionnaire.fatigue / 10.0) / 2.0
        if questions_feature and questions_feature.features:
            if (questions_feature.features.get("composite_signals") or {}).get("elevated_distress"):
                distress = max(distress, 0.6)
        if step_feature and step_feature.features:
            if (step_feature.features.get("composite_signals") or {}).get("activity_decline"):
                distress = max(distress, 0.5)

        avoidance = missingness.get("missingness_score") or 0.0
        if skip_rates.get("elevated_avoidance"):
            avoidance = max(avoidance, 0.6)

        if distress >= 0.5 and avoidance >= 0.4:
            return 0.85
        if abs(distress - avoidance) < 0.25:
            return 0.75
        if distress >= 0.5 and avoidance < 0.2:
            return 0.35
        return 0.55

    def _build_composite_signals(
        self,
        checkin_timing: dict[str, Any],
        compliance: dict[str, Any],
        missed: dict[str, Any],
        expression: dict[str, Any],
        skip_rates: dict[str, Any],
        open_patterns: dict[str, Any],
        task_duration: dict[str, Any],
        missingness: dict[str, Any],
        enrichment: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        reasons: list[str] = []

        if checkin_timing.get("circadian_disruption"):
            reasons.append("打卡时间分散或偏晚，可能存在昼夜节律紊乱")
        if compliance.get("label") == "prolonged":
            reasons.append("完成任务耗时过长，可能存在拖延或负担感")
        elif compliance.get("label") == "delayed":
            reasons.append("未按时完成打卡，依从性下降")

        if missed.get("elevated"):
            reasons.append(f"连续 {missed['consecutive_days']} 天缺测，缺测模式值得关注")

        diary_trend = expression.get("diary_word_count") or {}
        voice_trend = expression.get("voice_duration_sec") or {}
        if diary_trend.get("label") == "declining":
            reasons.append("日记字数呈下降趋势，表达意愿可能减弱")
        if voice_trend.get("label") == "declining":
            reasons.append("语音时长呈下降趋势，表达活跃度可能降低")

        if skip_rates.get("elevated_avoidance"):
            reasons.append("视频/语音跳过率偏高，可能存在回避或隐私顾虑")

        if open_patterns.get("label") == "high_engagement" and missed.get("consecutive_days", 0) >= 2:
            reasons.append("打开次数高但持续缺测，可能存在矛盾性关注/回避")
        if open_patterns.get("label") == "low_engagement" and missed.get("consecutive_days", 0) >= 2:
            reasons.append("打开次数低且连续缺测，动力/参与可能下降")

        if task_duration.get("label") == "hesitant":
            reasons.append("近期任务耗时增加，可能存在迟疑或负担感")

        if missingness.get("label") == "elevated":
            reasons.append("缺测/回避模式得分偏高（缺测本身即为信号）")

        q = context.get("questionnaire")
        if q and q.mood <= 4 and missed.get("consecutive_days", 0) >= 2:
            reasons.append("低情绪与连续缺测同步")

        consistency = enrichment.get("multimodal_consistency")
        if consistency is not None and consistency >= 0.8:
            reasons.append("行为回避与问卷/步数 distress 信号多模态一致")

        baseline = context.get("baseline")
        if baseline and baseline.self_harm in ("是", "有") and missingness.get("partial_media_avoidance"):
            reasons.append("基线自伤风险与媒体任务回避同时出现")

        elevated = bool(
            missed.get("elevated")
            or missingness.get("label") == "elevated"
            or skip_rates.get("elevated_avoidance")
            or (checkin_timing.get("circadian_disruption") and missed.get("consecutive_days", 0) >= 1)
            or len(reasons) >= 3
        )

        return {
            "elevated_engagement_risk": elevated,
            "avoidance_pattern": skip_rates.get("elevated_avoidance") or missingness.get("partial_media_avoidance"),
            "missingness_signal": missingness.get("label") == "elevated",
            "low_adherence": compliance.get("label") in ("delayed", "prolonged", "incomplete"),
            "reasons": reasons,
        }


def parse_task_date(value: str) -> date:
    return date.fromisoformat(value)
