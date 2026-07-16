"""Database session and base model (multi-DB by client type)."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.client_types import CLIENT_TYPE_WECHAT, VALID_CLIENT_TYPES, validate_client_type
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


class Base(DeclarativeBase):
    pass


def get_engine(client_type: str) -> Engine:
    return _engines[validate_client_type(client_type)]


def get_session_factory(client_type: str) -> sessionmaker:
    return _session_factories[validate_client_type(client_type)]


def create_session(client_type: str) -> Session:
    return get_session_factory(client_type)()


def iter_engines() -> list[tuple[str, Engine]]:
    return [(ct, _engines[ct]) for ct in sorted(VALID_CLIENT_TYPES)]
