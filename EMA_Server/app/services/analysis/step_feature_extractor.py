"""从 ema_step 提取微信运动步数特性并写入 step_features。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    BaselineProfile,
    EmaQuestion,
    EmaStep,
    QuestionsFeature,
    StepFeature,
)
from app.services.analysis.step_metrics import (
    activity_level_label,
    build_daily_step_map,
    compute_avg_last_n,
    compute_baseline_deviation,
    compute_fluctuation,
    compute_personal_baseline,
    compute_weekend_weekday_rhythm,
    count_consecutive_low_days,
    is_weekend,
    parse_task_date,
)
from app.services.datetime_fields import format_datetime

logger = logging.getLogger(__name__)


class StepFeatureExtractor:
    """
    微信运动步数特性提取器。

    强调相对个体基线的偏离，而非绝对步数阈值：
    1. 每日总步数  2. 近 7 天平均  3. 步数波动  4. 连续低步数天数
    5. 与个人基线差异  6. 周末/工作日节律差异

    可同时参考 ema_questions、questions_features、baseline 等同日/同用户上下文。
    """

    def __init__(
        self,
        db: Session,
        baseline_window_days: int | None = None,
        short_avg_days: int | None = None,
        low_ratio: float | None = None,
        rhythm_window_days: int | None = None,
    ) -> None:
        self.db = db
        settings = get_settings()
        self.baseline_window_days = (
            baseline_window_days if baseline_window_days is not None else settings.step_baseline_window_days
        )
        self.short_avg_days = short_avg_days if short_avg_days is not None else settings.step_short_avg_days
        self.low_ratio = low_ratio if low_ratio is not None else settings.step_low_ratio
        self.rhythm_window_days = (
            rhythm_window_days if rhythm_window_days is not None else settings.step_rhythm_window_days
        )

    # ------------------------------------------------------------------ public

    def process_step(self, record: EmaStep) -> StepFeature:
        features = self.extract_from_step(record)
        return self.save_features(record, features)

    def extract_from_step(self, record: EmaStep) -> dict[str, Any]:
        step_map = self._load_user_step_history(record.user_id, up_to_date=record.task_date)
        step_map[record.task_date] = max(step_map.get(record.task_date, 0), int(record.steps))
        today_steps = step_map[record.task_date]

        baseline = compute_personal_baseline(step_map, record.task_date, self.baseline_window_days)
        context = self._load_context(record)

        daily_total = {
            "steps": today_steps,
            "source": record.source,
            "activity_level": activity_level_label(today_steps, baseline),
            "is_weekend": is_weekend(parse_task_date(record.task_date)),
        }
        avg_7d = {
            "days": self.short_avg_days,
            "average": compute_avg_last_n(step_map, record.task_date, self.short_avg_days),
        }
        fluctuation = compute_fluctuation(step_map, record.task_date, window_days=14)
        consecutive_low = count_consecutive_low_days(
            step_map, record.task_date, baseline, self.low_ratio
        )
        baseline_dev = compute_baseline_deviation(today_steps, baseline)
        rhythm = compute_weekend_weekday_rhythm(step_map, record.task_date, self.rhythm_window_days)

        enrichment = self._build_context_enrichment(context, today_steps, baseline_dev, consecutive_low)
        composite = self._build_composite_signals(
            daily_total, avg_7d, baseline_dev, consecutive_low, fluctuation, rhythm, enrichment, context
        )

        return {
            "step_id": record.id,
            "task_date": record.task_date,
            "personal_baseline": round(baseline, 2) if baseline is not None else None,
            "baseline_window_days": self.baseline_window_days,
            "low_step_threshold": consecutive_low.get("threshold"),
            "daily_total": daily_total,
            "avg_last_n_days": avg_7d,
            "fluctuation": fluctuation,
            "consecutive_low_days": consecutive_low,
            "baseline_deviation": baseline_dev,
            "weekend_weekday_rhythm": rhythm,
            "context_enrichment": enrichment,
            "composite_signals": composite,
            "extracted_at": format_datetime(datetime.now()),
        }

    def save_features(self, record: EmaStep, features: dict[str, Any]) -> StepFeature:
        row = (
            self.db.query(StepFeature)
            .filter(
                StepFeature.user_id == record.user_id,
                StepFeature.task_date == record.task_date,
                StepFeature.session_id == record.session_id,
            )
            .first()
        )
        if row:
            row.features = features
            row.status = "done"
            row.submission_id = record.id
        else:
            row = StepFeature(
                user_id=record.user_id,
                task_date=record.task_date,
                session_id=record.session_id,
                submission_id=record.id,
                status="done",
                features=features,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def process_step_by_id(self, step_id: int) -> StepFeature | None:
        record = self.db.query(EmaStep).filter(EmaStep.id == step_id).first()
        if not record:
            return None
        return self.process_step(record)

    def process_pending_steps(self, user_id: int | None = None, limit: int = 100) -> int:
        q = self.db.query(EmaStep).order_by(EmaStep.id.desc())
        if user_id is not None:
            q = q.filter(EmaStep.user_id == user_id)
        count = 0
        for record in q.limit(limit * 3):
            if count >= limit:
                break
            exists = (
                self.db.query(StepFeature)
                .filter(
                    StepFeature.user_id == record.user_id,
                    StepFeature.task_date == record.task_date,
                    StepFeature.session_id == record.session_id,
                    StepFeature.status == "done",
                )
                .first()
            )
            if exists:
                continue
            try:
                self.process_step(record)
                count += 1
            except Exception:
                logger.exception("step feature extract failed step_id=%s", record.id)
        return count

    # ------------------------------------------------------------------ data

    def _load_user_step_history(self, user_id: int, up_to_date: str) -> dict[str, int]:
        records = (
            self.db.query(EmaStep)
            .filter(EmaStep.user_id == user_id, EmaStep.task_date <= up_to_date)
            .order_by(EmaStep.task_date.asc(), EmaStep.recorded_at.asc())
            .all()
        )
        return build_daily_step_map(records)

    def _load_context(self, record: EmaStep) -> dict[str, Any]:
        questionnaire = (
            self.db.query(EmaQuestion)
            .filter(
                EmaQuestion.user_id == record.user_id,
                EmaQuestion.task_date == record.task_date,
                EmaQuestion.session_id == record.session_id,
            )
            .first()
        )
        questions_feature = (
            self.db.query(QuestionsFeature)
            .filter(
                QuestionsFeature.user_id == record.user_id,
                QuestionsFeature.task_date == record.task_date,
                QuestionsFeature.session_id == record.session_id,
                QuestionsFeature.status == "done",
            )
            .first()
        )
        baseline = (
            self.db.query(BaselineProfile).filter(BaselineProfile.user_id == record.user_id).first()
        )
        return {
            "questionnaire": questionnaire,
            "questions_feature": questions_feature,
            "baseline": baseline,
        }

    def _build_context_enrichment(
        self,
        context: dict[str, Any],
        today_steps: int,
        baseline_dev: dict[str, Any],
        consecutive_low: dict[str, Any],
    ) -> dict[str, Any]:
        q = context.get("questionnaire")
        q_data = None
        if q:
            q_data = {
                "mood": q.mood,
                "fatigue": q.fatigue,
                "function": q.function,
                "stress": q.stress,
            }

        qf_summary = None
        qf = context.get("questions_feature")
        if qf and qf.features:
            comp = qf.features.get("composite_signals") or {}
            qf_summary = {
                "sustained_low_mood": comp.get("sustained_low_mood"),
                "rising_stress": comp.get("rising_stress"),
            }

        baseline_profile = context.get("baseline")
        exercise_context = None
        if baseline_profile:
            exercise_context = {
                "exercise_freq": baseline_profile.exercise_freq,
                "sleep_habit": baseline_profile.sleep_habit,
            }

        cross_modal = self._steps_questionnaire_consistency(q, baseline_dev, consecutive_low)

        return {
            "questionnaire": q_data,
            "questions_feature": qf_summary,
            "baseline_profile": exercise_context,
            "steps_questionnaire_consistency": cross_modal,
        }

    @staticmethod
    def _steps_questionnaire_consistency(
        questionnaire: EmaQuestion | None,
        baseline_dev: dict[str, Any],
        consecutive_low: dict[str, Any],
    ) -> float | None:
        if not questionnaire:
            return None
        low_activity = baseline_dev.get("label") in ("sharp_drop", "below_baseline") or (
            consecutive_low.get("count", 0) >= 2
        )
        low_energy = questionnaire.fatigue >= 7 or questionnaire.mood <= 4
        high_function_impact = questionnaire.function >= 7
        expected_low = low_energy or high_function_impact
        if low_activity and expected_low:
            return 0.9
        if low_activity != expected_low:
            return 0.35
        return 0.75

    def _build_composite_signals(
        self,
        daily_total: dict[str, Any],
        avg_7d: dict[str, Any],
        baseline_dev: dict[str, Any],
        consecutive_low: dict[str, Any],
        fluctuation: dict[str, Any],
        rhythm: dict[str, Any],
        enrichment: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        reasons: list[str] = []
        sharp_drop = baseline_dev.get("label") == "sharp_drop"
        below = baseline_dev.get("label") in ("sharp_drop", "below_baseline")
        low_streak = consecutive_low.get("count", 0) >= 3
        irregular = fluctuation.get("label") == "irregular"
        rhythm_shift = rhythm.get("label") in ("weekend_less_active", "weekend_more_active")

        if sharp_drop:
            reasons.append("步数相对个人基线大幅下降")
        if low_streak:
            reasons.append(f"连续 {consecutive_low['count']} 天低于个体低步数阈值")
        if irregular:
            reasons.append("近期步数波动较大，生活规律性偏低")

        q = context.get("questionnaire")
        if q and below and (q.fatigue >= 7 or q.mood <= 4):
            reasons.append("低步数与问卷疲劳/低情绪一致")
        if q and below and q.mood >= 7:
            reasons.append("问卷情绪较好但步数低于基线，建议关注活动回避")

        consistency = enrichment.get("steps_questionnaire_consistency")
        if consistency is not None and consistency < 0.4:
            reasons.append("步数变化与问卷状态不一致")

        qf = context.get("questions_feature")
        if qf and qf.features:
            comp = qf.features.get("composite_signals") or {}
            if comp.get("sustained_low_mood") and below:
                reasons.append("问卷 EMA 持续低情绪与步数下降同步")

        if rhythm_shift and rhythm.get("label") == "weekend_less_active":
            reasons.append("周末步数明显低于工作日，节律发生变化")

        activity_decline = bool(sharp_drop or low_streak)
        elevated = bool(activity_decline or (below and len(reasons) >= 2))

        return {
            "elevated_inactivity_risk": elevated,
            "activity_decline": activity_decline,
            "sharp_drop_from_baseline": sharp_drop,
            "consecutive_low_days": consecutive_low.get("count", 0),
            "irregular_pattern": irregular,
            "rhythm_change": rhythm_shift,
            "reasons": reasons,
        }
