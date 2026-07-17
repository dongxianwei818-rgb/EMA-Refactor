"""从 ema_questions 提取 EMA 趋势特性并写入 questions_feature。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import models_for
from app.services.analysis.questions_metrics import (
    METRIC_LABELS,
    NEGATIVE_THOUGHT_MAP,
    SCALE_FIELDS,
    SCALE_METRICS,
)
from app.services.datetime_fields import format_datetime

logger = logging.getLogger(__name__)


def compute_ema_series(values: list[float], alpha: float) -> list[float]:
    """对观测序列计算 EMA；首个观测作为初始值。"""
    if not values:
        return []
    ema_values = [values[0]]
    for value in values[1:]:
        ema_values.append(alpha * value + (1.0 - alpha) * ema_values[-1])
    return ema_values


def _distress_score(field: str, value: float) -> float:
    """将 0-10 分转为 distress 方向（越高越 distress）。"""
    for name, _, higher_is_distress in SCALE_METRICS:
        if name == field:
            return value if higher_is_distress else (10.0 - value)
    return value


class QuestionsFeatureExtractor:
    """
    EMA 问卷趋势特性提取器。

    对 7 项 0-10 分量表分别计算指数移动平均（EMA），得到平滑趋势曲线；
    可同时参考 baseline、同轮 text_features / ema_diary 等上下文提高判定精度。
    """

    def __init__(self, db: Session, ema_span: int | None = None, history_days: int | None = None) -> None:
        self.db = db
        settings = get_settings()
        self.ema_span = ema_span if ema_span is not None else settings.questions_ema_span
        self.history_days = history_days if history_days is not None else settings.questions_ema_history_days
        self.alpha = 2.0 / (self.ema_span + 1.0)

    @property
    def m(self):
        return models_for(db=self.db)

    # ------------------------------------------------------------------ public

    def process_questionnaire(self, record) -> Any:
        features = self.extract_from_questionnaire(record)
        return self.save_features(record, features)

    def extract_from_questionnaire(self, record) -> dict[str, Any]:
        daily_series = self._build_daily_series(record.user_id, up_to_date=record.task_date)
        target_idx = self._index_of_date(daily_series, record.task_date)
        if target_idx < 0:
            target_idx = len(daily_series) - 1

        raw = self._raw_from_record(record)
        ema_block = self._compute_ema_block(daily_series, target_idx)
        trend_curves = self._build_trend_curves(daily_series, target_idx)
        negative_block = self._analyze_negative_thoughts(record, daily_series, target_idx)
        context = self._load_context(record)
        composite = self._build_composite_signals(ema_block, trend_curves, negative_block, context)

        return {
            "question_id": record.id,
            "raw": raw,
            "ema": ema_block,
            "trend_curves": trend_curves,
            "negative_thoughts": negative_block,
            "context_enrichment": context,
            "composite_signals": composite,
            "extracted_at": format_datetime(datetime.now()),
        }

    def save_features(self, record, features: dict[str, Any]) -> Any:
        QuestionsFeature = self.m.QuestionsFeature
        row = (
            self.db.query(QuestionsFeature)
            .filter(
                QuestionsFeature.user_id == record.user_id,
                QuestionsFeature.task_date == record.task_date,
                QuestionsFeature.session_id == record.session_id,
            )
            .first()
        )
        if row:
            row.features = features
            row.status = "done"
            row.submission_id = record.id
        else:
            row = QuestionsFeature(
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

    def process_questionnaire_by_id(self, question_id: int) -> Any | None:
        EmaQuestion = self.m.EmaQuestion
        record = self.db.query(EmaQuestion).filter(EmaQuestion.id == question_id).first()
        if not record:
            return None
        return self.process_questionnaire(record)

    def process_pending_questionnaires(self, user_id: int | None = None, limit: int = 100) -> int:
        EmaQuestion = self.m.EmaQuestion
        QuestionsFeature = self.m.QuestionsFeature
        q = self.db.query(EmaQuestion).order_by(EmaQuestion.id.desc())
        if user_id is not None:
            q = q.filter(EmaQuestion.user_id == user_id)
        count = 0
        for record in q.limit(limit * 3):
            if count >= limit:
                break
            exists = (
                self.db.query(QuestionsFeature)
                .filter(
                    QuestionsFeature.user_id == record.user_id,
                    QuestionsFeature.task_date == record.task_date,
                    QuestionsFeature.session_id == record.session_id,
                    QuestionsFeature.status == "done",
                )
                .first()
            )
            if exists:
                continue
            try:
                self.process_questionnaire(record)
                count += 1
            except Exception:
                logger.exception("questions feature extract failed question_id=%s", record.id)
        return count

    def recompute_user_from_date(self, user_id: int, from_date: str | None = None) -> int:
        """从指定日期起按时间顺序重算该用户全部 questions_feature（用于补历史）。"""
        EmaQuestion = self.m.EmaQuestion
        q = self.db.query(EmaQuestion).filter(EmaQuestion.user_id == user_id)
        if from_date:
            q = q.filter(EmaQuestion.task_date >= from_date)
        records = q.order_by(EmaQuestion.task_date.asc(), EmaQuestion.answered_at.asc()).all()
        count = 0
        for record in records:
            try:
                self.process_questionnaire(record)
                count += 1
            except Exception:
                logger.exception("questions feature recompute failed question_id=%s", record.id)
        return count

    # ------------------------------------------------------------------ series

    def _build_daily_series(self, user_id: int, up_to_date: str | None = None) -> list[dict[str, Any]]:
        """按 task_date 聚合为日序列；同日多条取各量表均值。"""
        EmaQuestion = self.m.EmaQuestion
        q = self.db.query(EmaQuestion).filter(EmaQuestion.user_id == user_id)
        if up_to_date:
            q = q.filter(EmaQuestion.task_date <= up_to_date)
        records = q.order_by(EmaQuestion.task_date.asc(), EmaQuestion.answered_at.asc()).all()

        by_date: dict[str, list[Any]] = {}
        for rec in records:
            by_date.setdefault(rec.task_date, []).append(rec)

        series: list[dict[str, Any]] = []
        for task_date in sorted(by_date.keys()):
            day_records = by_date[task_date]
            scales = {}
            for field in SCALE_FIELDS:
                scales[field] = round(
                    sum(getattr(r, field) for r in day_records) / len(day_records),
                    4,
                )
            neg_values = [NEGATIVE_THOUGHT_MAP.get(r.negative, 0.5) for r in day_records]
            negative_score = round(sum(neg_values) / len(neg_values), 4)
            series.append(
                {
                    "task_date": task_date,
                    "session_count": len(day_records),
                    "scales": scales,
                    "negative_score": negative_score,
                    "negative_raw": day_records[-1].negative,
                }
            )
        return series

    @staticmethod
    def _index_of_date(daily_series: list[dict[str, Any]], task_date: str) -> int:
        for i, point in enumerate(daily_series):
            if point["task_date"] == task_date:
                return i
        return -1

    @staticmethod
    def _raw_from_record(record) -> dict[str, Any]:
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

    def _compute_ema_block(self, daily_series: list[dict[str, Any]], target_idx: int) -> dict[str, Any]:
        block: dict[str, Any] = {
            "span": self.ema_span,
            "alpha": round(self.alpha, 6),
            "observation_count": len(daily_series),
            "metrics": {},
        }
        if not daily_series or target_idx < 0:
            return block

        target_scales = daily_series[target_idx]["scales"]
        for field in SCALE_FIELDS:
            values = [point["scales"][field] for point in daily_series]
            ema_values = compute_ema_series(values, self.alpha)
            current_ema = ema_values[target_idx]
            raw_today = target_scales[field]
            prev_ema = ema_values[target_idx - 1] if target_idx > 0 else None
            delta = round(current_ema - raw_today, 4)
            trend = self._trend_direction(current_ema, prev_ema, field)
            block["metrics"][field] = {
                "label": METRIC_LABELS[field],
                "raw": raw_today,
                "ema": round(current_ema, 4),
                "delta_from_raw": delta,
                "trend": trend,
                "distress_ema": round(_distress_score(field, current_ema), 4),
            }
        return block

    def _build_trend_curves(
        self,
        daily_series: list[dict[str, Any]],
        target_idx: int,
    ) -> dict[str, list[dict[str, Any]]]:
        """为每个量表返回最近 N 天的 raw + ema 曲线点，供模型与可视化使用。"""
        if not daily_series:
            return {field: [] for field in SCALE_FIELDS}

        start = max(0, target_idx - self.history_days + 1)
        window = daily_series[start : target_idx + 1]
        curves: dict[str, list[dict[str, Any]]] = {}

        prefix_len = start
        for field in SCALE_FIELDS:
            full_values = [point["scales"][field] for point in daily_series]
            full_ema = compute_ema_series(full_values, self.alpha)
            points = []
            for i, point in enumerate(window):
                idx = prefix_len + i
                points.append(
                    {
                        "task_date": point["task_date"],
                        "raw": point["scales"][field],
                        "ema": round(full_ema[idx], 4),
                    }
                )
            curves[field] = points
        return curves

    def _analyze_negative_thoughts(
        self,
        record,
        daily_series: list[dict[str, Any]],
        target_idx: int,
    ) -> dict[str, Any]:
        window = daily_series[max(0, target_idx - 6) : target_idx + 1]
        yes_count = sum(1 for p in window if p.get("negative_raw") == "是")
        recent_scores = [p["negative_score"] for p in window]
        ema_neg = compute_ema_series(recent_scores, self.alpha)[-1] if recent_scores else 0.0

        consecutive_yes = 0
        for point in reversed(window):
            if point.get("negative_raw") == "是":
                consecutive_yes += 1
            else:
                break

        return {
            "today": record.negative,
            "score_today": NEGATIVE_THOUGHT_MAP.get(record.negative, 0.5),
            "recent_yes_count_7d": yes_count,
            "consecutive_yes_days": consecutive_yes,
            "negative_ema": round(ema_neg, 4),
        }

    # ------------------------------------------------------------------ context

    def _load_context(self, record) -> dict[str, Any]:
        BaselineProfile = self.m.BaselineProfile
        TextFeature = self.m.TextFeature
        EmaDiary = self.m.EmaDiary
        baseline = (
            self.db.query(BaselineProfile).filter(BaselineProfile.user_id == record.user_id).first()
        )
        text_feature = (
            self.db.query(TextFeature)
            .filter(
                TextFeature.user_id == record.user_id,
                TextFeature.task_date == record.task_date,
                TextFeature.session_id == record.session_id,
                TextFeature.status == "done",
            )
            .first()
        )
        diary = (
            self.db.query(EmaDiary)
            .filter(
                EmaDiary.user_id == record.user_id,
                EmaDiary.task_date == record.task_date,
                EmaDiary.session_id == record.session_id,
            )
            .first()
        )

        baseline_data = None
        if baseline:
            baseline_data = {
                "phq9_1": baseline.phq9_1,
                "phq9_2": baseline.phq9_2,
                "gad7_1": baseline.gad7_1,
                "gad7_2": baseline.gad7_2,
                "self_harm": baseline.self_harm,
                "course_pressure": baseline.course_pressure,
                "exam_pressure": baseline.exam_pressure,
            }

        text_summary = None
        if text_feature and text_feature.features:
            tf = text_feature.features
            text_summary = {
                "emotional_polarity": (tf.get("emotional_words") or {}).get("polarity"),
                "hopelessness_score": (tf.get("hopelessness") or {}).get("score"),
                "composite_elevated": (tf.get("composite_risk_signals") or {}).get("elevated_distress"),
            }

        diary_summary = None
        if diary:
            diary_summary = {"length": diary.length, "has_text": bool(diary.text)}

        consistency = self._questionnaire_text_consistency(record, text_feature)

        return {
            "baseline": baseline_data,
            "text_features": text_summary,
            "diary": diary_summary,
            "questionnaire_text_consistency": consistency,
        }

    def _questionnaire_text_consistency(
        self,
        record,
        text_feature: Any | None,
    ) -> float | None:
        if not text_feature or not text_feature.features:
            return None
        emotional = text_feature.features.get("emotional_words") or {}
        hopeless = text_feature.features.get("hopelessness") or {}
        distress_from_q = (
            (10 - record.mood) / 10.0 + record.stress / 10.0 + record.anxiety / 10.0
        ) / 3.0
        distress_from_text = max(-emotional.get("score", 0), 0) * 0.5 + hopeless.get("score", 0) * 0.5
        return round(max(0.0, 1.0 - abs(distress_from_q - distress_from_text)), 4)

    # ------------------------------------------------------------------ signals

    def _personalized_mood_threshold(self, context: dict[str, Any]) -> float:
        baseline = context.get("baseline") or {}
        low_baseline = baseline.get("phq9_1") in ("经常", "几乎每天") or baseline.get("phq9_2") in (
            "经常",
            "几乎每天",
        )
        return 3.5 if low_baseline else 4.0

    def _build_composite_signals(
        self,
        ema_block: dict[str, Any],
        trend_curves: dict[str, list[dict[str, Any]]],
        negative_block: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        metrics = ema_block.get("metrics") or {}
        mood_threshold = self._personalized_mood_threshold(context)
        reasons: list[str] = []

        mood_metric = metrics.get("mood") or {}
        mood_ema = mood_metric.get("ema")
        sustained_low_mood = self._sustained_low(mood_ema, trend_curves.get("mood", []), mood_threshold)

        stress_metric = metrics.get("stress") or {}
        stress_ema = stress_metric.get("ema")
        rising_stress = self._is_rising(trend_curves.get("stress", []), min_delta=1.0)

        anxiety_metric = metrics.get("anxiety") or {}
        anxiety_ema = anxiety_metric.get("ema")

        multidimensional_distress = False
        if mood_ema is not None and mood_ema <= mood_threshold:
            if (stress_ema or 0) >= 6.0 or (anxiety_ema or 0) >= 6.0:
                multidimensional_distress = True
                reasons.append("情绪与压力/焦虑 EMA 同时偏高")

        if sustained_low_mood:
            reasons.append("心情 EMA 持续偏低")
        if rising_stress:
            reasons.append("压力 EMA 呈上升趋势")
        if negative_block.get("recent_yes_count_7d", 0) >= 2:
            reasons.append("近 7 日多次报告消极想法")
        if negative_block.get("consecutive_yes_days", 0) >= 2:
            reasons.append("连续多日报告消极想法")

        consistency = context.get("questionnaire_text_consistency")
        if consistency is not None and consistency < 0.4:
            reasons.append("问卷与日记文本情绪不一致，建议复核")

        elevated = bool(
            sustained_low_mood
            or rising_stress
            or multidimensional_distress
            or negative_block.get("consecutive_yes_days", 0) >= 2
        )

        return {
            "elevated_distress": elevated,
            "sustained_low_mood": sustained_low_mood,
            "rising_stress": rising_stress,
            "multidimensional_distress": multidimensional_distress,
            "mood_ema_threshold_used": mood_threshold,
            "reasons": reasons,
        }

    @staticmethod
    def _trend_direction(current: float, previous: float | None, field: str) -> str:
        if previous is None:
            return "stable"
        delta = current - previous
        if abs(delta) < 0.3:
            return "stable"
        # mood / sleep：EMA 下降表示 distress 上升
        if field in ("mood", "sleep"):
            if delta <= -0.3:
                return "worsening"
            if delta >= 0.3:
                return "improving"
        else:
            if delta >= 0.3:
                return "worsening"
            if delta <= -0.3:
                return "improving"
        return "stable"

    @staticmethod
    def _sustained_low(
        current_ema: float | None,
        curve: list[dict[str, Any]],
        threshold: float,
    ) -> bool:
        if current_ema is None:
            return False
        recent = [p["ema"] for p in curve[-5:] if p.get("ema") is not None]
        if len(recent) < 3:
            return current_ema <= threshold
        return sum(1 for v in recent if v <= threshold) >= 3

    @staticmethod
    def _is_rising(curve: list[dict[str, Any]], min_delta: float = 1.0) -> bool:
        if len(curve) < 3:
            return False
        ema_vals = [p["ema"] for p in curve if p.get("ema") is not None]
        if len(ema_vals) < 3:
            return False
        return ema_vals[-1] - ema_vals[0] >= min_delta
