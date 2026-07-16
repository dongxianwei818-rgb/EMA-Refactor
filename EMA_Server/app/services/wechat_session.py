"""WeChat jscode2session."""

from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


async def jscode2session(code: str) -> dict[str, Any]:
    if settings.mock_wx_login or not settings.wechat_app_id:
        return {
            "openid": f"mock_openid_{code}",
            "session_key": "mock_session_key_for_dev_only",
        }

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if "openid" not in data or "session_key" not in data:
        raise ValueError(data.get("errmsg", "jscode2session 失败"))
    return data
