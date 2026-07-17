"""跨端用户身份：wechat/app 用 openid；web 业务侧用 users.id。"""

from __future__ import annotations

from typing import Any

from app.client_types import CLIENT_TYPE_APP, CLIENT_TYPE_WEB, CLIENT_TYPE_WECHAT


def is_web_user(user: Any) -> bool:
    return hasattr(user, "user_name") and not hasattr(user, "openid")


def client_type_from_user(user: Any) -> str:
    """由 ORM 用户实例推断 client_type（不依赖 ContextVar，线程池内也安全）。"""
    mod = type(user).__module__ or ""
    if ".web." in mod:
        return CLIENT_TYPE_WEB
    if ".app." in mod:
        return CLIENT_TYPE_APP
    if is_web_user(user):
        return CLIENT_TYPE_WEB
    return CLIENT_TYPE_WECHAT


def auth_principal(user: Any) -> str:
    """JWT sub / 鉴权匹配：web 用登录 user_name，其余用 openid。"""
    if is_web_user(user):
        return getattr(user, "user_name", None) or ""
    return getattr(user, "openid", None) or ""


def user_principal(user: Any) -> str:
    """业务冗余标识与 API 中的 openid 字段：web 为 users.id 字符串，其余为 openid。"""
    if is_web_user(user):
        return str(user.id)
    return getattr(user, "openid", None) or ""


def identity_row_kwargs(user: Any) -> dict[str, Any]:
    """写入业务表时的身份列：web → user_name=str(id)；wechat/app → openid。"""
    if is_web_user(user):
        return {"user_name": str(user.id)}
    return {"openid": user.openid}


def record_principal(record: Any) -> str:
    """从业务行读出身份展示字段（web 为 users.id，其余为 openid）。"""
    if hasattr(record, "user_name"):
        return record.user_name or ""
    return getattr(record, "openid", None) or ""
