"""Client type constants for multi-database routing."""

from contextvars import ContextVar

from fastapi import HTTPException, status

CLIENT_TYPE_WECHAT = "wechat"
CLIENT_TYPE_WEB = "web"
CLIENT_TYPE_APP = "app"

VALID_CLIENT_TYPES = frozenset({CLIENT_TYPE_WECHAT, CLIENT_TYPE_WEB, CLIENT_TYPE_APP})

DEFAULT_CLIENT_TYPE = CLIENT_TYPE_WECHAT

_current_client_type: ContextVar[str] = ContextVar("client_type", default=DEFAULT_CLIENT_TYPE)


def validate_client_type(client_type: str | None) -> str:
    if not client_type or client_type not in VALID_CLIENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"client_type 必须为 {', '.join(sorted(VALID_CLIENT_TYPES))} 之一",
        )
    return client_type


def set_current_client_type(client_type: str) -> str:
    validated = validate_client_type(client_type)
    _current_client_type.set(validated)
    return validated


def get_current_client_type() -> str:
    return _current_client_type.get()
