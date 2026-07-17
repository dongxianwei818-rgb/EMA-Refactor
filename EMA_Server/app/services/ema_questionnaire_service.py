"""每日 EMA 问卷提交服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.analysis.async_extract import schedule_questions_features
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_session_id, parse_task_date
from app.services.user_identity import client_type_from_user, identity_row_kwargs, record_principal

SCALE_FIELDS = ("mood", "stress", "anxiety", "lonely", "sleep", "fatigue", "function")
NEGATIVE_OPTIONS = {"是", "否", "不愿回答"}


def _validate_scale(value: Any, field: str) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} 必须为 0-10 的整数") from exc
    if num < 0 or num > 10:
        raise ValueError(f"{field} 必须在 0-10 之间")
    return num


def submit_ema_questionnaire(db: Session, user, body: dict[str, Any]) -> dict[str, Any]:
    answered_at = body.get("answered_at")
    if isinstance(answered_at, datetime):
        at = answered_at
    else:
        at = parse_client_at(body)
    negative = body.get("negative")
    if not negative or str(negative) not in NEGATIVE_OPTIONS:
        raise ValueError("negative 必须为：是 / 否 / 不愿回答")

    scales = {field: _validate_scale(body.get(field), field) for field in SCALE_FIELDS}
    session_id = parse_session_id(body)
    task_date = parse_task_date(body, at)

    EmaQuestion = models_for(user=user).EmaQuestion
    record = EmaQuestion(
        user_id=user.id,
        **identity_row_kwargs(user),
        session_id=session_id,
        task_date=task_date,
        answered_at=at,
        negative=str(negative),
        **scales,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    schedule_questions_features(client_type_from_user(user), record.id)

    return {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record_principal(record),
        "session_id": record.session_id,
        "task_date": record.task_date,
        "answered_at": format_datetime(record.answered_at),
        "at": datetime_to_ms(record.answered_at),
        "mood": record.mood,
        "stress": record.stress,
        "anxiety": record.anxiety,
        "lonely": record.lonely,
        "sleep": record.sleep,
        "fatigue": record.fatigue,
        "function": record.function,
        "negative": record.negative,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "questions_feature_status": "pending",
    }
