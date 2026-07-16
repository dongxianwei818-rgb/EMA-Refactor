"""Non-diagnostic feedback read/write."""

from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models import FeedbackRecord, User

CAMPUS_RESOURCES = [
    {
        "title": "校内心理中心",
        "desc": "research@example.edu.cn（请替换为实际预约方式）",
        "type": "campus",
    },
    {
        "title": "全国心理援助热线",
        "phone": "12356",
        "desc": "24 小时",
        "type": "hotline",
    },
]

DEFAULT_MESSAGES = {
    "low": "近期状态整体平稳。规律打卡有助于研究团队更好理解您的日常变化。",
    "medium": "部分指标出现波动，这并不等同于诊断。建议适当休息，并可浏览资源页自助练习。",
    "high": "系统检测到需重点关注的信号。本反馈仅供科研参考，不构成临床诊断，建议主动联系心理支持资源。",
    "unknown": "数据尚不足，完成基线测评与 EMA 打卡后可获得个性化反馈。",
}


def _default_content(level: str = "unknown") -> dict[str, Any]:
    return {
        "disclaimer": "本反馈为非诊断性信息，不能替代专业医疗或心理咨询。",
        "level": level,
        "message": DEFAULT_MESSAGES.get(level, DEFAULT_MESSAGES["unknown"]),
        "resources": CAMPUS_RESOURCES,
    }


def _record_to_response(record: FeedbackRecord) -> dict[str, Any]:
    content = record.content or {}
    return {
        "hasFeedback": True,
        "id": record.id,
        "user_id": record.user_id,
        "task_date": record.task_date,
        "session_id": record.session_id,
        "feedback_type": record.feedback_type,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "disclaimer": content.get("disclaimer") or _default_content()["disclaimer"],
        "level": content.get("level", "unknown"),
        "message": content.get("message") or DEFAULT_MESSAGES["unknown"],
        "resources": content.get("resources") or CAMPUS_RESOURCES,
        "content": content,
    }


def get_feedback(
    db: Session,
    user: User,
    task_date: str | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    query = db.query(FeedbackRecord).filter(FeedbackRecord.user_id == user.id)
    if task_date:
        query = query.filter(FeedbackRecord.task_date == task_date)
    if session_id is not None:
        query = query.filter(FeedbackRecord.session_id == session_id)

    record = query.order_by(FeedbackRecord.created_at.desc()).first()
    if record:
        return _record_to_response(record)

    default = _default_content("unknown")
    return {
        "hasFeedback": False,
        "user_id": user.id,
        "task_date": task_date,
        "session_id": session_id,
        "feedback_type": None,
        "created_at": None,
        **default,
        "content": default,
    }


def create_feedback_record(
    db: Session,
    *,
    user_id: int,
    task_date: str,
    session_id: int,
    content: dict[str, Any],
    feedback_type: str = "non_diagnostic",
) -> dict[str, Any]:
    if session_id < 1:
        raise ValueError("session_id 必须 >= 1")
    if not task_date:
        raise ValueError("task_date 不能为空")
    if not content:
        raise ValueError("content 不能为空")

    payload = dict(content)
    payload.setdefault("disclaimer", _default_content()["disclaimer"])
    payload.setdefault("resources", CAMPUS_RESOURCES)

    stmt = mysql_insert(FeedbackRecord).values(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        feedback_type=feedback_type,
        content=payload,
    )
    stmt = stmt.on_duplicate_key_update(content=stmt.inserted.content)
    db.execute(stmt)
    db.commit()

    record = (
        db.query(FeedbackRecord)
        .filter(
            FeedbackRecord.user_id == user_id,
            FeedbackRecord.task_date == task_date,
            FeedbackRecord.session_id == session_id,
            FeedbackRecord.feedback_type == feedback_type,
        )
        .first()
    )
    if not record:
        raise ValueError("反馈记录保存失败")
    return _record_to_response(record)
