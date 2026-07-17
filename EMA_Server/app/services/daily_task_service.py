"""Daily task snapshot read/write."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.datetime_fields import datetime_to_ms, format_datetime

DEFAULT_TASKS: dict[str, bool] = {
    "questionnaire": False,
    "diary": False,
    "voice": False,
    "video": False,
    "steps": False,
    "videoSkipped": False,
    "voiceSkipped": False,
}


def _normalize_tasks(tasks: dict[str, Any] | None) -> dict[str, bool]:
    merged = dict(DEFAULT_TASKS)
    if tasks:
        for key in DEFAULT_TASKS:
            if key in tasks:
                merged[key] = bool(tasks[key])
    return merged


def _build_step_patch(step_type: str, payload: dict[str, Any] | None = None) -> dict[str, bool]:
    payload = payload or {}
    if step_type == "questionnaire":
        return {"questionnaire": True}
    if step_type == "diary":
        return {"diary": True}
    if step_type == "steps":
        return {"steps": True}
    if step_type == "voice":
        if payload.get("skip"):
            return {"voice": True, "voiceSkipped": True}
        return {"voice": True, "voiceSkipped": False}
    if step_type == "video":
        if payload.get("skip"):
            return {"video": True, "videoSkipped": True}
        return {"video": True, "videoSkipped": False}
    raise ValueError(f"不支持的步骤类型: {step_type}")


def patch_daily_task_snapshot(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
    patch: dict[str, bool],
    updated_at: datetime | None = None,
    *,
    commit: bool = True,
    user=None,
) -> dict[str, Any]:
    if session_id < 1:
        raise ValueError("session_id 必须 >= 1")
    if not task_date:
        raise ValueError("task_date 不能为空")

    at = updated_at or datetime.now()
    DailyTaskSnapshot = models_for(user=user, db=db).DailyTaskSnapshot
    existing = (
        db.query(DailyTaskSnapshot)
        .filter(
            DailyTaskSnapshot.user_id == user_id,
            DailyTaskSnapshot.task_date == task_date,
            DailyTaskSnapshot.session_id == session_id,
        )
        .first()
    )
    if existing:
        tasks = _normalize_tasks(existing.tasks)
        tasks.update(patch)
        existing.tasks = tasks
        existing.updated_at = at
    else:
        tasks = _normalize_tasks(patch)
        db.add(
            DailyTaskSnapshot(
                user_id=user_id,
                task_date=task_date,
                session_id=session_id,
                tasks=tasks,
                updated_at=at,
            )
        )
    if commit:
        db.commit()
    return {
        "user_id": user_id,
        "task_date": task_date,
        "session_id": session_id,
        "tasks": tasks,
        "updated_at": format_datetime(at),
        "at": datetime_to_ms(at),
    }


def init_daily_task_snapshot(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
    updated_at: datetime | None = None,
    *,
    commit: bool = True,
    user=None,
) -> dict[str, Any]:
    at = updated_at or datetime.now()
    DailyTaskSnapshot = models_for(user=user, db=db).DailyTaskSnapshot
    existing = (
        db.query(DailyTaskSnapshot)
        .filter(
            DailyTaskSnapshot.user_id == user_id,
            DailyTaskSnapshot.task_date == task_date,
            DailyTaskSnapshot.session_id == session_id,
        )
        .first()
    )
    if existing:
        return {
            "user_id": user_id,
            "task_date": task_date,
            "session_id": session_id,
            "tasks": _normalize_tasks(existing.tasks),
            "updated_at": format_datetime(existing.updated_at),
            "at": datetime_to_ms(existing.updated_at),
        }
    tasks = dict(DEFAULT_TASKS)
    db.add(
        DailyTaskSnapshot(
            user_id=user_id,
            task_date=task_date,
            session_id=session_id,
            tasks=tasks,
            updated_at=at,
        )
    )
    if commit:
        db.commit()
    return {
        "user_id": user_id,
        "task_date": task_date,
        "session_id": session_id,
        "tasks": tasks,
        "updated_at": format_datetime(at),
        "at": datetime_to_ms(at),
    }


def apply_step_to_daily_tasks(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
    step_type: str,
    payload: dict[str, Any] | None = None,
    updated_at: datetime | None = None,
    *,
    user=None,
) -> dict[str, Any]:
    patch = _build_step_patch(step_type, payload)
    return patch_daily_task_snapshot(
        db, user_id, task_date, session_id, patch, updated_at, commit=True, user=user
    )


def get_daily_task_snapshot(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
) -> dict[str, Any]:
    DailyTaskSnapshot = models_for(db=db).DailyTaskSnapshot
    row = (
        db.query(DailyTaskSnapshot)
        .filter(
            DailyTaskSnapshot.user_id == user_id,
            DailyTaskSnapshot.task_date == task_date,
            DailyTaskSnapshot.session_id == session_id,
        )
        .first()
    )
    if not row:
        return {
            "task_date": task_date,
            "session_id": session_id,
            "tasks": dict(DEFAULT_TASKS),
            "updated_at": None,
            "at": None,
            "hasSnapshot": False,
        }
    return {
        "task_date": row.task_date,
        "session_id": row.session_id,
        "tasks": _normalize_tasks(row.tasks),
        "updated_at": format_datetime(row.updated_at),
        "at": datetime_to_ms(row.updated_at),
        "hasSnapshot": True,
    }


def get_daily_tasks_for_user(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int,
) -> dict[str, Any]:
    snapshot = get_daily_task_snapshot(db, user_id, task_date, session_id)
    return {
        "task_date": snapshot["task_date"],
        "session_id": snapshot["session_id"],
        "tasks": snapshot["tasks"],
        "updated_at": snapshot["updated_at"],
        "at": snapshot["at"],
        "hasSnapshot": snapshot["hasSnapshot"],
        "daily_tasks": {task_date: snapshot["tasks"]},
    }


def upsert_daily_tasks_batch(
    db: Session,
    user_id: int,
    daily_tasks: dict,
    checkin_day: dict | None = None,
) -> int:
    from app.services.session_fields import parse_session_id

    count = 0
    now = datetime.now()
    checkin_date = (checkin_day or {}).get("date") or ""
    for task_date_key, tasks in (daily_tasks or {}).items():
        if isinstance(tasks, dict) and "tasks" in tasks:
            session_id = parse_session_id(tasks)
            task_payload = tasks.get("tasks") or {}
        else:
            session_id = parse_session_id(checkin_day) if task_date_key == checkin_date else 1
            task_payload = tasks if isinstance(tasks, dict) else {}
        patch_daily_task_snapshot(
            db,
            user_id,
            task_date_key,
            session_id,
            _normalize_tasks(task_payload),
            now,
            commit=False,
        )
        count += 1
    return count
