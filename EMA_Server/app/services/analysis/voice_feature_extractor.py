"""从 ema_voice 录音提取声学+转写特性并写入 voice_features。"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    BaselineProfile,
    EmaDiary,
    EmaQuestion,
    EmaVoice,
    QuestionsFeature,
    TextFeature,
    VoiceFeature,
)
from app.services.analysis.text_lexicons import EMOTION_NEGATIVE, EMOTION_POSITIVE, HOPELESSNESS
from app.services.analysis.voice_acoustic import analyze_acoustic_waveform, load_mono_audio
from app.services.consent_service import user_has_consent
from app.services.datetime_fields import format_datetime

logger = logging.getLogger(__name__)


class VoiceFeatureExtractor:
    """
    语音特性提取器。

    从 ema_voice 录音提取：
    1. 语速  2. 停顿时长  3. 音高变化  4. 能量/响度  5. 声音单调性  6. 语音转文本语义

    轻量版仅保存转写+声学特征；研究版可在知情同意后保留原始音频引用。
    可同时参考 ema_questions、questions_features、ema_diary、baseline 等同轮上下文。
    """

    def __init__(
        self,
        db: Session,
        asr_model: str | None = None,
        storage_mode: str | None = None,
        delete_audio_after_extract: bool | None = None,
    ) -> None:
        self.db = db
        settings = get_settings()
        self.asr_model = asr_model if asr_model is not None else settings.voice_asr_model
        self.asr_language = settings.voice_asr_language
        self.storage_mode = storage_mode if storage_mode is not None else settings.voice_storage_mode
        self.delete_audio_after_extract = (
            delete_audio_after_extract
            if delete_audio_after_extract is not None
            else settings.voice_delete_audio_after_extract
        )
        self._whisper: Any | False | None = None

    # ------------------------------------------------------------------ public

    def process_voice(self, voice: EmaVoice) -> VoiceFeature:
        features = self.extract_from_voice(voice)
        row = self.save_features(voice, features)
        self._maybe_delete_audio(voice, features)
        return row

    def extract_from_voice(self, voice: EmaVoice) -> dict[str, Any]:
        context = self._load_context(voice)

        if voice.skip:
            return self._skipped_features(voice, context)

        audio_path = self._resolve_audio_path(voice)
        decode_ok = False
        acoustic: dict[str, Any] | None = None
        transcription: dict[str, Any] = {"text": "", "model": None, "language": self.asr_language}

        if audio_path and audio_path.exists():
            try:
                y, sr = self._load_audio(audio_path)
                acoustic = analyze_acoustic_waveform(y, sr, float(voice.duration_sec or 0))
                decode_ok = True
                transcription = self._transcribe(audio_path)
                if transcription.get("text"):
                    chars_per_min = self._chars_per_minute(
                        transcription["text"],
                        acoustic.get("speech_time_sec") or voice.duration_sec,
                    )
                    acoustic["speech_rate"]["chars_per_minute"] = chars_per_min
                    if chars_per_min is not None:
                        acoustic["speech_rate"]["label"] = self._rate_label_from_cpm(chars_per_min)
            except Exception:
                logger.exception("voice acoustic decode failed voice_id=%s path=%s", voice.id, audio_path)

        if acoustic is None:
            acoustic = self._metadata_fallback_acoustic(voice)

        semantic = self._analyze_transcript_semantics(transcription.get("text") or "")
        user_baseline = self._user_historical_baseline(voice.user_id, voice.id)
        enrichment = self._build_context_enrichment(context, acoustic, semantic, user_baseline)
        composite = self._build_composite_signals(acoustic, semantic, context, enrichment, user_baseline)

        storage = self._storage_info(voice, audio_path, decode_ok, context)

        return {
            "voice_id": voice.id,
            "duration_sec": voice.duration_sec,
            "skip": False,
            "decode_ok": decode_ok,
            "acoustic": acoustic,
            "transcription": transcription,
            "semantic": semantic,
            "user_historical_baseline": user_baseline,
            "context_enrichment": enrichment,
            "composite_signals": composite,
            "storage": storage,
            "extracted_at": format_datetime(datetime.now()),
        }

    def save_features(self, voice: EmaVoice, features: dict[str, Any]) -> VoiceFeature:
        status = "done" if not features.get("error") else "failed"
        if voice.skip:
            status = "done"

        row = (
            self.db.query(VoiceFeature)
            .filter(
                VoiceFeature.user_id == voice.user_id,
                VoiceFeature.task_date == voice.task_date,
                VoiceFeature.session_id == voice.session_id,
            )
            .first()
        )
        if row:
            row.features = features
            row.status = status
            row.submission_id = voice.id
        else:
            row = VoiceFeature(
                user_id=voice.user_id,
                task_date=voice.task_date,
                session_id=voice.session_id,
                submission_id=voice.id,
                status=status,
                features=features,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def process_voice_by_id(self, voice_id: int) -> VoiceFeature | None:
        voice = self.db.query(EmaVoice).filter(EmaVoice.id == voice_id).first()
        if not voice:
            return None
        return self.process_voice(voice)

    def process_pending_voices(self, user_id: int | None = None, limit: int = 100) -> int:
        q = self.db.query(EmaVoice).filter(EmaVoice.skip.is_(False)).order_by(EmaVoice.id.desc())
        if user_id is not None:
            q = q.filter(EmaVoice.user_id == user_id)
        count = 0
        for voice in q.limit(limit * 3):
            if count >= limit:
                break
            exists = (
                self.db.query(VoiceFeature)
                .filter(
                    VoiceFeature.user_id == voice.user_id,
                    VoiceFeature.task_date == voice.task_date,
                    VoiceFeature.session_id == voice.session_id,
                    VoiceFeature.status == "done",
                )
                .first()
            )
            if exists:
                continue
            try:
                self.process_voice(voice)
                count += 1
            except Exception:
                logger.exception("voice feature extract failed voice_id=%s", voice.id)
        return count

    # ------------------------------------------------------------------ audio

    def _resolve_audio_path(self, voice: EmaVoice) -> Path | None:
        if not voice.file_name:
            return None
        return get_settings().voice_files_path / voice.file_name

    @staticmethod
    def _load_audio(path: Path) -> tuple[np.ndarray, int]:
        return load_mono_audio(path)

    def _transcribe(self, path: Path) -> dict[str, Any]:
        if not self.asr_model:
            return {"text": "", "model": None, "language": self.asr_language, "confidence": None}

        model = self._get_whisper()
        if not model:
            return {"text": "", "model": self.asr_model, "language": self.asr_language, "confidence": None}

        try:
            segments, info = model.transcribe(str(path), language=self.asr_language, beam_size=1)
            text = "".join(seg.text for seg in segments).strip()
            confidences = [getattr(seg, "avg_logprob", None) for seg in segments]
            confidences = [c for c in confidences if c is not None]
            confidence = round(float(np.mean(confidences)), 4) if confidences else None
            return {
                "text": text,
                "model": self.asr_model,
                "language": getattr(info, "language", self.asr_language),
                "confidence": confidence,
            }
        except Exception:
            logger.exception("voice ASR failed path=%s", path)
            return {"text": "", "model": self.asr_model, "language": self.asr_language, "confidence": None}

    def _get_whisper(self) -> Any | False:
        if self._whisper is not None:
            return self._whisper or False
        try:
            from faster_whisper import WhisperModel

            self._whisper = WhisperModel(self.asr_model, device="cpu", compute_type="int8")
        except Exception:
            logger.info("faster-whisper unavailable (model=%s), ASR disabled", self.asr_model)
            self._whisper = False
        return self._whisper or False

    def _maybe_delete_audio(self, voice: EmaVoice, features: dict[str, Any]) -> None:
        if voice.skip or not self.delete_audio_after_extract:
            return
        if self.storage_mode == "research":
            return
        path = self._resolve_audio_path(voice)
        if path and path.exists():
            try:
                path.unlink()
                if features.get("storage"):
                    features["storage"]["raw_audio_deleted"] = True
                    row = (
                        self.db.query(VoiceFeature)
                        .filter(
                            VoiceFeature.user_id == voice.user_id,
                            VoiceFeature.task_date == voice.task_date,
                            VoiceFeature.session_id == voice.session_id,
                        )
                        .first()
                    )
                    if row:
                        row.features = features
                        self.db.commit()
            except OSError:
                logger.exception("failed to delete voice file voice_id=%s", voice.id)

    # ------------------------------------------------------------------ semantics

    @staticmethod
    def _match_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
        return [kw for kw in keywords if kw and kw in text]

    def _analyze_transcript_semantics(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {
                "char_count": 0,
                "positive_hits": [],
                "negative_hits": [],
                "hopelessness_hits": [],
                "distress_score": 0.0,
            }
        pos = self._match_keywords(text, EMOTION_POSITIVE)
        neg = self._match_keywords(text, EMOTION_NEGATIVE)
        hopeless = self._match_keywords(text, HOPELESSNESS)
        distress = round(min(1.0, len(neg) * 0.15 + len(hopeless) * 0.2), 4)
        return {
            "char_count": len(text),
            "positive_hits": pos,
            "negative_hits": neg,
            "hopelessness_hits": hopeless,
            "distress_score": distress,
        }

    @staticmethod
    def _chars_per_minute(text: str, speech_sec: float | None) -> float | None:
        if not text or not speech_sec or speech_sec <= 0:
            return None
        return round(len(text) / (speech_sec / 60.0), 2)

    @staticmethod
    def _rate_label_from_cpm(cpm: float) -> str:
        # 中文口语约 150–250 字/分钟
        if cpm < 120:
            return "slow"
        if cpm > 280:
            return "fast"
        return "normal"

    @staticmethod
    def _metadata_fallback_acoustic(voice: EmaVoice) -> dict[str, Any]:
        dur = float(voice.duration_sec or 0)
        return {
            "duration_sec": dur,
            "sample_rate": None,
            "speech_ratio": None,
            "speech_time_sec": None,
            "speech_rate": {
                "onset_count": None,
                "onsets_per_minute": None,
                "normalized_rate": None,
                "label": "unknown",
            },
            "pause": {"count": None, "total_sec": None, "mean_sec": None, "max_sec": None, "pause_ratio": None},
            "pitch": {"variation_score": None, "std_hz": None, "mean_hz": None},
            "energy": {"mean_db": None, "dynamic_range_db": None},
            "monotony": {"score": None, "label": "unknown"},
            "fallback": True,
        }

    # ------------------------------------------------------------------ context

    def _load_context(self, voice: EmaVoice) -> dict[str, Any]:
        questionnaire = (
            self.db.query(EmaQuestion)
            .filter(
                EmaQuestion.user_id == voice.user_id,
                EmaQuestion.task_date == voice.task_date,
                EmaQuestion.session_id == voice.session_id,
            )
            .first()
        )
        questions_feature = (
            self.db.query(QuestionsFeature)
            .filter(
                QuestionsFeature.user_id == voice.user_id,
                QuestionsFeature.task_date == voice.task_date,
                QuestionsFeature.session_id == voice.session_id,
                QuestionsFeature.status == "done",
            )
            .first()
        )
        diary = (
            self.db.query(EmaDiary)
            .filter(
                EmaDiary.user_id == voice.user_id,
                EmaDiary.task_date == voice.task_date,
                EmaDiary.session_id == voice.session_id,
            )
            .first()
        )
        text_feature = (
            self.db.query(TextFeature)
            .filter(
                TextFeature.user_id == voice.user_id,
                TextFeature.task_date == voice.task_date,
                TextFeature.session_id == voice.session_id,
                TextFeature.status == "done",
            )
            .first()
        )
        baseline = (
            self.db.query(BaselineProfile).filter(BaselineProfile.user_id == voice.user_id).first()
        )
        return {
            "questionnaire": questionnaire,
            "questions_feature": questions_feature,
            "diary": diary,
            "text_feature": text_feature,
            "baseline": baseline,
        }

    def _user_historical_baseline(self, user_id: int, current_voice_id: int) -> dict[str, Any]:
        """用户历史语音语速/单调性基线，用于相对偏离判定。"""
        rows = (
            self.db.query(VoiceFeature)
            .filter(
                VoiceFeature.user_id == user_id,
                VoiceFeature.status == "done",
            )
            .order_by(VoiceFeature.id.desc())
            .limit(15)
            .all()
        )
        rates: list[float] = []
        monotony: list[float] = []
        for row in rows:
            if row.submission_id == current_voice_id:
                continue
            feat = row.features or {}
            if feat.get("skip"):
                continue
            acoustic = feat.get("acoustic") or {}
            rate = (acoustic.get("speech_rate") or {}).get("normalized_rate")
            mono = (acoustic.get("monotony") or {}).get("score")
            if rate is not None:
                rates.append(float(rate))
            if mono is not None:
                monotony.append(float(mono))
        return {
            "sample_count": len(rates),
            "avg_speech_rate": round(sum(rates) / len(rates), 4) if rates else None,
            "avg_monotony": round(sum(monotony) / len(monotony), 4) if monotony else None,
        }

    def _build_context_enrichment(
        self,
        context: dict[str, Any],
        acoustic: dict[str, Any],
        semantic: dict[str, Any],
        user_baseline: dict[str, Any],
    ) -> dict[str, Any]:
        q = context.get("questionnaire")
        q_data = None
        if q:
            q_data = {
                "mood": q.mood,
                "stress": q.stress,
                "anxiety": q.anxiety,
                "fatigue": q.fatigue,
                "negative": q.negative,
            }

        qf_summary = None
        qf = context.get("questions_feature")
        if qf and qf.features:
            comp = qf.features.get("composite_signals") or {}
            qf_summary = {
                "sustained_low_mood": comp.get("sustained_low_mood"),
                "rising_stress": comp.get("rising_stress"),
            }

        consistency = self._voice_questionnaire_consistency(acoustic, semantic, q)
        rate_deviation = self._speech_rate_deviation(acoustic, user_baseline)

        return {
            "questionnaire": q_data,
            "questions_feature": qf_summary,
            "voice_questionnaire_consistency": consistency,
            "speech_rate_deviation_from_user": rate_deviation,
        }

    @staticmethod
    def _voice_questionnaire_consistency(
        acoustic: dict[str, Any],
        semantic: dict[str, Any],
        questionnaire: EmaQuestion | None,
    ) -> float | None:
        if not questionnaire:
            return None
        distress_from_q = (
            (10 - questionnaire.mood) / 10.0
            + questionnaire.stress / 10.0
            + questionnaire.anxiety / 10.0
        ) / 3.0
        mono = (acoustic.get("monotony") or {}).get("score") or 0.0
        pause_ratio = (acoustic.get("pause") or {}).get("pause_ratio") or 0.0
        rate_label = (acoustic.get("speech_rate") or {}).get("label")
        distress_from_voice = min(
            1.0,
            mono * 0.35 + pause_ratio * 0.35 + semantic.get("distress_score", 0) * 0.3,
        )
        if rate_label == "slow":
            distress_from_voice = min(1.0, distress_from_voice + 0.15)
        return round(max(0.0, 1.0 - abs(distress_from_q - distress_from_voice)), 4)

    @staticmethod
    def _speech_rate_deviation(acoustic: dict[str, Any], user_baseline: dict[str, Any]) -> float | None:
        current = (acoustic.get("speech_rate") or {}).get("normalized_rate")
        avg = user_baseline.get("avg_speech_rate")
        if current is None or avg is None:
            return None
        return round(current - avg, 4)

    def _build_composite_signals(
        self,
        acoustic: dict[str, Any],
        semantic: dict[str, Any],
        context: dict[str, Any],
        enrichment: dict[str, Any],
        user_baseline: dict[str, Any],
    ) -> dict[str, Any]:
        reasons: list[str] = []
        rate = acoustic.get("speech_rate") or {}
        pause = acoustic.get("pause") or {}
        pitch = acoustic.get("pitch") or {}
        monotony = acoustic.get("monotony") or {}

        slow_speech = rate.get("label") == "slow"
        high_pause = (pause.get("pause_ratio") or 0) >= 0.35
        flat_affect = (monotony.get("score") or 0) >= 0.6 or (pitch.get("variation_score") or 1) <= 0.25
        depressed_pattern = slow_speech and (high_pause or flat_affect)

        if depressed_pattern:
            reasons.append("语速偏慢且停顿/单调性偏高，符合抑郁相关声学模式")
        if flat_affect:
            reasons.append("音高/能量变化偏小，情感表达偏平淡")
        if semantic.get("distress_score", 0) >= 0.3:
            reasons.append("转写文本含消极或绝望表达")

        q = context.get("questionnaire")
        if q and q.mood <= 4 and (slow_speech or flat_affect):
            reasons.append("问卷低情绪与声学指标一致")
        if q and q.mood >= 7 and (slow_speech or semantic.get("distress_score", 0) >= 0.3):
            reasons.append("问卷情绪较好但语音/转写 distress 偏高，建议复核")

        deviation = enrichment.get("speech_rate_deviation_from_user")
        if deviation is not None and deviation <= -0.2:
            reasons.append("语速相对个人基线明显偏慢")

        consistency = enrichment.get("voice_questionnaire_consistency")
        if consistency is not None and consistency < 0.4:
            reasons.append("语音与问卷 distress 不一致")

        baseline = context.get("baseline")
        if baseline and baseline.self_harm in ("是", "有") and semantic.get("hopelessness_hits"):
            reasons.append("基线自伤风险与语音绝望表达同时出现")

        elevated = bool(depressed_pattern or flat_affect or len(reasons) >= 2)

        return {
            "elevated_distress": elevated,
            "depressed_speech_pattern": depressed_pattern,
            "flat_affect": flat_affect,
            "slow_speech": slow_speech,
            "high_pause": high_pause,
            "reasons": reasons,
        }

    def _storage_info(
        self,
        voice: EmaVoice,
        path: Path | None,
        decode_ok: bool,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        has_consent = user_has_consent(self.db, voice.user_id)
        retain_raw = self.storage_mode == "research" and has_consent
        return {
            "mode": self.storage_mode,
            "raw_audio_retained": retain_raw and path is not None and path.exists(),
            "raw_audio_path": str(path) if retain_raw and path else None,
            "decode_ok": decode_ok,
            "delete_after_extract": self.delete_audio_after_extract and self.storage_mode != "research",
        }

    @staticmethod
    def _skipped_features(voice: EmaVoice, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "voice_id": voice.id,
            "skip": True,
            "duration_sec": voice.duration_sec,
            "acoustic": None,
            "transcription": None,
            "semantic": None,
            "context_enrichment": {"skipped": True},
            "composite_signals": {"elevated_distress": False, "skipped": True, "reasons": []},
            "extracted_at": format_datetime(datetime.now()),
        }
