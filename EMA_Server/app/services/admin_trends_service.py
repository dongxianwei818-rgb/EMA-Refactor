"""Web 管理端：普通用户趋势分析汇总与详情。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.client_types import CLIENT_TYPE_WEB
from app.models import models_for
from app.services.risk_service import LEVEL_META, compute_risk_assessment
from app.services.trends_service import get_trends_overview


LEVEL_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "unknown": 0,
}


def _is_normal_user(user) -> bool:
    return user.role is None or int(user.role) != 0


def _get_normal_user(db: Session, user_id: int):
    User = models_for(CLIENT_TYPE_WEB).User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if not _is_normal_user(user):
        raise ValueError("仅支持查看普通用户的趋势数据")
    return user


def _risk_summary(db: Session, user) -> dict[str, Any]:
    risk = compute_risk_assessment(db, user, save_snapshot=False)
    current = risk.get("current") or {}
    level = current.get("level") or "unknown"
    meta = LEVEL_META.get(level) or LEVEL_META["unknown"]
    return {
        "hasAssessment": bool(risk.get("hasAssessment")),
        "level": level,
        "levelLabel": current.get("levelLabel") or meta["label"],
        "levelClass": current.get("levelClass") or meta["className"],
        "score": int(current.get("score") or 0),
        "scoreBasedLevel": current.get("scoreBasedLevel") or level,
        "scoreBasedLevelLabel": current.get("scoreBasedLevelLabel") or meta["label"],
        "critical": bool(current.get("critical") or risk.get("critical")),
        "criticalForced": bool(current.get("criticalForced") or risk.get("criticalForced")),
        "criticalReasons": current.get("criticalReasons")
        or risk.get("criticalReasons")
        or [],
        "summary": current.get("summary") or "",
        "updatedLabel": current.get("updatedLabel") or "",
        "alertCount": int(risk.get("alertCount") or 0),
        "alertDangerCount": int(risk.get("alertDangerCount") or 0),
        "alertWarnCount": int(risk.get("alertWarnCount") or 0),
        "severityRank": LEVEL_RANK.get(level, 0),
    }


def list_user_trend_summaries(
    db: Session,
    *,
    keyword: str | None = None,
    study_status: str | None = None,
    level: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """列出普通用户趋势摘要，按重点关注 → 中等关注 → 低风险排序。"""
    User = models_for(CLIENT_TYPE_WEB).User
    q = db.query(User).filter(or_(User.role.is_(None), User.role != 0))
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(User.user_name.like(like) | User.research_id.like(like))
    if study_status:
        q = q.filter(User.study_status == study_status)

    users = q.order_by(User.id.asc()).all()
    items: list[dict[str, Any]] = []
    for user in users:
        risk = _risk_summary(db, user)
        items.append(
            {
                "userId": user.id,
                "userName": user.user_name,
                "researchId": user.research_id,
                "studyStatus": user.study_status,
                "loginCount": user.login_count or 0,
                **risk,
            }
        )

    items.sort(
        key=lambda row: (
            -int(row.get("severityRank") or 0),
            -int(row.get("score") or 0),
            -int(row.get("alertDangerCount") or 0),
            int(row.get("userId") or 0),
        )
    )

    high_count = sum(1 for row in items if row.get("level") == "high")
    medium_count = sum(1 for row in items if row.get("level") == "medium")
    low_count = sum(1 for row in items if row.get("level") == "low")

    if level:
        items = [row for row in items if row.get("level") == level]

    total = len(items)
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "highCount": high_count,
        "mediumCount": medium_count,
        "lowCount": low_count,
        "items": page_items,
    }


def get_user_trends_overview(db: Session, user_id: int, days: int = 7) -> dict[str, Any]:
    """管理员查看指定普通用户的完整趋势概览。"""
    user = _get_normal_user(db, user_id)
    overview = get_trends_overview(db, user, days=days)
    overview["user"] = {
        "userId": user.id,
        "userName": user.user_name,
        "researchId": user.research_id,
        "studyStatus": user.study_status,
    }
    return overview
