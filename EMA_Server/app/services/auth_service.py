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
    from app.client_types import get_current_client_type, validate_client_type

    resolved = validate_client_type(client_type or get_current_client_type())
    m = models_for(client_type=resolved, user=user, db=db)
    UserLoginLog = m.UserLoginLog
    logged_at = datetime.now()
    user.login_count = (user.login_count or 0) + 1
    principal = user_principal(user)
    log_kwargs = {"user_id": user.id, "logged_at": logged_at}
    if hasattr(UserLoginLog, "client_type"):
        log_kwargs["client_type"] = resolved
    # 兼容旧表结构若仍有 openid 列
    if hasattr(UserLoginLog, "openid"):
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
        "client_type": resolved,
        "logged_at": logged_at.strftime("%Y-%m-%d %H:%M:%S"),
        "login_count": user.login_count,
    }


def record_user_logout(db: Session, user, client_type: str | None = None) -> dict:
    UserLoginLog = models_for(client_type=client_type, user=user, db=db).UserLoginLog
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
    """用户名密码登录（wechat / web / app），校验 ema_web.users.user_name / psw。

    普通用户若已退出研究（study_status=exited）：校验密码通过后新建一条参与记录
   （study_status=active，无 research_id），需重新知情同意并绑定基线。
    微信小程序端仅允许普通用户（role!=0）；管理员请使用 Web 端登录。
    """
    from app.client_types import CLIENT_TYPE_WECHAT, validate_client_type
    from app.services.user_service import create_participation_user

    client_type = validate_client_type(client_type)

    m = models_for(client_type)
    User = m.User
    name = (user_name or "").strip()
    if not name or not psw:
        raise ValueError("用户名和密码不能为空")

    # 优先使用当前 active 参与记录；否则取同名最近一条（含已退出）
    user = (
        db.query(User)
        .filter(User.user_name == name, User.study_status == "active")
        .order_by(User.id.desc())
        .first()
    )
    if not user:
        user = (
            db.query(User)
            .filter(User.user_name == name)
            .order_by(User.id.desc())
            .first()
        )

    if not user or (user.psw or "") != psw:
        raise ValueError("用户名或密码错误")

    role = getattr(user, "role", None)
    is_admin = role == 0

    if client_type == CLIENT_TYPE_WECHAT and is_admin:
        raise ValueError("微信小程序仅支持普通用户，管理员账号请使用 Web 端登录！！")

    if is_admin:
        if (user.study_status or "") != "active":
            raise ValueError(f"账号当前状态为「{user.study_status or '未知'}」，无法登录")
    elif (user.study_status or "") == "exited":
        # 退出后再登录：新建参与轮次，重新走知情同意 + 基线绑定
        user = create_participation_user(db, user)
        db.commit()
        db.refresh(user)
    elif (user.study_status or "") != "active":
        raise ValueError(f"账号当前状态为「{user.study_status or '未知'}」，无法登录")

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


def change_password(
    db: Session,
    user_name: str,
    old_psw: str,
    new_psw: str,
    client_type: str = "web",
) -> dict:
    """修改密码：校验用户名与原密码后更新同名账号的全部参与记录（无需先登录）。"""
    from app.client_types import validate_client_type

    client_type = validate_client_type(client_type)

    User = models_for(client_type).User
    name = (user_name or "").strip()
    old = old_psw or ""
    new = (new_psw or "").strip()

    if not name or not old or not new:
        raise ValueError("用户名、原密码和新密码不能为空")
    if new == old:
        raise ValueError("新密码不能与原密码相同")
    if len(new) < 6:
        raise ValueError("新密码至少 6 位")

    user = (
        db.query(User)
        .filter(User.user_name == name, User.study_status == "active")
        .order_by(User.id.desc())
        .first()
    )
    if not user:
        user = (
            db.query(User)
            .filter(User.user_name == name)
            .order_by(User.id.desc())
            .first()
        )

    if not user or (user.psw or "") != old:
        raise ValueError("用户名或原密码错误")

    # 同名多轮参与记录一并更新，避免退出后再登录仍用旧密码
    rows = db.query(User).filter(User.user_name == name).all()
    for row in rows:
        row.psw = new
    db.commit()

    return {
        "user_name": name,
        "updated_count": len(rows),
    }
