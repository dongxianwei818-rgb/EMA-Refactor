"""Check-in session lifecycle."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.analysis.async_extract import schedule_behavior_features
from app.services.daily_task_service import init_daily_task_snapshot
from app.services.datetime_fields import datetime_to_ms, format_datetime, ms_to_datetime
from app.services.user_identity import client_type_from_user


def _upsert_checkin_day_state(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
    state_data: dict[str, Any],
) -> None:
    m = models_for(db=db)
    CheckinDayState = m.CheckinDayState
    now = datetime.now()
    row = (
        db.query(CheckinDayState)
        .filter(CheckinDayState.user_id == user_id, CheckinDayState.task_date == task_date)
        .first()
    )
    if row:
        row.session_id = session_id
        row.state_data = state_data
        row.updated_at = now
    else:
        db.add(
            CheckinDayState(
                user_id=user_id,
                task_date=task_date,
                session_id=session_id,
                state_data=state_data,
                updated_at=now,
            )
        )


def start_checkin_session(
    db: Session,
    user,
    *,
    task_date: str,
    session_id: int,
    started_at: datetime,
    checkin_day: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if session_id < 1:
        raise ValueError("session_id 必须 >= 1")
    if not task_date:
        raise ValueError("task_date 不能为空")

    m = models_for(user=user, db=db)
    CheckinSession = m.CheckinSession
    row = (
        db.query(CheckinSession)
        .filter(
            CheckinSession.user_id == user.id,
            CheckinSession.task_date == task_date,
            CheckinSession.session_id == session_id,
        )
        .first()
    )
    if row:
        row.started_at = started_at
        if row.completed_at is not None:
            row.completed_at = None
    else:
        db.add(
            CheckinSession(
                user_id=user.id,
                task_date=task_date,
                session_id=session_id,
                started_at=started_at,
                completed_at=None,
            )
        )
        init_daily_task_snapshot(db, user.id, task_date, session_id, started_at, commit=False)

    started_ms = datetime_to_ms(started_at)
    state_data = checkin_day or {
        "date": task_date,
        "sessionId": session_id,
        "sessions": [{"id": session_id, "startedAt": started_ms, "completedAt": None}],
    }
    _upsert_checkin_day_state(db, user.id, task_date, session_id, state_data)
    db.commit()

    return {
        "user_id": user.id,
        "task_date": task_date,
        "session_id": session_id,
        "started_at": format_datetime(started_at),
        "at": started_ms,
    }


def complete_checkin_session(
    db: Session,
    user,
    *,
    task_date: str,
    session_id: int,
    completed_at: datetime,
    checkin_day: dict[str, Any] | None = None,
) -> dict[str, Any]:
    m = models_for(user=user, db=db)
    CheckinSession = m.CheckinSession
    row = (
        db.query(CheckinSession)
        .filter(
            CheckinSession.user_id == user.id,
            CheckinSession.task_date == task_date,
            CheckinSession.session_id == session_id,
        )
        .first()
    )
    if not row:
        raise ValueError("打卡会话不存在，请先开始打卡")
    row.completed_at = completed_at

    if checkin_day:
        _upsert_checkin_day_state(db, user.id, task_date, session_id, checkin_day)
    db.commit()

    schedule_behavior_features(
        client_type_from_user(user), user.id, task_date, session_id
    )

    return {
        "user_id": user.id,
        "task_date": task_date,
        "session_id": session_id,
        "completed_at": format_datetime(completed_at),
        "at": datetime_to_ms(completed_at),
        "behavior_feature_status": "pending",
    }


def sync_checkin_sessions_from_state(
    db: Session,
    user_id: int,
    checkin_day: dict[str, Any] | None,
) -> int:
    if not checkin_day:
        return 0
    m = models_for(db=db)
    CheckinSession = m.CheckinSession
    now = datetime.now()
    task_date = checkin_day.get("date") or ""
    session_id = checkin_day.get("sessionId") or 1
    _upsert_checkin_day_state(db, user_id, task_date, session_id, checkin_day)

    sessions = checkin_day.get("sessions") or []
    for s in sessions:
        sid = s.get("id")
        if sid is None:
            continue
        started_at = ms_to_datetime(s.get("startedAt")) or now
        completed_raw = s.get("completedAt")
        completed_at = ms_to_datetime(completed_raw) if completed_raw else None
        row = (
            db.query(CheckinSession)
            .filter(
                CheckinSession.user_id == user_id,
                CheckinSession.task_date == task_date,
                CheckinSession.session_id == sid,
            )
            .first()
        )
        if row:
            row.started_at = started_at
            row.completed_at = completed_at
        else:
            db.add(
                CheckinSession(
                    user_id=user_id,
                    task_date=task_date,
                    session_id=sid,
                    started_at=started_at,
                    completed_at=completed_at,
                )
            )
    return 1
