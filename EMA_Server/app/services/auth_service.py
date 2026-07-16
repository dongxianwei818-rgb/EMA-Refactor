"""WeChat login service."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.dependencies import create_access_token
from app.models import BaselineProfile, User, UserLoginLog
from app.services.consent_service import user_has_consent
from app.services.wechat_session import jscode2session


def get_active_user_by_openid(db: Session, openid: str) -> User | None:
    return (
        db.query(User)
        .filter(User.openid == openid, User.study_status == "active")
        .order_by(User.id.desc())
        .first()
    )


def get_or_create_user(db: Session, openid: str) -> User:
    """获取当前 active 参与记录；若均已退出则新建一条参与记录。"""
    user = get_active_user_by_openid(db, openid)
    if user:
        return user
    user = User(openid=openid, study_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def record_user_login(db: Session, user: User) -> dict:
    logged_at = datetime.now()
    user.login_count = (user.login_count or 0) + 1
    log = UserLoginLog(
        user_id=user.id,
        openid=user.openid,
        logged_at=logged_at,
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    db.refresh(log)
    return {
        "login_log_id": log.id,
        "user_id": user.id,
        "openid": user.openid,
        "logged_at": logged_at.strftime("%Y-%m-%d %H:%M:%S"),
        "login_count": user.login_count,
    }


def record_user_logout(db: Session, user: User) -> dict:
    logout_at = datetime.now()
    log = (
        db.query(UserLoginLog)
        .filter(UserLoginLog.user_id == user.id, UserLoginLog.logout_at.is_(None))
        .order_by(UserLoginLog.logged_at.desc())
        .first()
    )
    if not log:
        return {
            "user_id": user.id,
            "openid": user.openid,
            "logout_at": None,
            "updated": False,
        }
    log.logout_at = logout_at
    db.commit()
    db.refresh(log)
    return {
        "login_log_id": log.id,
        "user_id": user.id,
        "openid": user.openid,
        "logged_at": log.logged_at.strftime("%Y-%m-%d %H:%M:%S"),
        "logout_at": logout_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated": True,
    }


async def wx_login(db: Session, code: str, client_type: str) -> dict:
    from app.client_types import validate_client_type

    client_type = validate_client_type(client_type)
    session = await jscode2session(code)
    openid = session["openid"]
    user = get_or_create_user(db, openid)
    user.session_key = session.get("session_key")
    db.commit()
    db.refresh(user)
    has_baseline = (
        db.query(BaselineProfile).filter(BaselineProfile.user_id == user.id).count() > 0
    )
    token = create_access_token(openid, user.id, client_type)
    return {
        "openid": openid,
        "token": token,
        "user_id": user.id,
        "client_type": client_type,
        "research_id": user.research_id,
        "study_status": user.study_status,
        "has_consent": user_has_consent(db, user.id),
        "has_baseline": has_baseline,
    }
