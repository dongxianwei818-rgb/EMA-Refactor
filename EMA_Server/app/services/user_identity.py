"""跨端用户身份：三端共用 ema_web 表结构（users.user_name / psw / role）。

client_type 以请求上下文 / JWT / Session.info 为准，不再依赖 ORM 模块路径。
"""

from __future__ import annotations

from typing import Any

from app.client_types import get_current_client_type


def is_web_user(user: Any) -> bool:
    """统一库后均具备 user_name；兼容旧 openid 形态。"""
    return hasattr(user, "user_name") and not hasattr(user, "openid")


def client_type_from_user(user: Any) -> str:
    """推断 client_type：优先 ContextVar（JWT/请求已设置）。"""
    return get_current_client_type()


def auth_principal(user: Any) -> str:
    """JWT sub / 鉴权匹配：统一用登录 user_name。"""
    if hasattr(user, "user_name") and user.user_name:
        return user.user_name
    return getattr(user, "openid", None) or ""


def user_principal(user: Any) -> str:
    """业务冗余标识与 API 中的 openid 字段：统一为 users.id 字符串。"""
    if hasattr(user, "user_name"):
        return str(user.id)
    return getattr(user, "openid", None) or ""


def identity_row_kwargs(user: Any) -> dict[str, Any]:
    """写入业务表时的身份列：统一 user_name=str(id)。"""
    if hasattr(user, "user_name"):
        return {"user_name": str(user.id)}
    return {"openid": getattr(user, "openid", None)}


def record_principal(record: Any) -> str:
    """从业务行读出身份展示字段。"""
    if hasattr(record, "user_name"):
        return record.user_name or ""
    return getattr(record, "openid", None) or ""
