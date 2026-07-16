"""文本日志提交服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import EmaDiary, User
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_session_id, parse_task_date

DIARY_MIN_LEN = 30
DIARY_MAX_LEN = 100


def submit_ema_diary(db: Session, user: User, body: dict[str, Any]) -> dict[str, Any]:
    text = (body.get("text") or "")
    if not text:
        raise ValueError("日记内容不能为空")

    char_len = len(text)
    if char_len < DIARY_MIN_LEN or char_len > DIARY_MAX_LEN:
        raise ValueError(f"日记长度须在 {DIARY_MIN_LEN}-{DIARY_MAX_LEN} 字之间")

    client_length = body.get("length")
    if client_length is not None and int(client_length) != char_len:
        raise ValueError("length 与 text 实际字数不一致")

    written_at = body.get("written_at")
    if isinstance(written_at, datetime):
        at = written_at
    else:
        at = parse_client_at(body)

    record = EmaDiary(
        user_id=user.id,
        openid=user.openid,
        session_id=parse_session_id(body),
        task_date=parse_task_date(body, at),
        written_at=at,
        text=text,
        length=char_len,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        from app.services.analysis import extract_text_features_from_diary_row

        text_feature = extract_text_features_from_diary_row(db, record)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("日记文本特性提取失败 diary_id=%s", record.id)
        text_feature = None

    result = {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record.openid,
        "session_id": record.session_id,
        "task_date": record.task_date,
        "written_at": format_datetime(record.written_at),
        "at": datetime_to_ms(record.written_at),
        "text": record.text,
        "length": record.length,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if text_feature:
        result["text_feature_id"] = text_feature.id
        result["text_feature_status"] = text_feature.status
    return result
