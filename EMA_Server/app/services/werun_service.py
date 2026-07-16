"""WeChat WeRun (微信运动) step data decryption."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.services.wechat_crypto import decrypt_wechat_data
from app.services.wechat_session import jscode2session

settings = get_settings()
CN_TZ = timezone(timedelta(hours=8))


def _today_start_ts() -> int:
    now = datetime.now(CN_TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp())


def _extract_today_steps(step_info_list: list[dict[str, Any]]) -> int:
    today_ts = _today_start_ts()
    yesterday_ts = today_ts - 86400

    today_steps = None
    latest_steps = 0
    latest_ts = 0

    for item in step_info_list or []:
        ts = int(item.get("timestamp") or 0)
        steps = int(item.get("step") or 0)
        if ts == today_ts:
            today_steps = steps
        if ts > latest_ts:
            latest_ts = ts
            latest_steps = steps

    if today_steps is not None:
        return today_steps
    if latest_ts == yesterday_ts:
        return latest_steps
    return latest_steps


def _mock_steps(openid: str) -> int:
    base = sum(ord(c) for c in openid) % 4000
    return 3000 + base


async def decrypt_werun_steps(
    db: Session,
    user: User,
    code: str,
    encrypted_data: str,
    iv: str,
) -> dict[str, Any]:
    if settings.mock_wx_login or not settings.wechat_app_id:
        steps = _mock_steps(user.openid)
        return {
            "steps": steps,
            "date": datetime.now(CN_TZ).strftime("%Y-%m-%d"),
            "source": "mock",
            "stepInfoList": [],
        }

    session = await jscode2session(code)
    if session["openid"] != user.openid:
        raise ValueError("登录用户与当前账号不一致，请重新进入小程序")

    user.session_key = session["session_key"]
    db.commit()

    payload = decrypt_wechat_data(encrypted_data, iv, session["session_key"])
    step_info_list = payload.get("stepInfoList") or []
    steps = _extract_today_steps(step_info_list)

    return {
        "steps": steps,
        "date": datetime.now(CN_TZ).strftime("%Y-%m-%d"),
        "source": "werun",
        "stepInfoList": step_info_list[-7:],
    }
