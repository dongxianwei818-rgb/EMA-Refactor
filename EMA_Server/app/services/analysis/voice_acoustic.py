"""声学特征计算（语速、停顿、音高、响度、单调性）。"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

FRAME_LENGTH = 2048
HOP_LENGTH = 512
MIN_PAUSE_SEC = 0.25
SILENCE_PERCENTILE = 25


def analyze_acoustic_waveform(y: np.ndarray, sr: int, duration_sec: float | None = None) -> dict[str, Any]:
    """从单声道波形提取声学特征。"""
    import librosa

    if y.size == 0:
        raise ValueError("音频为空")

    y = librosa.util.normalize(y)
    total_duration = duration_sec if duration_sec and duration_sec > 0 else float(len(y) / sr)

    rms = librosa.feature.rms(y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP_LENGTH)

    silence_threshold = float(np.percentile(rms, SILENCE_PERCENTILE))
    is_speech = rms >= silence_threshold
    speech_time = float(np.sum(is_speech) * HOP_LENGTH / sr)
    speech_ratio = round(speech_time / max(total_duration, 0.001), 4)

    pause_stats = _pause_stats(is_speech, frame_times, sr)
    onset_count = int(len(librosa.onset.onset_detect(y=y, sr=sr, units="time")))
    speech_rate = _speech_rate(onset_count, speech_time, total_duration)

    pitch_stats = _pitch_stats(y, sr)
    energy_stats = _energy_stats(rms, rms_db, is_speech)
    monotony = _voice_monotony(pitch_stats, energy_stats)

    return {
        "duration_sec": round(total_duration, 3),
        "sample_rate": sr,
        "speech_ratio": speech_ratio,
        "speech_time_sec": round(speech_time, 3),
        "speech_rate": speech_rate,
        "pause": pause_stats,
        "pitch": pitch_stats,
        "energy": energy_stats,
        "monotony": monotony,
    }


def _pause_stats(is_speech: np.ndarray, frame_times: np.ndarray, sr: int) -> dict[str, Any]:
    pauses: list[float] = []
    in_pause = False
    pause_start = 0.0
    for i, speaking in enumerate(is_speech):
        t = float(frame_times[i])
        if not speaking and not in_pause:
            in_pause = True
            pause_start = t
        elif speaking and in_pause:
            dur = t - pause_start
            if dur >= MIN_PAUSE_SEC:
                pauses.append(dur)
            in_pause = False
    if in_pause and len(frame_times):
        dur = float(frame_times[-1]) - pause_start
        if dur >= MIN_PAUSE_SEC:
            pauses.append(dur)

    total_pause = round(sum(pauses), 3)
    return {
        "count": len(pauses),
        "total_sec": total_pause,
        "mean_sec": round(total_pause / len(pauses), 3) if pauses else 0.0,
        "max_sec": round(max(pauses), 3) if pauses else 0.0,
        "pause_ratio": round(total_pause / max(float(frame_times[-1]) if len(frame_times) else 1.0, 0.001), 4),
    }


def _speech_rate(onset_count: int, speech_time: float, total_duration: float) -> dict[str, Any]:
    """语速代理： onset 密度 + 有效语音占比。"""
    active = speech_time if speech_time > 0 else total_duration
    onsets_per_min = round(onset_count / max(active / 60.0, 0.01), 2)
    # 中文口语粗略参考：约 3–6 syllables/sec → 180–360 syllables/min；onset 作音节代理
    normalized = round(min(onsets_per_min / 200.0, 1.5), 4)
    label = "normal"
    if normalized < 0.45:
        label = "slow"
    elif normalized > 0.85:
        label = "fast"
    return {
        "onset_count": onset_count,
        "onsets_per_minute": onsets_per_min,
        "normalized_rate": normalized,
        "label": label,
    }


def _pitch_stats(y: np.ndarray, sr: int) -> dict[str, Any]:
    import librosa

    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH,
    )
    valid = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    if valid.size == 0:
        return {
            "mean_hz": None,
            "std_hz": None,
            "range_hz": None,
            "variation_score": 0.0,
            "voiced_ratio": 0.0,
        }
    std_hz = float(np.std(valid))
    range_hz = float(np.ptp(valid))
    variation_score = round(min(std_hz / 50.0, 1.0), 4)
    voiced_ratio = round(float(valid.size) / max(float(f0.size), 1.0), 4)
    return {
        "mean_hz": round(float(np.mean(valid)), 2),
        "std_hz": round(std_hz, 2),
        "range_hz": round(range_hz, 2),
        "variation_score": variation_score,
        "voiced_ratio": voiced_ratio,
    }


def _energy_stats(rms: np.ndarray, rms_db: np.ndarray, is_speech: np.ndarray) -> dict[str, Any]:
    speech_rms = rms[is_speech] if np.any(is_speech) else rms
    speech_db = rms_db[is_speech] if np.any(is_speech) else rms_db
    cv = float(np.std(speech_rms) / max(float(np.mean(speech_rms)), 1e-6))
    return {
        "mean_rms": round(float(np.mean(speech_rms)), 6),
        "mean_db": round(float(np.mean(speech_db)), 2),
        "max_db": round(float(np.max(speech_db)), 2),
        "dynamic_range_db": round(float(np.ptp(speech_db)), 2),
        "coefficient_of_variation": round(cv, 4),
    }


def _voice_monotony(pitch: dict[str, Any], energy: dict[str, Any]) -> dict[str, Any]:
    pitch_var = pitch.get("variation_score") or 0.0
    energy_cv = energy.get("coefficient_of_variation") or 0.0
    energy_flat = max(0.0, 1.0 - min(energy_cv / 0.5, 1.0))
    pitch_flat = max(0.0, 1.0 - pitch_var)
    score = round(min(1.0, pitch_flat * 0.6 + energy_flat * 0.4), 4)
    label = "normal"
    if score >= 0.65:
        label = "monotonous"
    elif score <= 0.35:
        label = "expressive"
    return {
        "score": score,
        "label": label,
        "pitch_flatness": round(pitch_flat, 4),
        "energy_flatness": round(energy_flat, 4),
    }


def load_mono_audio(path: Path) -> tuple[np.ndarray, int]:
    """
    加载单声道浮点波形。

    微信小程序录音为 AAC；libsndfile / soundfile 不支持 AAC，优先用 PyAV 解码。
    """
    suffix = path.suffix.lower()
    if suffix in {".wav", ".flac", ".ogg"}:
        return _load_with_librosa(path)
    if suffix in {".aac", ".m4a", ".mp4", ".mp3", ".webm"}:
        try:
            return _load_with_pyav(path)
        except Exception:
            logger.debug("PyAV decode failed for %s, trying ffmpeg", path, exc_info=True)
            return _load_with_ffmpeg(path)
    try:
        return _load_with_librosa(path)
    except Exception:
        logger.debug("librosa decode failed for %s, trying PyAV", path, exc_info=True)
        return _load_with_pyav(path)


def _load_with_librosa(path: Path) -> tuple[np.ndarray, int]:
    import librosa

    y, sr = librosa.load(str(path), sr=None, mono=True)
    return y.astype(np.float32), int(sr)


def _load_with_pyav(path: Path) -> tuple[np.ndarray, int]:
    import av

    container = av.open(str(path))
    if not container.streams.audio:
        raise ValueError(f"no audio stream in {path}")

    chunks: list[np.ndarray] = []
    sample_rate: int | None = None
    for frame in container.decode(audio=0):
        arr = frame.to_ndarray()
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        chunks.append(arr.astype(np.float32))
        sample_rate = int(frame.rate)

    if not chunks or sample_rate is None:
        raise ValueError(f"empty audio in {path}")

    y = np.concatenate(chunks)
    peak = float(np.max(np.abs(y)))
    if peak > 0:
        y = y / peak
    return y, sample_rate


def _load_with_ffmpeg(path: Path, target_sr: int = 22050) -> tuple[np.ndarray, int]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found in PATH")

    cmd = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        str(target_sr),
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    y = np.frombuffer(proc.stdout, dtype=np.float32)
    if y.size == 0:
        raise ValueError(f"ffmpeg produced empty audio for {path}")
    return y, target_sr
