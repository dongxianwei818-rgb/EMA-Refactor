"""从 ema_diary 文本提取特性并写入 text_features。"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import BaselineProfile, EmaDiary, EmaQuestion, TextFeature
from app.services.analysis.text_lexicons import (
    EMOTION_NEGATIVE,
    EMOTION_POSITIVE,
    HOPELESSNESS,
    SELF_REFERENCE,
    STRESS_EVENTS,
)
from app.services.datetime_fields import format_datetime

logger = logging.getLogger(__name__)

SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;\n]+")
EMBEDDING_DIM = 768


class TextFeatureExtractor:
    """
    文本特性提取器。

    从 ema_diary.text 提取六类特性：
    1. 情绪词（积极/消极）
    2. 自我指向
    3. 绝望感
    4. 压力事件
    5. 语言复杂度（字数、句长、重复表达）
    6. 语义向量（可选 SentenceTransformer；默认 lexical-proxy）

    可同时参考 ema_questions、baseline_profiles 等同轮/同用户上下文以提高判定精度。
    """

    def __init__(self, db: Session, embedding_model: str | None = None) -> None:
        self.db = db
        settings = get_settings()
        self.embedding_model = embedding_model if embedding_model is not None else settings.text_embedding_model
        self._transformer: Any | False | None = None

    # ------------------------------------------------------------------ public

    def process_diary(self, diary: EmaDiary) -> TextFeature:
        """提取特性并 upsert 至 text_features。"""
        features = self.extract_from_diary(diary)
        return self.save_features(diary, features)

    def extract_from_diary(self, diary: EmaDiary) -> dict[str, Any]:
        text = (diary.text or "").strip()
        context = self._load_context(diary)

        emotional = self._extract_emotional_words(text, context)
        self_ref = self._extract_self_reference(text)
        hopeless = self._extract_hopelessness(text, context)
        stress = self._extract_stress_events(text, context)
        complexity = self._extract_linguistic_complexity(text)
        embedding = self._extract_semantic_embedding(text, emotional, self_ref, hopeless, stress)
        enrichment = self._build_context_enrichment(context, emotional, hopeless)
        composite = self._build_composite_signals(emotional, self_ref, hopeless, stress, context, enrichment)

        return {
            "diary_id": diary.id,
            "source_text_length": len(text),
            "emotional_words": emotional,
            "self_reference": self_ref,
            "hopelessness": hopeless,
            "stress_events": stress,
            "linguistic_complexity": complexity,
            "semantic_embedding": embedding,
            "context_enrichment": enrichment,
            "composite_risk_signals": composite,
            "extracted_at": format_datetime(datetime.now()),
        }

    def save_features(self, diary: EmaDiary, features: dict[str, Any]) -> TextFeature:
        row = (
            self.db.query(TextFeature)
            .filter(
                TextFeature.user_id == diary.user_id,
                TextFeature.task_date == diary.task_date,
                TextFeature.session_id == diary.session_id,
            )
            .first()
        )
        if row:
            row.features = features
            row.status = "done"
            row.submission_id = diary.id
        else:
            row = TextFeature(
                user_id=diary.user_id,
                task_date=diary.task_date,
                session_id=diary.session_id,
                submission_id=diary.id,
                status="done",
                features=features,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def process_diary_by_id(self, diary_id: int) -> TextFeature | None:
        diary = self.db.query(EmaDiary).filter(EmaDiary.id == diary_id).first()
        if not diary:
            return None
        return self.process_diary(diary)

    def process_pending_diaries(self, user_id: int | None = None, limit: int = 100) -> int:
        """批量处理尚未生成 text_features 的日记。"""
        q = self.db.query(EmaDiary).order_by(EmaDiary.id.desc())
        if user_id is not None:
            q = q.filter(EmaDiary.user_id == user_id)
        count = 0
        for diary in q.limit(limit * 3):
            if count >= limit:
                break
            exists = (
                self.db.query(TextFeature)
                .filter(
                    TextFeature.user_id == diary.user_id,
                    TextFeature.task_date == diary.task_date,
                    TextFeature.session_id == diary.session_id,
                    TextFeature.status == "done",
                )
                .first()
            )
            if exists:
                continue
            try:
                self.process_diary(diary)
                count += 1
            except Exception:
                logger.exception("text feature extract failed diary_id=%s", diary.id)
        return count

    # ------------------------------------------------------------------ context

    def _load_context(self, diary: EmaDiary) -> dict[str, Any]:
        questionnaire = (
            self.db.query(EmaQuestion)
            .filter(
                EmaQuestion.user_id == diary.user_id,
                EmaQuestion.task_date == diary.task_date,
                EmaQuestion.session_id == diary.session_id,
            )
            .first()
        )
        baseline = (
            self.db.query(BaselineProfile).filter(BaselineProfile.user_id == diary.user_id).first()
        )
        return {
            "questionnaire": questionnaire,
            "baseline": baseline,
        }

    # ------------------------------------------------------------------ extractors

    def _match_keywords(self, text: str, keywords: tuple[str, ...]) -> list[str]:
        hits: list[str] = []
        for kw in keywords:
            if kw and kw in text:
                hits.append(kw)
        return hits

    def _extract_emotional_words(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        pos_hits = self._match_keywords(text, EMOTION_POSITIVE)
        neg_hits = self._match_keywords(text, EMOTION_NEGATIVE)

        pos_count = len(pos_hits)
        neg_count = len(neg_hits)
        total = pos_count + neg_count
        score = (pos_count - neg_count) / total if total else 0.0

        questionnaire = context.get("questionnaire")
        if questionnaire and neg_count == 0 and questionnaire.mood <= 4:
            neg_hits.append("__context_low_mood__")
            neg_count += 1
            score = (pos_count - neg_count) / max(pos_count + neg_count, 1)

        polarity = "neutral"
        if score > 0.15:
            polarity = "positive"
        elif score < -0.15:
            polarity = "negative"

        return {
            "positive": {"count": pos_count, "hits": pos_hits},
            "negative": {"count": neg_count, "hits": neg_hits},
            "score": round(score, 4),
            "polarity": polarity,
        }

    def _extract_self_reference(self, text: str) -> dict[str, Any]:
        hits = self._match_keywords(text, SELF_REFERENCE)
        char_len = max(len(text), 1)
        first_person = text.count("我")
        density = round((first_person + len(hits)) / char_len, 4)
        return {
            "count": len(hits) + first_person,
            "hits": hits,
            "first_person_count": first_person,
            "density": density,
        }

    def _extract_hopelessness(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        hits = self._match_keywords(text, HOPELESSNESS)
        score = min(len(hits) / 3.0, 1.0)

        questionnaire = context.get("questionnaire")
        if questionnaire and questionnaire.negative in ("是", "yes", "Yes", "YES"):
            if "__questionnaire_negative__" not in hits:
                hits.append("__questionnaire_negative__")
                score = min(score + 0.25, 1.0)

        baseline = context.get("baseline")
        if baseline and baseline.self_harm in ("是", "有时", "偶尔"):
            score = min(score + 0.15, 1.0)

        return {
            "count": len(hits),
            "hits": hits,
            "score": round(score, 4),
        }

    def _extract_stress_events(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        hits: list[dict[str, str]] = []
        categories: Counter[str] = Counter()

        for category, words in STRESS_EVENTS.items():
            for word in words:
                if word in text:
                    hits.append({"category": category, "word": word})
                    categories[category] += 1

        baseline = context.get("baseline")
        if baseline:
            baseline_map = {
                "course_pressure": "exam",
                "exam_pressure": "exam",
                "gpa_pressure": "exam",
                "job_pressure": "employment",
            }
            for field, cat in baseline_map.items():
                val = getattr(baseline, field, None)
                if val and str(val) in ("高", "较高", "很大", "非常大", "经常"):
                    if cat not in categories:
                        categories[cat] += 1
                        hits.append({"category": cat, "word": f"__baseline_{field}__"})

        return {
            "count": len(hits),
            "hits": hits,
            "categories": dict(categories),
        }

    def _extract_linguistic_complexity(self, text: str) -> dict[str, Any]:
        char_count = len(text)
        sentences = [s for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
        if not sentences:
            sentences = [text] if text else [""]
        sentence_count = len(sentences)
        avg_sentence_length = round(char_count / sentence_count, 2) if sentence_count else 0.0
        unique_chars = len(set(text))
        unique_char_ratio = round(unique_chars / max(char_count, 1), 4)

        repeated_phrases, repetition_score = self._detect_repetition(text)

        return {
            "char_count": char_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": avg_sentence_length,
            "unique_char_ratio": unique_char_ratio,
            "repetition_score": repetition_score,
            "repeated_phrases": repeated_phrases[:10],
        }

    def _detect_repetition(self, text: str) -> tuple[list[str], float]:
        if len(text) < 4:
            return [], 0.0
        counts: Counter[str] = Counter()
        for size in (2, 3, 4):
            for i in range(len(text) - size + 1):
                frag = text[i : i + size]
                if frag.strip():
                    counts[frag] += 1
        repeated = [k for k, v in counts.items() if v >= 2]
        repetition_score = round(min(len(repeated) / 5.0, 1.0), 4)
        return repeated, repetition_score

    def _extract_semantic_embedding(
        self,
        text: str,
        emotional: dict[str, Any],
        self_ref: dict[str, Any],
        hopeless: dict[str, Any],
        stress: dict[str, Any],
    ) -> dict[str, Any]:
        transformer = self._get_transformer()
        if transformer:
            try:
                vector = transformer.encode(text, normalize_embeddings=True)
                if hasattr(vector, "tolist"):
                    vector = vector.tolist()
                return {
                    "model": self.embedding_model,
                    "dimension": len(vector),
                    "vector": vector,
                }
            except Exception:
                logger.exception("SentenceTransformer encode failed, fallback to lexical proxy")

        vector = self._build_lexical_embedding(text, emotional, self_ref, hopeless, stress)
        return {
            "model": "lexical-proxy-v1",
            "dimension": len(vector),
            "vector": vector,
        }

    def _build_lexical_embedding(
        self,
        text: str,
        emotional: dict[str, Any],
        self_ref: dict[str, Any],
        hopeless: dict[str, Any],
        stress: dict[str, Any],
    ) -> list[float]:
        """无外部模型时的语义向量代理（768 维，归一化）。"""
        vec = [0.0] * EMBEDDING_DIM
        vec[0] = emotional.get("score", 0.0)
        vec[1] = emotional["positive"]["count"] / 10.0
        vec[2] = emotional["negative"]["count"] / 10.0
        vec[3] = self_ref.get("density", 0.0)
        vec[4] = hopeless.get("score", 0.0)
        vec[5] = min(stress.get("count", 0) / 5.0, 1.0)

        for i, ch in enumerate(text):
            for size in (1, 2, 3):
                if i + size > len(text):
                    continue
                ng = text[i : i + size]
                bucket = (hash(ng) % (EMBEDDING_DIM - 32)) + 32
                vec[bucket] += 1.0

        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]

    def _get_transformer(self) -> Any | False:
        if self._transformer is not None:
            return self._transformer or False
        if not self.embedding_model:
            self._transformer = False
            return False
        try:
            from sentence_transformers import SentenceTransformer

            self._transformer = SentenceTransformer(self.embedding_model)
        except Exception:
            logger.info(
                "SentenceTransformer unavailable (model=%s), using lexical-proxy",
                self.embedding_model,
            )
            self._transformer = False
        return self._transformer or False

    # ------------------------------------------------------------------ enrichment

    def _build_context_enrichment(
        self,
        context: dict[str, Any],
        emotional: dict[str, Any],
        hopeless: dict[str, Any],
    ) -> dict[str, Any]:
        questionnaire = context.get("questionnaire")
        baseline = context.get("baseline")

        q_data = None
        if questionnaire:
            q_data = {
                "mood": questionnaire.mood,
                "stress": questionnaire.stress,
                "anxiety": questionnaire.anxiety,
                "lonely": questionnaire.lonely,
                "sleep": questionnaire.sleep,
                "fatigue": questionnaire.fatigue,
                "function": questionnaire.function,
                "negative": questionnaire.negative,
            }

        b_data = None
        if baseline:
            b_data = {
                "course_pressure": baseline.course_pressure,
                "exam_pressure": baseline.exam_pressure,
                "job_pressure": baseline.job_pressure,
                "self_harm": baseline.self_harm,
                "phq9_1": baseline.phq9_1,
                "phq9_2": baseline.phq9_2,
                "gad7_1": baseline.gad7_1,
                "gad7_2": baseline.gad7_2,
            }

        consistency = self._text_questionnaire_consistency(q_data, emotional, hopeless)

        return {
            "questionnaire": q_data,
            "baseline": b_data,
            "text_questionnaire_consistency": consistency,
        }

    def _text_questionnaire_consistency(
        self,
        questionnaire: dict[str, Any] | None,
        emotional: dict[str, Any],
        hopeless: dict[str, Any],
    ) -> float | None:
        if not questionnaire:
            return None
        distress_from_q = (
            (10 - questionnaire["mood"]) / 10.0
            + questionnaire["stress"] / 10.0
            + questionnaire["anxiety"] / 10.0
        ) / 3.0
        distress_from_text = max(-emotional.get("score", 0), 0) * 0.5 + hopeless.get("score", 0) * 0.5
        diff = abs(distress_from_q - distress_from_text)
        return round(max(0.0, 1.0 - diff), 4)

    def _build_composite_signals(
        self,
        emotional: dict[str, Any],
        self_ref: dict[str, Any],
        hopeless: dict[str, Any],
        stress: dict[str, Any],
        context: dict[str, Any],
        enrichment: dict[str, Any],
    ) -> dict[str, Any]:
        reasons: list[str] = []
        elevated = False

        if emotional["polarity"] == "negative" and emotional["negative"]["count"] >= 2:
            elevated = True
            reasons.append("日记消极情绪词偏多")
        if hopeless["score"] >= 0.34:
            elevated = True
            reasons.append("绝望感表达")
        if self_ref["density"] >= 0.08 and hopeless["score"] >= 0.2:
            elevated = True
            reasons.append("高自我指向伴随绝望表达")
        if stress["count"] >= 2:
            reasons.append("多重压力事件")

        questionnaire = context.get("questionnaire")
        if questionnaire and questionnaire.mood <= 3 and emotional["polarity"] != "positive":
            elevated = True
            reasons.append("问卷低情绪与文本一致偏低")

        consistency = enrichment.get("text_questionnaire_consistency")
        if consistency is not None and consistency < 0.4:
            reasons.append("文本与问卷情绪不一致，需人工复核")

        return {
            "elevated_distress": elevated,
            "reasons": reasons,
        }
