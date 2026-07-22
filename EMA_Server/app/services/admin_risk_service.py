"""Web 管理端：普通用户风险预警汇总与详情。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.client_types import CLIENT_TYPE_WEB
from app.models import models_for
from app.services.risk_service import LEVEL_META, compute_risk_assessment


LEVEL_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "unknown": 0,
}

ALERT_LEVEL_RANK = {
    "danger": 3,
    "warn": 2,
    "info": 1,
}


def _is_normal_user(user) -> bool:
    return user.role is None or int(user.role) != 0


def _get_normal_user(db: Session, user_id: int):
    User = models_for(CLIENT_TYPE_WEB).User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if not _is_normal_user(user):
        raise ValueError("仅支持查看普通用户的风险预警数据")
    return user


def _sort_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        alerts,
        key=lambda item: (
            -int(ALERT_LEVEL_RANK.get(item.get("level") or "", 0)),
            str(item.get("id") or ""),
        ),
    )


def _alert_preview(alerts: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for item in _sort_alerts(alerts)[:limit]:
        preview.append(
            {
                "id": item.get("id"),
                "level": item.get("level"),
                "levelLabel": item.get("levelLabel"),
                "title": item.get("title"),
                "desc": item.get("desc"),
                "category": item.get("category"),
                "source": item.get("source"),
                "metric": item.get("metric"),
            }
        )
    return preview


def _risk_warning_summary(db: Session, user) -> dict[str, Any]:
    risk = compute_risk_assessment(db, user, save_snapshot=False)
    current = risk.get("current") or {}
    level = current.get("level") or "unknown"
    meta = LEVEL_META.get(level) or LEVEL_META["unknown"]
    alerts = list(risk.get("alerts") or [])
    sorted_alerts = _sort_alerts(alerts)
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
        "alertInfoCount": int(risk.get("alertInfoCount") or 0),
        "alertCategories": risk.get("alertCategories") or [],
        "forecast30PeakLabel": (risk.get("forecast30") or {}).get("peakLevelLabel") or "",
        "forecast30HighDays": int((risk.get("forecast30") or {}).get("highRiskDays") or 0),
        "forecast30MediumDays": int((risk.get("forecast30") or {}).get("mediumRiskDays") or 0),
        "forecastAlertCount": int(risk.get("forecastAlertCount") or 0),
        "forecastAlertDangerCount": int(risk.get("forecastAlertDangerCount") or 0),
        "emaFeatureAlertCount": sum(
            1
            for a in (risk.get("alerts") or [])
            if (a.get("category") or "") == "EMA五特性抽取风险预警"
        ),
        "behaviorAnalysisAlertCount": sum(
            1
            for a in (risk.get("alerts") or [])
            if (a.get("category") or "") == "用户行为分析风险预警"
        ),
        "topForecastAlerts": _alert_preview(list(risk.get("forecastAlerts") or []), limit=3),
        "topAlerts": _alert_preview(sorted_alerts),
        "severityRank": LEVEL_RANK.get(level, 0),
    }


def list_user_risk_warnings(
    db: Session,
    *,
    keyword: str | None = None,
    study_status: str | None = None,
    level: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """列出普通用户风险预警摘要，按风险等级严重程度从高到低排序。"""
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
        risk = _risk_warning_summary(db, user)
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
            -int(row.get("alertDangerCount") or 0),
            -int(row.get("alertCount") or 0),
            -int(row.get("score") or 0),
            int(row.get("userId") or 0),
        )
    )

    high_count = sum(1 for row in items if row.get("level") == "high")
    medium_count = sum(1 for row in items if row.get("level") == "medium")
    low_count = sum(1 for row in items if row.get("level") == "low")
    alert_user_count = sum(1 for row in items if int(row.get("alertCount") or 0) > 0)
    danger_alert_total = sum(int(row.get("alertDangerCount") or 0) for row in items)

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
        "alertUserCount": alert_user_count,
        "dangerAlertTotal": danger_alert_total,
        "items": page_items,
    }


def get_user_risk_warning(db: Session, user_id: int) -> dict[str, Any]:
    """管理员查看指定普通用户的完整风险预警详情。"""
    user = _get_normal_user(db, user_id)
    risk = compute_risk_assessment(db, user, save_snapshot=False)
    alerts = _sort_alerts(list(risk.get("alerts") or []))
    risk = {**risk, "alerts": alerts}
    return {
        "user": {
            "userId": user.id,
            "userName": user.user_name,
            "researchId": user.research_id,
            "studyStatus": user.study_status,
        },
        "risk": risk,
    }


def list_user_risk_options(
    db: Session,
    *,
    exclude_user_id: int | None = None,
) -> list[dict[str, Any]]:
    """返回可切换的普通用户简表（按风险等级排序），供详情页切换入口。"""
    data = list_user_risk_warnings(db, page=1, page_size=100)
    options: list[dict[str, Any]] = []
    for row in data.get("items") or []:
        uid = int(row.get("userId") or 0)
        if exclude_user_id and uid == exclude_user_id:
            continue
        options.append(
            {
                "userId": uid,
                "userName": row.get("userName"),
                "researchId": row.get("researchId"),
                "level": row.get("level"),
                "levelLabel": row.get("levelLabel"),
                "score": row.get("score"),
                "alertCount": row.get("alertCount"),
            }
        )
    return options
