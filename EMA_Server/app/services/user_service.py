"""User and study lifecycle."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import BaselineProfile, ConsentRecord, User
from app.services.baseline_fields import apply_baseline_fields, parse_baseline_profile


class ResearchIdConflictError(Exception):
    pass


def assert_research_id_available(
    db: Session, research_id: str, user_id: int, openid: str
) -> None:
    """仅阻止其他 openid 的 active 参与记录占用该 research_id。"""
    other = (
        db.query(User)
        .filter(
            User.research_id == research_id,
            User.id != user_id,
            User.openid != openid,
            User.study_status == "active",
        )
        .first()
    )
    if other:
        raise ResearchIdConflictError("该研究编号已被其他用户绑定")


def create_participation_user(db: Session, source: User) -> User:
    """新建一条 users 参与记录（不修改历史记录）。"""
    user = User(
        openid=source.openid,
        study_status="active",
        session_key=source.session_key,
    )
    db.add(user)
    db.flush()
    return user


def resolve_baseline_user(db: Session, user: User, research_id: str) -> User:
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


def record_consent(db: Session, user: User, action: str, client_at: datetime) -> None:
    """遗留：仅用于 exit 等非 accept/revoke 场景。"""
    db.add(ConsentRecord(user_id=user.id, action=action, client_at=client_at))
    db.commit()


def save_baseline(db: Session, user: User, research_id: str, profile: dict) -> tuple[BaselineProfile, User]:
    target = resolve_baseline_user(db, user, research_id)
    assert_research_id_available(db, research_id, target.id, user.openid)

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
    user: User,
    event_info: dict | None = None,
    client_at: datetime | None = None,
) -> dict:
    from app.services.consent_service import record_consent_authorization

    return record_consent_authorization(db, user, "exit", event_info, client_at)
