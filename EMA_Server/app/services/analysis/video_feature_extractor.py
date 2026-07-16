"""从 ema_video 录制提取面部视觉特性并写入 video_features。"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    BaselineProfile,
    EmaDiary,
    EmaQuestion,
    EmaVideo,
    QuestionsFeature,
    TextFeature,
    VideoFeature,
    VoiceFeature,
)
from app.services.analysis.json_safe import sanitize_for_json
from app.services.analysis.video_visual import analyze_video_file
from app.services.consent_service import user_has_consent
from app.services.datetime_fields import format_datetime

logger = logging.getLogger(__name__)


class VideoFeatureExtractor:
    """
    视频特性提取器。

    从 ema_video 提取六类特性：
    1. 面部动作单元（微笑、皱眉、眼部动作代理）
    2. 头部姿态（低头、转头、稳定性）
    3. 眼神方向（回避倾向）
    4. 表情变化幅度
    5. 面部活动量（迟滞/活跃）
    6. 视频完成率（露脸意愿行为信号）

    可同时参考 ema_questions、voice_features、text_features 等同轮上下文。
    """

    def __init__(
        self,
        db: Session,
        sample_fps: float | None = None,
        max_frames: int | None = None,
        face_backend: str | None = None,
        storage_mode: str | None = None,
        delete_video_after_extract: bool | None = None,
    ) -> None:
        self.db = db
        settings = get_settings()
        self.sample_fps = sample_fps if sample_fps is not None else settings.video_sample_fps
        self.max_frames = max_frames if max_frames is not None else settings.video_max_frames
        self.face_backend = face_backend if face_backend is not None else settings.video_face_backend
        self.storage_mode = storage_mode if storage_mode is not None else settings.video_storage_mode
        self.delete_video_after_extract = (
            delete_video_after_extract
            if delete_video_after_extract is not None
            else settings.video_delete_after_extract
        )

    # ------------------------------------------------------------------ public

    def process_video(self, video: EmaVideo) -> VideoFeature:
        features = self.extract_from_video(video)
        row = self.save_features(video, features)
        self._maybe_delete_video(video, features)
        return row

    def extract_from_video(self, video: EmaVideo) -> dict[str, Any]:
        context = self._load_context(video)

        if video.skip:
            return self._skipped_features(video)

        video_path = self._resolve_video_path(video)
        visual: dict[str, Any] | None = None
        decode_ok = False

        if video_path and video_path.exists():
            try:
                visual = analyze_video_file(
                    str(video_path),
                    expected_duration_sec=float(video.duration_sec or 0),
                    sample_fps=self.sample_fps,
                    max_frames=self.max_frames,
                    backend=self.face_backend,
                )
                decode_ok = True
            except Exception:
                logger.exception("video visual decode failed video_id=%s path=%s", video.id, video_path)

        if visual is None:
            visual = self._metadata_fallback_visual(video)

        user_baseline = self._user_historical_baseline(video.user_id, video.id)
        enrichment = self._build_context_enrichment(context, visual, user_baseline)
        composite = self._build_composite_signals(visual, context, enrichment, user_baseline)
        storage = self._storage_info(video, video_path, decode_ok)

        return {
            "video_id": video.id,
            "duration_sec": video.duration_sec,
            "skip": False,
            "decode_ok": decode_ok,
            "visual": visual,
            "user_historical_baseline": user_baseline,
            "context_enrichment": enrichment,
            "composite_signals": composite,
            "storage": storage,
            "extracted_at": format_datetime(datetime.now()),
        }

    def save_features(self, video: EmaVideo, features: dict[str, Any]) -> VideoFeature:
        status = "done" if not features.get("error") else "failed"
        if video.skip:
            status = "done"

        features = sanitize_for_json(features)
        row = (
            self.db.query(VideoFeature)
            .filter(
                VideoFeature.user_id == video.user_id,
                VideoFeature.task_date == video.task_date,
                VideoFeature.session_id == video.session_id,
            )
            .first()
        )
        if row:
            row.features = features
            row.status = status
            row.submission_id = video.id
        else:
            row = VideoFeature(
                user_id=video.user_id,
                task_date=video.task_date,
                session_id=video.session_id,
                submission_id=video.id,
                status=status,
                features=features,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def process_video_by_id(self, video_id: int) -> VideoFeature | None:
        video = self.db.query(EmaVideo).filter(EmaVideo.id == video_id).first()
        if not video:
            return None
        return self.process_video(video)

    def process_pending_videos(self, user_id: int | None = None, limit: int = 100) -> int:
        q = self.db.query(EmaVideo).filter(EmaVideo.skip.is_(False)).order_by(EmaVideo.id.desc())
        if user_id is not None:
            q = q.filter(EmaVideo.user_id == user_id)
        count = 0
        for video in q.limit(limit * 3):
            if count >= limit:
                break
            exists = (
                self.db.query(VideoFeature)
                .filter(
                    VideoFeature.user_id == video.user_id,
                    VideoFeature.task_date == video.task_date,
                    VideoFeature.session_id == video.session_id,
                    VideoFeature.status == "done",
                )
                .first()
            )
            if exists:
                continue
            try:
                self.process_video(video)
                count += 1
            except Exception:
                logger.exception("video feature extract failed video_id=%s", video.id)
        return count

    # ------------------------------------------------------------------ helpers

    def _resolve_video_path(self, video: EmaVideo) -> Path | None:
        if not video.file_name:
            return None
        return get_settings().video_files_path / video.file_name

    @staticmethod
    def _metadata_fallback_visual(video: EmaVideo) -> dict[str, Any]:
        dur = float(video.duration_sec or 0)
        return {
            "frames_sampled": 0,
            "duration_sec": dur,
            "face_visible_ratio": None,
            "completion": {
                "duration_sec": dur,
                "completion_score": round(min(dur / 60.0, 1.0), 4) if dur else 0.0,
                "reluctance_signal": dur < 10,
            },
            "facial_action_units": {},
            "head_pose": {},
            "gaze": {},
            "expression_dynamics": {"label": "unknown"},
            "facial_activity": {"label": "unknown"},
            "fallback": True,
        }

    def _maybe_delete_video(self, video: EmaVideo, features: dict[str, Any]) -> None:
        if video.skip or not self.delete_video_after_extract or self.storage_mode == "research":
            return
        path = self._resolve_video_path(video)
        if path and path.exists():
            try:
                path.unlink()
                storage = features.get("storage")
                if storage is not None:
                    storage["raw_video_deleted"] = True
                    row = (
                        self.db.query(VideoFeature)
                        .filter(
                            VideoFeature.user_id == video.user_id,
                            VideoFeature.task_date == video.task_date,
                            VideoFeature.session_id == video.session_id,
                        )
                        .first()
                    )
                    if row:
                        row.features = features
                        self.db.commit()
            except OSError:
                logger.exception("failed to delete video file video_id=%s", video.id)

    # ------------------------------------------------------------------ context

    def _load_context(self, video: EmaVideo) -> dict[str, Any]:
        questionnaire = (
            self.db.query(EmaQuestion)
            .filter(
                EmaQuestion.user_id == video.user_id,
                EmaQuestion.task_date == video.task_date,
                EmaQuestion.session_id == video.session_id,
            )
            .first()
        )
        questions_feature = (
            self.db.query(QuestionsFeature)
            .filter(
                QuestionsFeature.user_id == video.user_id,
                QuestionsFeature.task_date == video.task_date,
                QuestionsFeature.session_id == video.session_id,
                QuestionsFeature.status == "done",
            )
            .first()
        )
        voice_feature = (
            self.db.query(VoiceFeature)
            .filter(
                VoiceFeature.user_id == video.user_id,
                VoiceFeature.task_date == video.task_date,
                VoiceFeature.session_id == video.session_id,
                VoiceFeature.status == "done",
            )
            .first()
        )
        text_feature = (
            self.db.query(TextFeature)
            .filter(
                TextFeature.user_id == video.user_id,
                TextFeature.task_date == video.task_date,
                TextFeature.session_id == video.session_id,
                TextFeature.status == "done",
            )
            .first()
        )
        diary = (
            self.db.query(EmaDiary)
            .filter(
                EmaDiary.user_id == video.user_id,
                EmaDiary.task_date == video.task_date,
                EmaDiary.session_id == video.session_id,
            )
            .first()
        )
        baseline = (
            self.db.query(BaselineProfile).filter(BaselineProfile.user_id == video.user_id).first()
        )
        return {
            "questionnaire": questionnaire,
            "questions_feature": questions_feature,
            "voice_feature": voice_feature,
            "text_feature": text_feature,
            "diary": diary,
            "baseline": baseline,
        }

    def _user_historical_baseline(self, user_id: int, current_video_id: int) -> dict[str, Any]:
        rows = (
            self.db.query(VideoFeature)
            .filter(VideoFeature.user_id == user_id, VideoFeature.status == "done")
            .order_by(VideoFeature.id.desc())
            .limit(12)
            .all()
        )
        activity_scores: list[float] = []
        face_ratios: list[float] = []
        for row in rows:
            if row.submission_id == current_video_id:
                continue
            feat = row.features or {}
            if feat.get("skip"):
                continue
            visual = feat.get("visual") or {}
            act = (visual.get("facial_activity") or {}).get("score")
            fr = visual.get("face_visible_ratio")
            if act is not None:
                activity_scores.append(float(act))
            if fr is not None:
                face_ratios.append(float(fr))
        return {
            "sample_count": len(activity_scores),
            "avg_facial_activity": round(sum(activity_scores) / len(activity_scores), 4)
            if activity_scores
            else None,
            "avg_face_visible_ratio": round(sum(face_ratios) / len(face_ratios), 4) if face_ratios else None,
        }

    def _build_context_enrichment(
        self,
        context: dict[str, Any],
        visual: dict[str, Any],
        user_baseline: dict[str, Any],
    ) -> dict[str, Any]:
        q = context.get("questionnaire")
        q_data = None
        if q:
            q_data = {
                "mood": q.mood,
                "stress": q.stress,
                "anxiety": q.anxiety,
                "lonely": q.lonely,
                "negative": q.negative,
            }

        voice_summary = None
        vf = context.get("voice_feature")
        if vf and vf.features:
            comp = vf.features.get("composite_signals") or {}
            voice_summary = {
                "flat_affect": comp.get("flat_affect"),
                "depressed_speech_pattern": comp.get("depressed_speech_pattern"),
            }

        multimodal = self._video_voice_consistency(visual, vf)
        activity_dev = self._activity_deviation(visual, user_baseline)

        return {
            "questionnaire": q_data,
            "voice_features": voice_summary,
            "video_voice_consistency": multimodal,
            "facial_activity_deviation_from_user": activity_dev,
        }

    @staticmethod
    def _video_voice_consistency(visual: dict[str, Any], voice_feature: VoiceFeature | None) -> float | None:
        if not voice_feature or not voice_feature.features or voice_feature.features.get("skip"):
            return None
        vf = voice_feature.features
        mono = (vf.get("acoustic") or {}).get("monotony") or {}
        voice_flat = (mono.get("score") or 0) >= 0.6
        expr = visual.get("expression_dynamics") or {}
        video_flat = expr.get("label") == "flat"
        activity = (visual.get("facial_activity") or {}).get("label") == "sluggish"
        voice_distress = (vf.get("composite_signals") or {}).get("elevated_distress", False)
        video_distress = (
            (visual.get("gaze") or {}).get("frequent_avoidance")
            or (visual.get("head_pose") or {}).get("label_down")
            or (visual.get("completion") or {}).get("reluctance_signal")
        )
        distress_match = voice_distress == bool(video_distress or video_flat)
        flat_match = voice_flat == video_flat or (voice_flat and activity)
        score = 0.5 * float(distress_match) + 0.5 * float(flat_match)
        return round(score, 4)

    @staticmethod
    def _activity_deviation(visual: dict[str, Any], user_baseline: dict[str, Any]) -> float | None:
        current = (visual.get("facial_activity") or {}).get("score")
        avg = user_baseline.get("avg_facial_activity")
        if current is None or avg is None:
            return None
        return round(float(current) - float(avg), 4)

    def _build_composite_signals(
        self,
        visual: dict[str, Any],
        context: dict[str, Any],
        enrichment: dict[str, Any],
        user_baseline: dict[str, Any],
    ) -> dict[str, Any]:
        reasons: list[str] = []
        completion = visual.get("completion") or {}
        gaze = visual.get("gaze") or {}
        head = visual.get("head_pose") or {}
        expr = visual.get("expression_dynamics") or {}
        activity = visual.get("facial_activity") or {}
        fau = visual.get("facial_action_units") or {}

        reluctance = completion.get("reluctance_signal", False)
        avoidance = gaze.get("frequent_avoidance", False)
        head_down = head.get("label_down", False)
        flat_affect = expr.get("label") == "flat" or activity.get("label") == "sluggish"
        low_smile = (fau.get("smile") or {}).get("label") != "elevated"

        if reluctance:
            reasons.append("视频完成率低或露脸比例低，可能存在回避录制行为")
        if avoidance:
            reasons.append("眼神/面部频繁偏离镜头")
        if head_down:
            reasons.append("头部长时间偏低")
        if flat_affect:
            reasons.append("表情变化幅度小或面部活动偏迟滞")

        q = context.get("questionnaire")
        if q and q.mood <= 4 and (flat_affect or reluctance):
            reasons.append("问卷低情绪与视频回避/迟滞一致")
        if q and q.mood >= 7 and (reluctance or avoidance):
            reasons.append("问卷情绪较好但视频呈现回避信号，建议复核")

        deviation = enrichment.get("facial_activity_deviation_from_user")
        if deviation is not None and deviation <= -0.25:
            reasons.append("面部活动量相对个人基线明显偏低")

        consistency = enrichment.get("video_voice_consistency")
        if consistency is not None and consistency >= 0.75 and flat_affect:
            reasons.append("视频与语音均呈现情感平淡/迟滞，多模态一致")

        baseline = context.get("baseline")
        if baseline and baseline.self_harm in ("是", "有") and (reluctance or avoidance):
            reasons.append("基线自伤风险与视频回避同时出现")

        depressed_pattern = flat_affect and (head_down or low_smile) and (avoidance or reluctance)
        elevated = bool(depressed_pattern or len(reasons) >= 2)

        return {
            "elevated_distress": elevated,
            "depressed_expression_pattern": depressed_pattern,
            "reluctance_to_show_face": reluctance,
            "gaze_avoidance": avoidance,
            "flat_affect": flat_affect,
            "reasons": reasons,
        }

    def _storage_info(self, video: EmaVideo, path: Path | None, decode_ok: bool) -> dict[str, Any]:
        has_consent = user_has_consent(self.db, video.user_id)
        retain_raw = self.storage_mode == "research" and has_consent
        return {
            "mode": self.storage_mode,
            "raw_video_retained": retain_raw and path is not None and path.exists(),
            "raw_video_path": str(path) if retain_raw and path else None,
            "decode_ok": decode_ok,
            "delete_after_extract": self.delete_video_after_extract and self.storage_mode != "research",
        }

    @staticmethod
    def _skipped_features(video: EmaVideo) -> dict[str, Any]:
        return {
            "video_id": video.id,
            "skip": True,
            "duration_sec": video.duration_sec,
            "visual": None,
            "completion": {
                "completion_score": 0.0,
                "reluctance_signal": True,
                "skipped": True,
            },
            "composite_signals": {
                "elevated_distress": False,
                "reluctance_to_show_face": True,
                "skipped": True,
                "reasons": ["用户跳过视频录制"],
            },
            "extracted_at": format_datetime(datetime.now()),
        }
