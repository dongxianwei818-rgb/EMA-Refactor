"""Auth dependencies and JWT helpers."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.client_types import (
    DEFAULT_CLIENT_TYPE,
    VALID_CLIENT_TYPES,
    get_current_client_type,
    set_current_client_type,
    validate_client_type,
)
from app.config import get_settings
from app.database import create_session
from app.models import models_for

settings = get_settings()
ALGORITHM = "HS256"


def create_access_token(
    openid: str, user_id: int, client_type: str | None = None
) -> str:
    client_type = validate_client_type(client_type or get_current_client_type())
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": openid,
        "uid": user_id,
        "client_type": client_type,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token_payload(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def client_type_from_token(token: str) -> str | None:
    try:
        payload = decode_token_payload(token)
    except JWTError:
        return None
    raw = payload.get("client_type")
    if raw in VALID_CLIENT_TYPES:
        return raw
    return None


def resolve_client_type(
    authorization: str | None = Header(default=None),
    x_client_type: str | None = Header(default=None, alias="X-Client-Type"),
) -> str:
    """Resolve DB client type: JWT claim > X-Client-Type header > default wechat."""
    resolved = DEFAULT_CLIENT_TYPE
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        from_token = client_type_from_token(token)
        if from_token:
            if x_client_type and x_client_type != from_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="X-Client-Type 与 token 中的 client_type 不一致",
                )
            resolved = from_token
        elif x_client_type:
            resolved = validate_client_type(x_client_type)
    elif x_client_type:
        resolved = validate_client_type(x_client_type)
    return set_current_client_type(resolved)


def get_db(client_type: str = Depends(resolve_client_type)) -> Generator[Session, None, None]:
    db = create_session(client_type)
    try:
        yield db
    finally:
        db.close()


def _user_identity_attr(User):
    return User.user_name if hasattr(User, "user_name") else User.openid


def _user_identity_value(user) -> str:
    """鉴权匹配用：web 登录主体仍为 user_name；业务冗余身份见 user_identity.user_principal。"""
    from app.services.user_identity import auth_principal

    return auth_principal(user)


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_openid: str | None = Header(default=None, alias="X-User-Openid"),
    client_type: str = Depends(resolve_client_type),
    db: Session = Depends(get_db),
):
    User = models_for(client_type).User
    identity_attr = _user_identity_attr(User)
    principal = None
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_token_payload(token)
            principal = payload.get("sub")
            raw_uid = payload.get("uid")
            if raw_uid is not None:
                user_id = int(raw_uid)
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token") from exc
    elif x_user_openid:
        principal = x_user_openid

    if not principal and user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if user and principal and _user_identity_value(user) != principal:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 与用户不匹配")
    if not user and principal:
        user = (
            db.query(User)
            .filter(identity_attr == principal, User.study_status == "active")
            .order_by(User.id.desc())
            .first()
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


def get_current_admin(
    user=Depends(get_current_user),
    client_type: str = Depends(resolve_client_type),
):
    """仅允许 web 端 role=0 的管理员。"""
    from app.client_types import CLIENT_TYPE_WEB

    if client_type != CLIENT_TYPE_WEB:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 Web 端可用")
    role = getattr(user, "role", None)
    if role != 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def resolve_web_client_type(
    authorization: str | None = Header(default=None),
    x_client_type: str | None = Header(default=None, alias="X-Client-Type"),
) -> str:
    """Web 管理端路由固定选 ema_web；JWT 若含 client_type 必须为 web。"""
    from app.client_types import CLIENT_TYPE_WEB

    if authorization and authorization.startswith("Bearer "):
        from_token = client_type_from_token(authorization.split(" ", 1)[1])
        if from_token and from_token != CLIENT_TYPE_WEB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请使用 Web 端账号登录（client_type=web）",
            )
    if x_client_type and x_client_type != CLIENT_TYPE_WEB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Client-Type 必须为 web",
        )
    return set_current_client_type(CLIENT_TYPE_WEB)


def get_web_db(
    client_type: str = Depends(resolve_web_client_type),
) -> Generator[Session, None, None]:
    db = create_session(client_type)
    try:
        yield db
    finally:
        db.close()


def get_current_web_admin(
    authorization: str | None = Header(default=None),
    client_type: str = Depends(resolve_web_client_type),
    db: Session = Depends(get_web_db),
):
    """Web 管理端鉴权：固定 web 库 + role=0。"""
    User = models_for(client_type).User
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token_payload(token)
        principal = payload.get("sub")
        raw_uid = payload.get("uid")
        user_id = int(raw_uid) if raw_uid is not None else None
    except (JWTError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token") from exc

    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if user and principal and user.user_name != principal:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 与用户不匹配")
    if not user and principal:
        user = (
            db.query(User)
            .filter(User.user_name == principal, User.study_status == "active")
            .order_by(User.id.desc())
            .first()
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if getattr(user, "role", None) != 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
