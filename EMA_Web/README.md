# EMA Chat（Vue 3）

将原 **EMA_Chat 微信小程序**能力重构为 **Vue 3 Web** 端，对接 `EMA_Server` 的 `/api/v1`。

登录与后续请求使用 `client_type: "web"`，数据写入 **`ema_web`**（与小程序 `ema`、App `ema_app` 隔离）。JWT 含 `client_type`；HTTP 拦截器同时带 `X-Client-Type: web`。

## 功能对照

| 原小程序 | Vue3 页面 | API |
|----------|-----------|-----|
| 知情同意 | `/consent`、`/consent?mode=view`（`views/Consent.vue`） | `GET /consent/status`、`POST /consent/accept-log`、`POST /consent/revoke-log` |
| 首页 / 登录 | `/` Home | `POST /auth/wx-login`（`client_type: web`）、`GET /feedback`、`GET /risk/assessment` |
| 对话 | `/chat` | `GET /chat/messages`、`POST /chat/send` |
| 资源 | `/resources` | `GET /resources` |

未同意时访问首页/对话/资源会自动跳转到 `/consent`（与小程序 onboarding 一致）。
撤回授权入口在首页（对齐小程序「我的」页），撤回后重新进入 `/consent`。

## 启动

```bash
# 1. 后端
cd EMA_Server
# .env 中 MOCK_WX_LOGIN=true（开发）
python scripts/init_db.py   # 确保 chat_messages 表存在
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Chat Web
cd EMA_Web
npm install
npm run dev
```

浏览器打开：`http://127.0.0.1:5174`

开发代理：`/api` → `http://127.0.0.1:8000`

## 环境变量（可选）

在 `EMA_Web/.env`：

```env
VITE_API_BASE=/api/v1
# 与服务端 MOCK_WX_LOGIN 联调的固定 code
VITE_MOCK_LOGIN_CODE=0f1ffwll2gtyPh40gYml2wB0wl2ffwlv
```

## 说明

- Web 端无 `wx.login`，开发环境用 mock `code` 换 JWT（与 `EMA_WeChat` 联调策略一致）；登录 body 须含 `client_type: "web"`。
- 服务端 `.env` 中 `DB_NAME_WEB=ema_web`；首次部署请执行 `python scripts/init_db.py` 建齐三库。
- 对话回复为服务端规则化非诊断助手，**不作临床诊断**。
- 生产环境需改为真实微信登录或独立账号体系，并配置 HTTPS 合法域名。
- 分库与鉴权细节见仓库根目录 `README.md`「客户端类型与分库」。
