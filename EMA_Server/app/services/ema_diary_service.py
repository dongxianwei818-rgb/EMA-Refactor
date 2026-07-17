"""文本日志提交服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.analysis.async_extract import schedule_text_features
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at
from app.services.session_fields import parse_session_id, parse_task_date
from app.services.user_identity import client_type_from_user, identity_row_kwargs, record_principal

DIARY_MIN_LEN = 30
DIARY_MAX_LEN = 100


def submit_ema_diary(db: Session, user, body: dict[str, Any]) -> dict[str, Any]:
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

    EmaDiary = models_for(user=user).EmaDiary
    record = EmaDiary(
        user_id=user.id,
        **identity_row_kwargs(user),
        session_id=parse_session_id(body),
        task_date=parse_task_date(body, at),
        written_at=at,
        text=text,
        length=char_len,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # 文本向量模型冷启动很慢，后台提取，避免提交接口超时
    schedule_text_features(client_type_from_user(user), record.id)

    return {
        "id": record.id,
        "user_id": record.user_id,
        "openid": record_principal(record),
        "session_id": record.session_id,
        "task_date": record.task_date,
        "written_at": format_datetime(record.written_at),
        "at": datetime_to_ms(record.written_at),
        "text": record.text,
        "length": record.length,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "text_feature_status": "pending",
    }
