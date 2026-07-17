"""步数打卡提交服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.analysis.async_extract import schedule_step_features
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_session_id, parse_task_date
from app.services.user_identity import client_type_from_user, identity_row_kwargs, record_principal

ALLOWED_SOURCES = {"werun", "manual", "mock"}


def submit_ema_step(db: Session, user, body: dict[str, Any]) -> dict[str, Any]:
    steps = body.get("steps")
    if steps is None:
        raise ValueError("步数不能为空")
    steps = int(steps)
    if steps < 0:
        raise ValueError("步数不能为负数")

    source = (body.get("source") or "manual").strip().lower()
    if source not in ALLOWED_SOURCES:
        raise ValueError("source 须为 werun、manual 或 mock")

    recorded_at = body.get("recorded_at")
    if isinstance(recorded_at, datetime):
        at = recorded_at
    else:
        at = parse_client_at(body)

    EmaStep = models_for(user=user).EmaStep
    record = EmaStep(
        user_id=user.id,
        **identity_row_kwargs(user),
        session_id=parse_session_id(body),
        task_date=parse_task_date(body, at),
        recorded_at=at,
        steps=steps,
        source=source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    schedule_step_features(client_type_from_user(user), record.id)

    return {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record_principal(record),
        "session_id": record.session_id,
        "task_date": record.task_date,
        "recorded_at": format_datetime(record.recorded_at),
        "at": datetime_to_ms(record.recorded_at),
        "steps": record.steps,
        "source": record.source,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "step_feature_status": "pending",
    }
