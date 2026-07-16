"""Database session and base models (multi-DB by client type)."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.client_types import (
    CLIENT_TYPE_APP,
    CLIENT_TYPE_WEB,
    CLIENT_TYPE_WECHAT,
    VALID_CLIENT_TYPES,
    validate_client_type,
)
from app.config import get_settings

settings = get_settings()

_engines: dict[str, Engine] = {}
_session_factories: dict[str, sessionmaker] = {}

for _client_type in sorted(VALID_CLIENT_TYPES):
    _db_name = settings.db_name_for_client(_client_type)
    _engine = create_engine(
        settings.database_url_for(_db_name),
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    _engines[_client_type] = _engine
    _session_factories[_client_type] = sessionmaker(
        autocommit=False, autoflush=False, bind=_engine
    )

# 兼容旧脚本：默认指向 wechat / ema
engine = _engines[CLIENT_TYPE_WECHAT]
SessionLocal = _session_factories[CLIENT_TYPE_WECHAT]


class WechatBase(DeclarativeBase):
    """wechat → ema：小程序表结构。"""


class WebBase(DeclarativeBase):
    """web → ema_web：Web 端表结构。"""


class AppBase(DeclarativeBase):
    """app → ema_app：App 端表结构。"""


BASES: dict[str, type[DeclarativeBase]] = {
    CLIENT_TYPE_WECHAT: WechatBase,
    CLIENT_TYPE_WEB: WebBase,
    CLIENT_TYPE_APP: AppBase,
}

# 兼容旧代码中的 Base 引用（等同 wechat）
Base = WechatBase


def get_base(client_type: str) -> type[DeclarativeBase]:
    return BASES[validate_client_type(client_type)]


def get_engine(client_type: str) -> Engine:
    return _engines[validate_client_type(client_type)]


def get_session_factory(client_type: str) -> sessionmaker:
    return _session_factories[validate_client_type(client_type)]


def create_session(client_type: str) -> Session:
    return get_session_factory(client_type)()


def iter_engines() -> list[tuple[str, Engine]]:
    return [(ct, _engines[ct]) for ct in sorted(VALID_CLIENT_TYPES)]
