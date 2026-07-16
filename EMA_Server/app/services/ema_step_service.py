"""步数打卡提交服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import EmaStep, User
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_session_id, parse_task_date

ALLOWED_SOURCES = {"werun", "manual", "mock"}


def submit_ema_step(db: Session, user: User, body: dict[str, Any]) -> dict[str, Any]:
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

    record = EmaStep(
        user_id=user.id,
        openid=user.openid,
        session_id=parse_session_id(body),
        task_date=parse_task_date(body, at),
        recorded_at=at,
        steps=steps,
        source=source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        from app.services.analysis import extract_step_features_from_step_row

        step_feature = extract_step_features_from_step_row(db, record)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("步数特性提取失败 step_id=%s", record.id)
        step_feature = None

    result = {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record.openid,
        "session_id": record.session_id,
        "task_date": record.task_date,
        "recorded_at": format_datetime(record.recorded_at),
        "at": datetime_to_ms(record.recorded_at),
        "steps": record.steps,
        "source": record.source,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if step_feature:
        result["step_feature_id"] = step_feature.id
        result["step_feature_status"] = step_feature.status
    return result
