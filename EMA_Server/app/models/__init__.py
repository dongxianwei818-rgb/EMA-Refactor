"""Per-client ORM packages (no shared tables).

Use ``models_for(client_type)`` at call time when the request's client is known.
``from app.models import User`` still resolves to wechat models for backward
compatibility; prefer ``models_for(...)`` once web/app schemas diverge.
"""

from types import ModuleType

from app.client_types import (
    CLIENT_TYPE_APP,
    CLIENT_TYPE_WEB,
    CLIENT_TYPE_WECHAT,
    get_current_client_type,
    validate_client_type,
)
import app.models.app as app_models
import app.models.web as web_models
import app.models.wechat as wechat_models

_PACKAGES: dict[str, ModuleType] = {
    CLIENT_TYPE_WECHAT: wechat_models,
    CLIENT_TYPE_WEB: web_models,
    CLIENT_TYPE_APP: app_models,
}


def models_for(client_type: str | None = None, user=None, db=None) -> ModuleType:
    """Return the independent model package for a client_type.

    Prefer ``user`` / ``db`` when available so resolution works inside
    sync threadpool workers where ContextVar may fall back to default.
    """
    if client_type is None and user is not None:
        from app.services.user_identity import client_type_from_user

        client_type = client_type_from_user(user)
    if client_type is None and db is not None:
        client_type = getattr(db, "info", {}).get("client_type")
    return _PACKAGES[validate_client_type(client_type or get_current_client_type())]


# Backward-compatible re-exports (wechat). Prefer models_for() for multi-client code.
from app.models.wechat import (  # noqa: E402
    BaselineProfile,
    BehaviorFeature,
    BehaviorLog,
    BehaviorMeta,
    ChatMessage,
    CheckinDayState,
    CheckinSession,
    ConsentAuthorizationLog,
    ConsentRecord,
    DailyTaskSnapshot,
    EmaDiary,
    EmaQuestion,
    EmaStep,
    EmaVideo,
    EmaVoice,
    FeedbackRecord,
    QuestionsFeature,
    ReferralRecord,
    RiskSnapshot,
    SkipEvent,
    StepFeature,
    StepsRecord,
    Submission,
    TextFeature,
    User,
    UserLoginLog,
    VideoDoneEvent,
    VideoFeature,
    VoiceFeature,
)

__all__ = [
    "models_for",
    "BaselineProfile",
    "BehaviorFeature",
    "BehaviorLog",
    "BehaviorMeta",
    "ChatMessage",
    "CheckinDayState",
    "CheckinSession",
    "ConsentAuthorizationLog",
    "ConsentRecord",
    "DailyTaskSnapshot",
    "EmaDiary",
    "EmaQuestion",
    "EmaStep",
    "EmaVideo",
    "EmaVoice",
    "FeedbackRecord",
    "QuestionsFeature",
    "ReferralRecord",
    "RiskSnapshot",
    "SkipEvent",
    "StepFeature",
    "StepsRecord",
    "Submission",
    "TextFeature",
    "User",
    "UserLoginLog",
    "VideoDoneEvent",
    "VideoFeature",
    "VoiceFeature",
]
