"""Per-client ORM packages.

三端（wechat / web / app）统一使用 web 表结构（库 ema_web）。
``models_for(client_type)`` 仍按请求 client_type 路由，但 ORM 包均为 web。
"""

from types import ModuleType

from app.client_types import (
    CLIENT_TYPE_APP,
    CLIENT_TYPE_WEB,
    CLIENT_TYPE_WECHAT,
    get_current_client_type,
    validate_client_type,
)
import app.models.web as web_models

# 三端共用 web ORM（ema_web 表结构）
_PACKAGES: dict[str, ModuleType] = {
    CLIENT_TYPE_WECHAT: web_models,
    CLIENT_TYPE_WEB: web_models,
    CLIENT_TYPE_APP: web_models,
}


def models_for(client_type: str | None = None, user=None, db=None) -> ModuleType:
    """Return the model package for a client_type（当前均为 web 表结构）。"""
    if client_type is None and user is not None:
        from app.services.user_identity import client_type_from_user

        client_type = client_type_from_user(user)
    if client_type is None and db is not None:
        client_type = getattr(db, "info", {}).get("client_type")
    return _PACKAGES[validate_client_type(client_type or get_current_client_type())]


# 兼容旧 import：导出 web 模型
from app.models.web import (  # noqa: E402
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
