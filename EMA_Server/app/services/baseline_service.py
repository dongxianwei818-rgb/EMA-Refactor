"""基线测评提交服务."""

from typing import Any

from sqlalchemy.orm import Session

from app.client_types import get_current_client_type
from app.dependencies import create_access_token
from app.services.baseline_fields import baseline_to_profile_dict
from app.services.user_identity import auth_principal, user_principal
from app.services.user_service import save_baseline


def submit_baseline_log(db: Session, user, profile: dict[str, Any]) -> dict[str, Any]:
    research_id = profile.get("researchId") or profile.get("research_id")
    if not research_id:
        raise ValueError("缺少 researchId")

    baseline, target_user = save_baseline(db, user, str(research_id), profile)
    data = baseline_to_profile_dict(baseline)
    result = {
        "user_id": target_user.id,
        "openid": user_principal(target_user),
        "research_id": baseline.research_id,
        "completed_at": baseline.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
        **data,
    }
    if hasattr(target_user, "user_name"):
        result["user_name"] = target_user.user_name
    if target_user.id != user.id:
        result["token"] = create_access_token(
            auth_principal(target_user), target_user.id, get_current_client_type()
        )
        result["participation_recreated"] = True
    return result
