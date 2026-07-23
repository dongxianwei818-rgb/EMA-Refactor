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

# 三端共用 ema_web：默认引擎指向 web
engine = _engines[CLIENT_TYPE_WEB]
SessionLocal = _session_factories[CLIENT_TYPE_WEB]


class WechatBase(DeclarativeBase):
    """遗留 Base（旧 wechat/ema 模型）；业务不再使用。"""


class WebBase(DeclarativeBase):
    """三端共用：ema_web 表结构。"""


class AppBase(DeclarativeBase):
    """遗留 Base（旧 app/ema_app 模型）；业务不再使用。"""


# 三端 ORM / create_all 统一走 WebBase（ema_web）
BASES: dict[str, type[DeclarativeBase]] = {
    CLIENT_TYPE_WECHAT: WebBase,
    CLIENT_TYPE_WEB: WebBase,
    CLIENT_TYPE_APP: WebBase,
}

# 兼容旧代码中的 Base 引用
Base = WebBase


def get_base(client_type: str) -> type[DeclarativeBase]:
    return BASES[validate_client_type(client_type)]


def get_engine(client_type: str) -> Engine:
    return _engines[validate_client_type(client_type)]


def get_session_factory(client_type: str) -> sessionmaker:
    return _session_factories[validate_client_type(client_type)]


def create_session(client_type: str) -> Session:
    client_type = validate_client_type(client_type)
    session = get_session_factory(client_type)()
    session.info["client_type"] = client_type
    return session


def iter_engines() -> list[tuple[str, Engine]]:
    return [(ct, _engines[ct]) for ct in sorted(VALID_CLIENT_TYPES)]
