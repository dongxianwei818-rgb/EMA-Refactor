"""Behavior tracking: behavior_logs + behavior_meta."""

from datetime import datetime
from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models import models_for
from app.services.datetime_fields import datetime_to_ms, format_datetime, parse_client_at


def upsert_behavior_log(
    db: Session,
    user_id: int,
    item: dict[str, Any],
    *,
    commit: bool = False,
) -> None:
    BehaviorLog = models_for(db=db).BehaviorLog
    client_at = parse_client_at(item)
    stmt = mysql_insert(BehaviorLog).values(
        user_id=user_id,
        module=item.get("module") or "",
        action=item.get("action") or "",
        extra=item.get("extra"),
        route=item.get("route"),
        hour=item.get("hour"),
        client_at=client_at,
    )
    stmt = stmt.on_duplicate_key_update(
        extra=stmt.inserted.extra,
        route=stmt.inserted.route,
        hour=stmt.inserted.hour,
    )
    db.execute(stmt)
    if commit:
        db.commit()


def upsert_behavior_meta(
    db: Session,
    user_id: int,
    meta: dict[str, Any],
    *,
    commit: bool = False,
) -> None:
    BehaviorMeta = models_for(db=db).BehaviorMeta
    now = datetime.now()
    row = db.query(BehaviorMeta).filter(BehaviorMeta.user_id == user_id).first()
    if row:
        row.meta_data = meta
        row.updated_at = now
    else:
        db.add(BehaviorMeta(user_id=user_id, meta_data=meta, updated_at=now))
    if commit:
        db.commit()


def record_behavior_event(
    db: Session,
    user_id: int,
    *,
    module: str,
    action: str,
    extra: dict[str, Any] | None = None,
    route: str | None = None,
    hour: int | None = None,
    client_at: datetime,
    behavior_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    upsert_behavior_log(
        db,
        user_id,
        {
            "module": module,
            "action": action,
            "extra": extra,
            "route": route,
            "hour": hour,
            "client_at": client_at,
        },
    )
    if behavior_meta is not None:
        upsert_behavior_meta(db, user_id, behavior_meta)
    db.commit()
    return {
        "module": module,
        "action": action,
        "client_at": format_datetime(client_at),
        "at": datetime_to_ms(client_at),
    }


def sync_behavior_batch(
    db: Session,
    user_id: int,
    logs: list[dict[str, Any]] | None,
    meta: dict[str, Any] | None,
) -> int:
    count = 0
    for item in logs or []:
        upsert_behavior_log(db, user_id, item)
        count += 1
    if meta is not None:
        upsert_behavior_meta(db, user_id, meta)
    return count
