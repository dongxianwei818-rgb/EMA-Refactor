"""每日 EMA 问卷提交服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import EmaQuestion, User
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_session_id, parse_task_date

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


def submit_ema_questionnaire(db: Session, user: User, body: dict[str, Any]) -> dict[str, Any]:
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

    record = EmaQuestion(
        user_id=user.id,
        openid=user.openid,
        session_id=session_id,
        task_date=task_date,
        answered_at=at,
        negative=str(negative),
        **scales,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        from app.services.analysis import extract_questions_features_from_question_row

        questions_feature = extract_questions_features_from_question_row(db, record)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("问卷 EMA 特性提取失败 question_id=%s", record.id)
        questions_feature = None

    result = {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record.openid,
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
    }
    if questions_feature:
        result["questions_feature_id"] = questions_feature.id
        result["questions_feature_status"] = questions_feature.status
    return result
