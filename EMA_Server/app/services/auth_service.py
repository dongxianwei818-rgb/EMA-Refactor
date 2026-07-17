"""Auth / login service (wechat openid & web password)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.dependencies import create_access_token
from app.models import models_for
from app.services.consent_service import user_has_consent
from app.services.user_identity import auth_principal, user_principal
from app.services.wechat_session import jscode2session


def get_active_user_by_openid(db: Session, openid: str, client_type: str | None = None):
    User = models_for(client_type).User
    return (
        db.query(User)
        .filter(User.openid == openid, User.study_status == "active")
        .order_by(User.id.desc())
        .first()
    )


def get_or_create_user(db: Session, openid: str, client_type: str | None = None):
    """获取当前 active 参与记录；若均已退出则新建一条参与记录。"""
    User = models_for(client_type).User
    user = get_active_user_by_openid(db, openid, client_type)
    if user:
        return user
    user = User(openid=openid, study_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def record_user_login(db: Session, user, client_type: str | None = None) -> dict:
    m = models_for(client_type)
    UserLoginLog = m.UserLoginLog
    logged_at = datetime.now()
    user.login_count = (user.login_count or 0) + 1
    principal = user_principal(user)
    log_kwargs = {"user_id": user.id, "logged_at": logged_at}
    if hasattr(UserLoginLog, "user_name"):
        log_kwargs["user_name"] = principal
    else:
        log_kwargs["openid"] = principal
    log = UserLoginLog(**log_kwargs)
    db.add(log)
    db.commit()
    db.refresh(user)
    db.refresh(log)
    return {
        "login_log_id": log.id,
        "user_id": user.id,
        "openid": principal,
        "user_name": getattr(user, "user_name", None),
        "logged_at": logged_at.strftime("%Y-%m-%d %H:%M:%S"),
        "login_count": user.login_count,
    }


def record_user_logout(db: Session, user, client_type: str | None = None) -> dict:
    UserLoginLog = models_for(client_type).UserLoginLog
    logout_at = datetime.now()
    principal = user_principal(user)
    log = (
        db.query(UserLoginLog)
        .filter(UserLoginLog.user_id == user.id, UserLoginLog.logout_at.is_(None))
        .order_by(UserLoginLog.logged_at.desc())
        .first()
    )
    if not log:
        return {
            "user_id": user.id,
            "openid": principal,
            "logout_at": None,
            "updated": False,
        }
    log.logout_at = logout_at
    db.commit()
    db.refresh(log)
    return {
        "login_log_id": log.id,
        "user_id": user.id,
        "openid": principal,
        "logged_at": log.logged_at.strftime("%Y-%m-%d %H:%M:%S"),
        "logout_at": logout_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated": True,
    }


async def wx_login(db: Session, code: str, client_type: str) -> dict:
    from app.client_types import validate_client_type

    client_type = validate_client_type(client_type)
    m = models_for(client_type)
    session = await jscode2session(code)
    openid = session["openid"]
    user = get_or_create_user(db, openid, client_type)
    user.session_key = session.get("session_key")
    db.commit()
    db.refresh(user)
    has_baseline = (
        db.query(m.BaselineProfile).filter(m.BaselineProfile.user_id == user.id).count() > 0
    )
    token = create_access_token(openid, user.id, client_type)
    return {
        "openid": openid,
        "token": token,
        "user_id": user.id,
        "client_type": client_type,
        "research_id": user.research_id,
        "study_status": user.study_status,
        "has_consent": user_has_consent(db, user.id, user=user),
        "has_baseline": has_baseline,
    }


def password_login(db: Session, user_name: str, psw: str, client_type: str = "web") -> dict:
    """Web 端用户名密码登录，校验 users.user_name / users.psw。"""
    from app.client_types import CLIENT_TYPE_WEB, validate_client_type

    client_type = validate_client_type(client_type)
    if client_type != CLIENT_TYPE_WEB:
        raise ValueError("密码登录仅支持 client_type=web")

    m = models_for(client_type)
    User = m.User
    name = (user_name or "").strip()
    if not name or not psw:
        raise ValueError("用户名和密码不能为空")

    user = (
        db.query(User)
        .filter(User.user_name == name, User.study_status == "active")
        .order_by(User.id.desc())
        .first()
    )
    if not user or (user.psw or "") != psw:
        raise ValueError("用户名或密码错误")

    record_user_login(db, user, client_type)
    db.refresh(user)
    has_baseline = (
        db.query(m.BaselineProfile).filter(m.BaselineProfile.user_id == user.id).count() > 0
    )
    # JWT sub 仍用登录名；响应 openid 字段对 web 统一为 users.id
    token = create_access_token(auth_principal(user), user.id, client_type)
    return {
        "openid": user_principal(user),
        "user_name": user.user_name,
        "token": token,
        "user_id": user.id,
        "client_type": client_type,
        "role": user.role,
        "research_id": user.research_id,
        "study_status": user.study_status,
        "has_consent": user_has_consent(db, user.id, user=user),
        "has_baseline": has_baseline,
    }
