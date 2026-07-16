"""语音录音上传与存储服务."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmaVoice, User
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_task_date

settings = get_settings()
VOICE_MIN_SEC = 5
VOICE_MAX_SEC = 60
CHUNK_SIZE = 64 * 1024


def _safe_openid(openid: str) -> str:
    return re.sub(r"[^\w\-]", "_", openid)[:48]


def build_voice_filename(user: User, recorded_at: datetime) -> str:
    at_ms = datetime_to_ms(recorded_at) or 0
    return f"voice_{user.id}_{_safe_openid(user.openid)}_{at_ms}.aac"


def _to_response(record: EmaVoice, file_path: str | None = None) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record.openid,
        "session_id": record.session_id,
        "task_date": record.task_date,
        "recorded_at": format_datetime(record.recorded_at),
        "at": datetime_to_ms(record.recorded_at),
        "duration_sec": record.duration_sec,
        "skip": record.skip,
        "file_name": record.file_name,
        "file_path": file_path,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


async def save_voice_stream(upload: UploadFile, dest: Path) -> None:
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(CHUNK_SIZE)
            if not chunk:
                break
            out.write(chunk)


def submit_ema_voice_skip(
    db: Session,
    user: User,
    recorded_at: datetime | None = None,
    session_id: int = 1,
    task_date: str | None = None,
) -> dict[str, Any]:
    at = recorded_at or datetime.now()
    record = EmaVoice(
        user_id=user.id,
        openid=user.openid,
        session_id=session_id,
        task_date=parse_task_date({"task_date": task_date}, at),
        recorded_at=at,
        duration_sec=0,
        skip=True,
        file_name=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    from app.services.submission_service import finalize_ema_step

    daily_tasks = finalize_ema_step(
        db,
        user.id,
        "voice",
        record.task_date,
        record.session_id,
        at,
        {"skip": True},
    )
    voice_feature = _try_extract_voice_features(db, record)
    result = _to_response(record)
    result["daily_tasks"] = daily_tasks
    if voice_feature:
        result["voice_feature_id"] = voice_feature.id
        result["voice_feature_status"] = voice_feature.status
    return result


async def submit_ema_voice(
    db: Session,
    user: User,
    upload: UploadFile,
    duration_sec: int,
    recorded_at: datetime | None = None,
    session_id: int = 1,
    task_date: str | None = None,
) -> dict[str, Any]:
    if duration_sec < VOICE_MIN_SEC or duration_sec > VOICE_MAX_SEC:
        raise ValueError(f"录音时长须在 {VOICE_MIN_SEC}-{VOICE_MAX_SEC} 秒之间")

    if not upload.filename and not upload.content_type:
        raise ValueError("未收到录音文件")

    at = recorded_at or datetime.now()
    file_name = build_voice_filename(user, at)
    files_dir = settings.voice_files_path
    dest_path = files_dir / file_name

    await save_voice_stream(upload, dest_path)
    if dest_path.stat().st_size == 0:
        dest_path.unlink(missing_ok=True)
        raise ValueError("录音文件为空")

    record = EmaVoice(
        user_id=user.id,
        openid=user.openid,
        session_id=session_id,
        task_date=parse_task_date({"task_date": task_date}, at),
        recorded_at=at,
        duration_sec=duration_sec,
        skip=False,
        file_name=file_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    from app.services.submission_service import finalize_ema_step

    daily_tasks = finalize_ema_step(
        db,
        user.id,
        "voice",
        record.task_date,
        record.session_id,
        record.recorded_at,
        {
            "duration": duration_sec,
            "skip": False,
            "file_name": file_name,
        },
    )
    voice_feature = _try_extract_voice_features(db, record)
    result = _to_response(record, str(dest_path))
    result["daily_tasks"] = daily_tasks
    if voice_feature:
        result["voice_feature_id"] = voice_feature.id
        result["voice_feature_status"] = voice_feature.status
    return result


def _try_extract_voice_features(db: Session, record: EmaVoice):
    try:
        from app.services.analysis import extract_voice_features_from_voice_row

        return extract_voice_features_from_voice_row(db, record)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("语音特性提取失败 voice_id=%s", record.id)
        return None
