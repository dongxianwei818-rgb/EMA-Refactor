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
from app.models import User

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


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_openid: str | None = Header(default=None, alias="X-User-Openid"),
    db: Session = Depends(get_db),
) -> User:
    openid = None
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_token_payload(token)
            openid = payload.get("sub")
            raw_uid = payload.get("uid")
            if raw_uid is not None:
                user_id = int(raw_uid)
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token") from exc
    elif x_user_openid:
        openid = x_user_openid

    if not openid and user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if user and openid and user.openid != openid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 与用户不匹配")
    if not user and openid:
        user = (
            db.query(User)
            .filter(User.openid == openid, User.study_status == "active")
            .order_by(User.id.desc())
            .first()
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user
