"""EMA step submission: submissions table + structured ema_* tables."""

from datetime import datetime
from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models import models_for
from app.client_types import set_current_client_type
from app.services.datetime_fields import parse_client_at
from app.services.ema_diary_service import submit_ema_diary
from app.services.ema_questionnaire_service import submit_ema_questionnaire
from app.services.ema_step_service import submit_ema_step as save_ema_step_record
from app.services.ema_video_service import submit_ema_video_skip
from app.services.daily_task_service import apply_step_to_daily_tasks
from app.services.ema_voice_service import submit_ema_voice_skip
from app.services.session_fields import parse_session_id, parse_task_date
from app.services.user_identity import client_type_from_user

VALID_SUBMISSION_TYPES = frozenset({"questionnaire", "diary", "voice", "video", "steps"})


def upsert_submission(
    db: Session,
    user_id: int,
    submission_type: str,
    task_date: str,
    session_id: int,
    client_at: datetime,
    payload: dict[str, Any] | None = None,
    *,
    commit: bool = True,
    user=None,
) -> None:
    Submission = models_for(user=user).Submission
    stmt = mysql_insert(Submission).values(
        user_id=user_id,
        submission_type=submission_type,
        task_date=task_date,
        session_id=session_id,
        payload=payload or {},
        client_at=client_at,
    )
    stmt = stmt.on_duplicate_key_update(payload=stmt.inserted.payload)
    db.execute(stmt)
    if commit:
        db.commit()


def record_submission_for_step(
    db: Session,
    user_id: int,
    submission_type: str,
    task_date: str,
    session_id: int,
    client_at: datetime,
    payload: dict[str, Any] | None = None,
    *,
    user=None,
) -> None:
    upsert_submission(
        db,
        user_id,
        submission_type,
        task_date,
        session_id,
        client_at,
        payload,
        commit=True,
        user=user,
    )


def finalize_ema_step(
    db: Session,
    user_id: int,
    step_type: str,
    task_date: str,
    session_id: int,
    client_at: datetime,
    payload: dict[str, Any] | None = None,
    *,
    user=None,
) -> dict[str, Any]:
    upsert_submission(
        db,
        user_id,
        step_type,
        task_date,
        session_id,
        client_at,
        payload,
        commit=False,
        user=user,
    )
    return apply_step_to_daily_tasks(
        db, user_id, task_date, session_id, step_type, payload, client_at, user=user
    )


def submit_ema_submission(db: Session, user, body: dict[str, Any]) -> dict[str, Any]:
    set_current_client_type(client_type_from_user(user))
    step_type = (body.get("type") or "").strip()
    if step_type not in VALID_SUBMISSION_TYPES:
        raise ValueError(f"type 须为 {', '.join(sorted(VALID_SUBMISSION_TYPES))}")

    payload = body.get("payload") or {}
    client_at = parse_client_at(body)
    session_id = parse_session_id(body)
    task_date = parse_task_date(body, client_at)
    meta = {
        "session_id": session_id,
        "task_date": task_date,
        "client_at": client_at,
    }

    if step_type == "questionnaire":
        answers = payload.get("answers") or {}
        if not answers:
            raise ValueError("payload.answers 不能为空")
        structured = submit_ema_questionnaire(
            db,
            user,
            {**answers, **meta, "answered_at": client_at},
        )
        sub_payload = payload
    elif step_type == "diary":
        structured = submit_ema_diary(
            db,
            user,
            {
                "text": payload.get("text"),
                "length": payload.get("length"),
                **meta,
                "written_at": client_at,
            },
        )
        sub_payload = payload
    elif step_type == "steps":
        structured = save_ema_step_record(
            db,
            user,
            {
                "steps": payload.get("steps"),
                "source": payload.get("source") or "manual",
                **meta,
                "recorded_at": client_at,
            },
        )
        sub_payload = payload
    elif step_type == "voice":
        if not payload.get("skip"):
            raise ValueError("语音文件请使用 /ema/voice/submit-log 上传；跳过请传 payload.skip=true")
        structured = submit_ema_voice_skip(db, user, client_at, session_id, task_date)
        sub_payload = {}
        daily_tasks = structured.pop("daily_tasks", None)
        return {
            **structured,
            "submission_type": step_type,
            "submission_payload": sub_payload,
            "daily_tasks": daily_tasks,
        }
    elif step_type == "video":
        if not payload.get("skip"):
            raise ValueError("视频文件请使用 /ema/video/submit-log 上传；跳过请传 payload.skip=true")
        structured = submit_ema_video_skip(db, user, client_at, session_id, task_date)
        sub_payload = {}
        daily_tasks = structured.pop("daily_tasks", None)
        return {
            **structured,
            "submission_type": step_type,
            "submission_payload": sub_payload,
            "daily_tasks": daily_tasks,
        }
    else:
        raise ValueError(f"不支持的 type: {step_type}")

    daily_tasks = finalize_ema_step(
        db, user.id, step_type, task_date, session_id, client_at, sub_payload, user=user
    )

    return {
        **structured,
        "submission_type": step_type,
        "submission_payload": sub_payload,
        "daily_tasks": daily_tasks,
    }
