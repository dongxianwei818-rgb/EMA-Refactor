# EMA Web（Vue 3 + Element Plus）

将原 **EMA_Chat / EMA_WeChat** 能力重构为 **Vue 3 Web** 端，使用 **Element Plus** 组件库，对接 `EMA_Server` 的 `/api/v1`。

登录与后续请求使用 `client_type: "web"`，数据写入 **`ema_web`**（与小程序 `ema`、App `ema_app` 隔离）。JWT 含 `client_type`；HTTP 拦截器同时带 `X-Client-Type: web`。

## 主界面模块

底部 Tab 已移至顶栏右上角（`layouts/MainLayout.vue`），共 **6** 大模块：

| 模块 | 路由 | 页面 | 说明 |
|------|------|------|------|
| 首页 | `/home` | `views/Home.vue` | 今日反馈摘要、风险只读、快捷入口 |
| 记录 | `/records` | `views/Records.vue` | 打卡采集记录（按会话展示，API 待对接） |
| 趋势 | `/trends` | `views/Trends.vue` | 风险评估与趋势 |
| 对话 | `/chat` | `views/Chat.vue` | 非诊断支持对话 |
| 资源 | `/resources` | `views/Resources.vue` | 校园/热线等心理健康资源 |
| 我的 | `/my` | `views/My.vue` | 账号信息、退出登录、知情同意 |
| 管理 | `/users` | `views/Users.vue` | **仅管理员**：用户列表增删改查 |

**登录页**：`/login`（`views/Login.vue`）— 用户名 + 密码，调用 `POST /api/v1/auth/login` 校验 `ema_web.users`。  
默认管理员：`admin` / `123456`（`role=0`，可跳过知情同意，可见「管理」菜单）。未登录访问业务页会跳转到登录页。

用户管理 API（需管理员 JWT）：`/api/web/v1/users`（GET 列表 / POST 创建 / PUT 更新 / DELETE 删除）。

知情同意独立页：`/consent`、`/consent?mode=view`（不显示主导航）。普通用户未同意时访问业务页会跳转到 `/consent`。

---

## 启动

```bash
# 1. 后端
cd EMA_Server
python scripts/init_db.py   # 确保 ema_web 有 admin 种子用户
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Web
cd EMA_Web
npm install
npm run dev
```

浏览器打开：`http://127.0.0.1:5174` → 进入登录页，使用 `admin` / `123456` 登录后进入 `/home`。

开发代理：`/api` → `http://127.0.0.1:8000`

## 环境变量（可选）

在 `EMA_Web/.env`：

```env
VITE_API_BASE=/api/v1
```

## 说明

- UI：`element-plus` + `@element-plus/icons-vue`；入口在 `main.js` 全局注册，中文 locale。
- Web 登录为用户名密码（`user_name` / `psw`），不再使用微信 `code` mock 登录。
- 服务端 `.env` 中 `DB_NAME_WEB=ema_web`；首次部署请执行 `python scripts/init_db.py` 建齐三库并写入默认管理员。
- 对话回复为服务端规则化非诊断助手，**不作临床诊断**。
- 分库与鉴权细节见仓库根目录 `README.md`「客户端类型与分库」。
