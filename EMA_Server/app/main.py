"""EMA FastAPI application entry."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as wechat_router
from app.api.web.router import router as web_router
from app.config import get_settings

settings = get_settings()

OPENAPI_TAGS = [
    {
        "name": "小程序",
        "description": "微信小程序端业务接口：登录、打卡、EMA 采集、同步与风险评估等。",
    },
    {
        "name": "Web 管理",
        "description": "Web 管理端预留接口：反馈录入、健康检查等。",
    },
    {
        "name": "系统",
        "description": "服务健康检查。",
    },
]

app = FastAPI(
    title="EMA 服务端 API",
    description=(
        "心理健康 EMA（Ecological Momentary Assessment）监测后端。\n\n"
        "认证方式：除登录外，请求头需携带 `Authorization: Bearer <token>`。"
    ),
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wechat_router, prefix=settings.api_prefix, tags=["小程序"])
app.include_router(web_router, prefix=settings.web_api_prefix, tags=["Web 管理"])


@app.get("/health", summary="健康检查", description="检查服务是否正常运行。", tags=["系统"])
def health():
    return {"status": "ok"}
