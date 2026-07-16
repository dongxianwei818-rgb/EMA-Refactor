"""视频帧面部视觉特征（FAU 代理、头姿、眼神、表情活跃度）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# MediaPipe Face Mesh 关键点索引（简化 FAU / 头姿代理）
IDX = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_outer": 33,
    "right_eye_outer": 263,
    "left_mouth": 61,
    "right_mouth": 291,
    "upper_lip": 13,
    "lower_lip": 14,
    "left_brow": 107,
    "right_brow": 336,
    "left_iris": 468,
    "right_iris": 473,
}


@dataclass
class FrameMetrics:
    face_detected: bool = False
    smile_score: float = 0.0
    frown_score: float = 0.0
    eye_openness: float = 0.0
    eye_movement: float = 0.0
    head_pitch: float = 0.0
    head_yaw: float = 0.0
    head_roll: float = 0.0
    gaze_offset: float = 0.0
    face_center_x: float = 0.5
    face_scale: float = 0.0
    landmark_vector: list[float] = field(default_factory=list)


def analyze_video_file(
    path: str,
    expected_duration_sec: float | None = None,
    sample_fps: float = 2.0,
    max_frames: int = 120,
    backend: str = "mediapipe",
) -> dict[str, Any]:
    """从 MP4 采样帧并提取六类视频视觉特征。"""
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    video_duration = expected_duration_sec
    if video_duration is None or video_duration <= 0:
        video_duration = frame_count / native_fps if frame_count and native_fps else 0.0

    step = max(int(round(native_fps / max(sample_fps, 0.5))), 1)
    frames_metrics: list[FrameMetrics] = []
    frame_idx = 0
    sampled = 0

    analyzer = _create_analyzer(backend)
    prev_lm: np.ndarray | None = None

    while sampled < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            break
        metrics = analyzer.analyze_frame(frame, prev_lm)
        if metrics.landmark_vector:
            lm = np.array(metrics.landmark_vector, dtype=float)
            if prev_lm is not None and prev_lm.shape == lm.shape:
                metrics.eye_movement = float(np.mean(np.abs(lm - prev_lm)))
            prev_lm = lm
        frames_metrics.append(metrics)
        sampled += 1
        frame_idx += step

    cap.release()

    if not frames_metrics:
        raise ValueError("视频无有效帧")

    return _aggregate_metrics(frames_metrics, float(video_duration), sampled)


def _create_analyzer(backend: str) -> "_FrameAnalyzer":
    if backend == "mediapipe":
        try:
            return _MediaPipeAnalyzer()
        except Exception:
            pass
    return _OpenCvAnalyzer()


class _FrameAnalyzer:
    def analyze_frame(self, frame: np.ndarray, prev_lm: np.ndarray | None) -> FrameMetrics:
        raise NotImplementedError


class _MediaPipeAnalyzer(_FrameAnalyzer):
    def __init__(self) -> None:
        import mediapipe as mp

        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def analyze_frame(self, frame: np.ndarray, prev_lm: np.ndarray | None) -> FrameMetrics:
        import cv2

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        result = self._mesh.process(rgb)
        if not result.multi_face_landmarks:
            return FrameMetrics(face_detected=False)

        lm = result.multi_face_landmarks[0].landmark
        pts = {k: _lm_xy(lm, idx, w, h) for k, idx in IDX.items()}

        mouth_w = _dist(pts["left_mouth"], pts["right_mouth"])
        face_w = _dist(pts["left_eye_outer"], pts["right_eye_outer"]) * 2.5 or 1.0
        mouth_h = _dist(pts["upper_lip"], pts["lower_lip"])
        smile_score = round(min(1.0, (mouth_w / face_w) * 1.2 + mouth_h / face_w * 0.5), 4)

        brow_eye_l = _dist(pts["left_brow"], pts["left_eye_outer"])
        brow_eye_r = _dist(pts["right_brow"], pts["right_eye_outer"])
        frown_score = round(max(0.0, 1.0 - (brow_eye_l + brow_eye_r) / (face_w * 0.35)), 4)

        eye_openness = round((mouth_h / max(face_w * 0.08, 1e-3)) * 0.5, 4)

        pitch = _head_pitch(pts)
        yaw = _head_yaw(pts, w)
        roll = _head_roll(pts)

        nose = pts["nose_tip"]
        gaze_offset = round(abs(nose[0] / w - 0.5) + abs(yaw) * 0.5, 4)
        face_scale = round(face_w / w, 4)

        vector = []
        for idx in sorted(IDX.values()):
            x, y = _lm_xy(lm, idx, w, h)
            vector.extend([x / w, y / h])

        return FrameMetrics(
            face_detected=True,
            smile_score=smile_score,
            frown_score=frown_score,
            eye_openness=eye_openness,
            head_pitch=pitch,
            head_yaw=yaw,
            head_roll=roll,
            gaze_offset=gaze_offset,
            face_center_x=round(nose[0] / w, 4),
            face_scale=face_scale,
            landmark_vector=vector,
        )


class _OpenCvAnalyzer(_FrameAnalyzer):
    def __init__(self) -> None:
        import cv2

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)

    def analyze_frame(self, frame: np.ndarray, prev_lm: np.ndarray | None) -> FrameMetrics:
        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        faces = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(48, 48))
        if len(faces) == 0:
            return FrameMetrics(face_detected=False)

        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        cx = (x + fw / 2) / w
        gaze_offset = round(abs(cx - 0.5) + abs(fw / w - 0.35), 4)
        return FrameMetrics(
            face_detected=True,
            smile_score=0.0,
            frown_score=0.0,
            gaze_offset=gaze_offset,
            face_center_x=round(cx, 4),
            face_scale=round(fw / w, 4),
            head_yaw=round((cx - 0.5) * 2, 4),
            landmark_vector=[cx, fw / w, fh / h],
        )


def _aggregate_metrics(frames: list[FrameMetrics], duration_sec: float, sampled: int) -> dict[str, Any]:
    detected = [f for f in frames if f.face_detected]
    face_ratio = round(len(detected) / len(frames), 4)
    duration_completion = round(min(duration_sec / 60.0, 1.0), 4) if duration_sec else None

    if not detected:
        return {
            "frames_sampled": sampled,
            "duration_sec": round(duration_sec, 3),
            "face_visible_ratio": face_ratio,
            "completion": _completion_block(duration_sec, face_ratio, False),
            "facial_action_units": _empty_fau(),
            "head_pose": _empty_head_pose(),
            "gaze": {"avoidance_score": 1.0, "frequent_avoidance": True},
            "expression_dynamics": _empty_dynamics(),
            "facial_activity": {"score": 0.0, "label": "no_face"},
            "backend": "none_detected",
        }

    smiles = [f.smile_score for f in detected]
    frowns = [f.frown_score for f in detected]
    eye_mov = [f.eye_movement for f in detected if f.eye_movement > 0]
    pitches = [f.head_pitch for f in detected]
    yaws = [f.head_yaw for f in detected]
    rolls = [f.head_roll for f in detected]
    gaze_offs = [f.gaze_offset for f in detected]

    lm_matrix = np.array([f.landmark_vector for f in detected if f.landmark_vector], dtype=float)
    expr_var = float(np.mean(np.std(lm_matrix, axis=0))) if lm_matrix.size else 0.0
    activity = float(np.mean(eye_mov)) if eye_mov else expr_var

    head_down_ratio = round(sum(1 for p in pitches if p > 0.15) / len(pitches), 4)
    head_turn_ratio = round(sum(1 for y in yaws if abs(y) > 0.2) / len(yaws), 4)
    head_stability = round(1.0 - min(np.std(pitches) + np.std(yaws) + np.std(rolls), 1.0), 4)

    avoidance = round(min(1.0, np.mean(gaze_offs) + (1.0 - face_ratio) * 0.5), 4)

    return {
        "frames_sampled": sampled,
        "duration_sec": round(duration_sec, 3),
        "face_visible_ratio": face_ratio,
        "completion": _completion_block(duration_sec, face_ratio, True),
        "facial_action_units": {
            "smile": _stat_block(smiles, "elevated" if np.mean(smiles) > 0.45 else "neutral"),
            "frown": _stat_block(frowns, "elevated" if np.mean(frowns) > 0.35 else "neutral"),
            "eye_movement": {
                "mean": round(float(np.mean(eye_mov)), 4) if eye_mov else 0.0,
                "label": "active" if eye_mov and np.mean(eye_mov) > 0.008 else "low",
            },
        },
        "head_pose": {
            "pitch_mean": round(float(np.mean(pitches)), 4),
            "yaw_mean": round(float(np.mean(yaws)), 4),
            "roll_mean": round(float(np.mean(rolls)), 4),
            "head_down_ratio": head_down_ratio,
            "head_turn_ratio": head_turn_ratio,
            "stability_score": head_stability,
            "label_down": bool(head_down_ratio >= 0.4),
        },
        "gaze": {
            "offset_mean": round(float(np.mean(gaze_offs)), 4),
            "avoidance_score": avoidance,
            "frequent_avoidance": bool(avoidance >= 0.45 or face_ratio < 0.5),
        },
        "expression_dynamics": {
            "landmark_variance": round(expr_var, 6),
            "expression_range_score": round(min(expr_var * 50, 1.0), 4),
            "label": _expressiveness_label(expr_var),
        },
        "facial_activity": {
            "score": round(min(activity * 80, 1.0), 4),
            "raw_motion": round(activity, 6),
            "label": _activity_label(activity),
        },
        "backend": "mediapipe" if isinstance(detected[0].landmark_vector, list) and len(detected[0].landmark_vector) > 10 else "opencv",
    }


def _lm_xy(landmarks: Any, index: int, w: int, h: int) -> tuple[float, float]:
    pt = landmarks[index]
    return pt.x * w, pt.y * h


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def _head_pitch(pts: dict[str, tuple[float, float]]) -> float:
    nose, chin = pts["nose_tip"], pts["chin"]
    eye_mid_y = (pts["left_eye_outer"][1] + pts["right_eye_outer"][1]) / 2
    vertical = chin[1] - nose[1]
    norm = abs(chin[1] - eye_mid_y) or 1.0
    return round((vertical / norm) - 0.8, 4)


def _head_yaw(pts: dict[str, tuple[float, float]], width: int) -> float:
    left, right = pts["left_eye_outer"], pts["right_eye_outer"]
    nose = pts["nose_tip"]
    mid_x = (left[0] + right[0]) / 2
    return round((nose[0] - mid_x) / (width * 0.15), 4)


def _head_roll(pts: dict[str, tuple[float, float]]) -> float:
    left, right = pts["left_eye_outer"], pts["right_eye_outer"]
    dy = right[1] - left[1]
    dx = right[0] - left[0] or 1.0
    return round(float(np.arctan2(dy, dx)), 4)


def _stat_block(values: list[float], label: str) -> dict[str, Any]:
    return {
        "mean": round(float(np.mean(values)), 4),
        "max": round(float(np.max(values)), 4),
        "label": label,
    }


def _completion_block(duration_sec: float, face_ratio: float, has_face: bool) -> dict[str, Any]:
    dur_score = min(duration_sec / 60.0, 1.0) if duration_sec else 0.0
    completion_score = round(dur_score * 0.4 + face_ratio * 0.6, 4)
    return {
        "duration_sec": round(duration_sec, 3),
        "duration_ratio": round(dur_score, 4),
        "face_visible_ratio": face_ratio,
        "completion_score": completion_score,
        "reluctance_signal": bool(not has_face or face_ratio < 0.35 or duration_sec < 10),
    }


def _expressiveness_label(variance: float) -> str:
    if variance < 0.004:
        return "flat"
    if variance > 0.015:
        return "expressive"
    return "moderate"


def _activity_label(activity: float) -> str:
    if activity < 0.004:
        return "sluggish"
    if activity > 0.012:
        return "active"
    return "normal"


def _empty_fau() -> dict[str, Any]:
    return {"smile": None, "frown": None, "eye_movement": None}


def _empty_head_pose() -> dict[str, Any]:
    return {"pitch_mean": None, "yaw_mean": None, "stability_score": None}


def _empty_dynamics() -> dict[str, Any]:
    return {"landmark_variance": None, "expression_range_score": None, "label": "unknown"}
