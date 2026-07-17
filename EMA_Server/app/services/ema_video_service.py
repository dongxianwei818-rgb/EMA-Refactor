"""视频录制上传与存储服务."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import models_for
from app.services.datetime_fields import datetime_to_ms, format_datetime
from app.services.session_fields import parse_task_date
from app.services.analysis.async_extract import schedule_video_features
from app.services.user_identity import (
    client_type_from_user,
    identity_row_kwargs,
    record_principal,
    user_principal,
)

settings = get_settings()
VIDEO_MIN_SEC = 5
VIDEO_MAX_SEC = 60
CHUNK_SIZE = 64 * 1024


def _safe_token(token: str) -> str:
    return re.sub(r"[^\w\-]", "_", token)[:48]


def build_video_filename(user, recorded_at: datetime) -> str:
    at_ms = datetime_to_ms(recorded_at) or 0
    return f"video_{user.id}_{_safe_token(user_principal(user))}_{at_ms}.mp4"


def _to_response(record, file_path: str | None = None) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record_principal(record),
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


async def save_video_stream(upload: UploadFile, dest: Path) -> None:
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(CHUNK_SIZE)
            if not chunk:
                break
            out.write(chunk)


def submit_ema_video_skip(
    db: Session,
    user,
    recorded_at: datetime | None = None,
    session_id: int = 1,
    task_date: str | None = None,
) -> dict[str, Any]:
    at = recorded_at or datetime.now()
    EmaVideo = models_for(user=user).EmaVideo
    record = EmaVideo(
        user_id=user.id,
        **identity_row_kwargs(user),
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
        "video",
        record.task_date,
        record.session_id,
        at,
        {"skip": True},
        user=user,
    )
    schedule_video_features(client_type_from_user(user), record.id)
    result = _to_response(record)
    result["daily_tasks"] = daily_tasks
    result["video_feature_status"] = "pending"
    return result


async def submit_ema_video(
    db: Session,
    user,
    upload: UploadFile,
    duration_sec: int,
    recorded_at: datetime | None = None,
    session_id: int = 1,
    task_date: str | None = None,
) -> dict[str, Any]:
    if duration_sec < VIDEO_MIN_SEC or duration_sec > VIDEO_MAX_SEC:
        raise ValueError(f"视频时长须在 {VIDEO_MIN_SEC}-{VIDEO_MAX_SEC} 秒之间")

    if not upload.filename and not upload.content_type:
        raise ValueError("未收到视频文件")

    at = recorded_at or datetime.now()
    file_name = build_video_filename(user, at)
    files_dir = settings.video_files_path
    dest_path = files_dir / file_name

    await save_video_stream(upload, dest_path)
    if dest_path.stat().st_size == 0:
        dest_path.unlink(missing_ok=True)
        raise ValueError("视频文件为空")

    EmaVideo = models_for(user=user).EmaVideo
    record = EmaVideo(
        user_id=user.id,
        **identity_row_kwargs(user),
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
        "video",
        record.task_date,
        record.session_id,
        record.recorded_at,
        {
            "duration": duration_sec,
            "skip": False,
            "file_name": file_name,
        },
        user=user,
    )
    schedule_video_features(client_type_from_user(user), record.id)
    result = _to_response(record, str(dest_path))
    result["daily_tasks"] = daily_tasks
    result["video_feature_status"] = "pending"
    return result
