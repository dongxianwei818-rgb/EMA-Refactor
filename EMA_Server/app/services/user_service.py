"""User and study lifecycle."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.baseline_fields import apply_baseline_fields, parse_baseline_profile
from app.services.user_identity import is_web_user, user_principal


class ResearchIdConflictError(Exception):
    pass


def assert_research_id_available(
    db: Session,
    research_id: str,
    user_id: int,
    identity: str | None = None,
    *,
    user=None,
) -> None:
    """阻止其他用户的 active 参与记录占用该 research_id。

    wechat/app：同一 openid 的多轮参与可复用编号（排除 identity）。
    web：以 users.id 区分，不依赖 openid。
    """
    User = models_for(user=user).User
    q = db.query(User).filter(
        User.research_id == research_id,
        User.id != user_id,
        User.study_status == "active",
    )
    if hasattr(User, "openid") and identity:
        q = q.filter(User.openid != identity)
    other = q.first()
    if other:
        raise ResearchIdConflictError("该研究编号已被其他用户绑定")


def create_participation_user(db: Session, source) -> object:
    """新建一条 users 参与记录（不修改历史记录）。"""
    User = models_for(user=source).User
    if is_web_user(source):
        user = User(
            user_name=source.user_name,
            psw=getattr(source, "psw", None),
            role=getattr(source, "role", 1),
            study_status="active",
            session_key=getattr(source, "session_key", None),
        )
    else:
        user = User(
            openid=source.openid,
            study_status="active",
            session_key=source.session_key,
        )
    db.add(user)
    db.flush()
    return user


def resolve_baseline_user(db: Session, user, research_id: str):
    """退出后重新登录已新建参与记录；绑定 research_id 时直接更新当前记录，不再重复新建。"""
    if (
        user.study_status == "active"
        and user.logout_at is None
        and user.research_id == research_id
    ):
        return user

    if user.study_status == "active" and user.logout_at is None:
        return user

    if user.study_status == "exited":
        return create_participation_user(db, user)
    if user.research_id and user.research_id != research_id:
        return create_participation_user(db, user)
    return user


def record_consent(db: Session, user, action: str, client_at: datetime) -> None:
    """遗留：仅用于 exit 等非 accept/revoke 场景。"""
    ConsentRecord = models_for(user=user).ConsentRecord
    db.add(ConsentRecord(user_id=user.id, action=action, client_at=client_at))
    db.commit()


def save_baseline(db: Session, user, research_id: str, profile: dict) -> tuple:
    BaselineProfile = models_for(user=user).BaselineProfile
    target = resolve_baseline_user(db, user, research_id)
    identity = None if is_web_user(user) else user_principal(user)
    assert_research_id_available(db, research_id, target.id, identity, user=user)

    fields = parse_baseline_profile(profile)
    fields["research_id"] = research_id

    target.research_id = research_id
    target.study_status = "active"
    target.logout_at = None

    baseline = db.query(BaselineProfile).filter(BaselineProfile.user_id == target.id).first()
    if baseline:
        apply_baseline_fields(baseline, fields)
        baseline.completed_at = datetime.now()
    else:
        baseline = BaselineProfile(user_id=target.id, **fields)
        db.add(baseline)

    db.commit()
    db.refresh(baseline)
    db.refresh(target)
    return baseline, target


def exit_study(
    db: Session,
    user,
    event_info: dict | None = None,
    client_at: datetime | None = None,
) -> dict:
    from app.services.consent_service import record_consent_authorization

    return record_consent_authorization(db, user, "exit", event_info, client_at)
