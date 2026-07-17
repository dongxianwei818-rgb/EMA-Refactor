"""EMA_Chat 非诊断对话服务。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.feedback_service import CAMPUS_RESOURCES, get_feedback
from app.services.risk_service import compute_risk_assessment

DISCLAIMER = (
    "本对话为科研非诊断支持，不能替代专业医疗或心理咨询。"
    "如遇紧急情况请拨打心理援助热线。"
)


def list_messages(db: Session, user, limit: int = 50) -> dict[str, Any]:
    ChatMessage = models_for(user=user, db=db).ChatMessage
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.id.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
    items = [_to_dict(r) for r in reversed(rows)]
    if not items:
        items = [
            {
                "id": 0,
                "role": "system",
                "content": (
                    DISCLAIMER
                    + "\n\n您好，我是 EMA 非诊断支持助手。"
                    "您可以询问近期状态反馈、校园资源，或描述当前困扰。"
                ),
                "meta": {"bootstrap": True},
                "created_at": None,
            }
        ]
    return {"items": items, "disclaimer": DISCLAIMER}


def send_user_message(db: Session, user, content: str) -> dict[str, Any]:
    ChatMessage = models_for(user=user, db=db).ChatMessage
    text = (content or "").strip()
    if not text:
        raise ValueError("消息不能为空")
    if len(text) > 2000:
        raise ValueError("消息过长（最多 2000 字）")

    user_msg = ChatMessage(user_id=user.id, role="user", content=text, meta={})
    db.add(user_msg)
    db.flush()

    reply_text, meta = _generate_assistant_reply(db, user, text)
    assistant_msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=reply_text,
        meta=meta,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return {
        "user_message": _to_dict(user_msg),
        "assistant_message": _to_dict(assistant_msg),
        "disclaimer": DISCLAIMER,
    }


def _generate_assistant_reply(db: Session, user, text: str) -> tuple[str, dict[str, Any]]:
    lower = text.lower()
    feedback = get_feedback(db, user)
    risk = compute_risk_assessment(db, user)
    level = (risk.get("current") or {}).get("level") or feedback.get("level") or "unknown"
    meta: dict[str, Any] = {"level": level, "kind": "rule_reply"}

    if any(k in text for k in ("资源", "热线", "求助", "预约", "联系")):
        lines = ["以下是可参考的支持资源（请按所在学校实际信息核对）："]
        for r in CAMPUS_RESOURCES:
            phone = f" · {r['phone']}" if r.get("phone") else ""
            lines.append(f"- {r.get('title')}{phone}：{r.get('desc')}")
        lines.append("\n" + DISCLAIMER)
        meta["kind"] = "resources"
        return "\n".join(lines), meta

    if any(k in text for k in ("风险", "评估", "预警", "状态")) or "risk" in lower:
        summary = (risk.get("current") or {}).get("summary") or feedback.get("message") or "暂无足够数据。"
        label = (risk.get("current") or {}).get("label") or level
        msg = (
            f"当前非诊断评估结果：【{label}】\n"
            f"{summary}\n\n"
            f"系统反馈：{feedback.get('message')}\n\n"
            f"{DISCLAIMER}"
        )
        meta["kind"] = "risk_summary"
        return msg, meta

    if any(k in text for k in ("焦虑", "抑郁", "失眠", "压力", "难受", "崩溃")):
        msg = (
            "感谢你愿意表达当下的感受。规律打卡与短暂的放松练习（如 4-7-8 呼吸）可能有帮助，"
            "但若痛苦持续或出现自伤想法，请尽快联系校园心理中心或拨打援助热线。\n\n"
            f"{DISCLAIMER}"
        )
        meta["kind"] = "support"
        return msg, meta

    msg = (
        f"{feedback.get('message') or '已收到你的消息。'}\n\n"
        "你也可以问我：今天的风险评估、校园心理资源，或描述具体困扰。\n\n"
        f"{DISCLAIMER}"
    )
    return msg, meta


def _to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "meta": row.meta or {},
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None,
    }
