"""知情同意与授权记录服务."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.datetime_fields import datetime_to_ms, format_datetime


def _user_principal(user) -> str:
    return getattr(user, "user_name", None) or getattr(user, "openid", "") or ""


def record_consent_authorization(
    db: Session,
    user,
    status: str,
    event_info: dict[str, Any] | None = None,
    client_at: datetime | None = None,
) -> dict[str, Any]:
    if status not in ("accept", "revoke", "exit"):
        raise ValueError("status 必须为 accept、revoke 或 exit")

    m = models_for()
    ConsentAuthorizationLog = m.ConsentAuthorizationLog
    at = client_at or datetime.now()
    info = event_info or {}
    principal = _user_principal(user)

    log_kwargs: dict[str, Any] = {
        "user_id": user.id,
        "status": status,
        "event_info": info,
        "client_at": at,
    }
    if hasattr(ConsentAuthorizationLog, "user_name"):
        log_kwargs["user_name"] = principal
    else:
        log_kwargs["openid"] = principal

    db.add(ConsentAuthorizationLog(**log_kwargs))
    if status == "accept":
        if user.study_status != "exited":
            user.study_status = "active"
    elif status == "revoke":
        user.study_status = "consent_revoked"
    elif status == "exit":
        user.study_status = "exited"
        user.logout_at = at
    db.commit()
    db.refresh(user)

    latest = (
        db.query(ConsentAuthorizationLog)
        .filter(ConsentAuthorizationLog.user_id == user.id)
        .order_by(ConsentAuthorizationLog.id.desc())
        .first()
    )
    return {
        "user_id": user.id,
        "openid": principal,
        "status": status,
        "event_info": info,
        "client_at": format_datetime(at),
        "at": datetime_to_ms(at),
        "logout_at": format_datetime(user.logout_at) if status == "exit" else None,
        "created_at": latest.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest else "",
    }


def get_consent_status(db: Session, user_id: int) -> dict[str, Any]:
    """从 consent_authorization_logs 读取当前授权状态。"""
    ConsentAuthorizationLog = models_for().ConsentAuthorizationLog
    latest = (
        db.query(ConsentAuthorizationLog)
        .filter(ConsentAuthorizationLog.user_id == user_id)
        .order_by(ConsentAuthorizationLog.id.desc())
        .first()
    )
    if not latest:
        return {
            "user_id": user_id,
            "has_consent": False,
            "status": None,
            "client_at": None,
            "at": None,
        }
    return {
        "user_id": user_id,
        "has_consent": latest.status == "accept",
        "status": latest.status,
        "client_at": format_datetime(latest.client_at) if latest.client_at else None,
        "at": datetime_to_ms(latest.client_at) if latest.client_at else None,
    }


def user_has_consent(db: Session, user_id: int) -> bool:
    return bool(get_consent_status(db, user_id).get("has_consent"))


def latest_accept_consent(db: Session, user_id: int):
    ConsentAuthorizationLog = models_for().ConsentAuthorizationLog
    return (
        db.query(ConsentAuthorizationLog)
        .filter(
            ConsentAuthorizationLog.user_id == user_id,
            ConsentAuthorizationLog.status == "accept",
        )
        .order_by(ConsentAuthorizationLog.client_at.desc())
        .first()
    )
