"""Web 管理端：用户 CRUD（ema_web）。"""

from sqlalchemy.orm import Session

from app.client_types import CLIENT_TYPE_WEB
from app.models import models_for
from app.services.datetime_fields import format_datetime


def _serialize_user(user) -> dict:
    return {
        "id": user.id,
        "user_name": user.user_name,
        "role": user.role,
        "research_id": user.research_id,
        "login_count": user.login_count or 0,
        "study_status": user.study_status,
        "logout_at": format_datetime(user.logout_at) if user.logout_at else None,
        "created_at": format_datetime(user.created_at) if user.created_at else None,
        "updated_at": format_datetime(user.updated_at) if user.updated_at else None,
    }


def list_users(
    db: Session,
    *,
    keyword: str | None = None,
    role: int | None = None,
    study_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    User = models_for(CLIENT_TYPE_WEB).User
    q = db.query(User)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(User.user_name.like(like) | User.research_id.like(like))
    if role is not None:
        q = q.filter(User.role == role)
    if study_status:
        q = q.filter(User.study_status == study_status)

    total = q.count()
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    rows = (
        q.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_user(u) for u in rows],
    }


def get_user(db: Session, user_id: int) -> dict:
    User = models_for(CLIENT_TYPE_WEB).User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    return _serialize_user(user)


def create_user(
    db: Session,
    *,
    user_name: str,
    psw: str,
    role: int | None = 1,
    research_id: str | None = None,
    study_status: str = "active",
) -> dict:
    User = models_for(CLIENT_TYPE_WEB).User
    name = (user_name or "").strip()
    if not name:
        raise ValueError("用户名不能为空")
    if not psw:
        raise ValueError("密码不能为空")
    if role not in (0, 1, None):
        raise ValueError("role 只能为 0（管理员）或 1（普通用户）")

    exists = db.query(User).filter(User.user_name == name).first()
    if exists:
        raise ValueError(f"用户名已存在：{name}")

    user = User(
        user_name=name,
        psw=psw,
        role=1 if role is None else role,
        research_id=(research_id or None),
        study_status=study_status or "active",
        login_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


def update_user(
    db: Session,
    user_id: int,
    *,
    user_name: str | None = None,
    psw: str | None = None,
    role: int | None = None,
    research_id: str | None = None,
    study_status: str | None = None,
    research_id_set: bool = False,
) -> dict:
    User = models_for(CLIENT_TYPE_WEB).User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")

    if user_name is not None:
        name = user_name.strip()
        if not name:
            raise ValueError("用户名不能为空")
        conflict = (
            db.query(User)
            .filter(User.user_name == name, User.id != user_id)
            .first()
        )
        if conflict:
            raise ValueError(f"用户名已存在：{name}")
        user.user_name = name

    if psw is not None:
        if not psw:
            raise ValueError("密码不能为空")
        user.psw = psw

    if role is not None:
        if role not in (0, 1):
            raise ValueError("role 只能为 0（管理员）或 1（普通用户）")
        # 禁止把自己的管理员身份改掉后导致系统无管理员：仅当当前用户是唯一管理员时阻止
        if user.role == 0 and role != 0:
            admin_count = db.query(User).filter(User.role == 0).count()
            if admin_count <= 1:
                raise ValueError("不能取消系统中唯一管理员的角色")
        user.role = role

    if research_id_set:
        user.research_id = research_id or None

    if study_status is not None:
        user.study_status = study_status

    db.commit()
    db.refresh(user)
    return _serialize_user(user)


def delete_user(db: Session, user_id: int, *, operator_id: int) -> dict:
    User = models_for(CLIENT_TYPE_WEB).User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if user.id == operator_id:
        raise ValueError("不能删除当前登录账号")
    if user.role == 0:
        admin_count = db.query(User).filter(User.role == 0).count()
        if admin_count <= 1:
            raise ValueError("不能删除系统中唯一管理员")

    snapshot = _serialize_user(user)
    db.delete(user)
    db.commit()
    return snapshot
