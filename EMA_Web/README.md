# EMA Web（Vue 3 + Element Plus）

将 **EMA_WeChat** 参与者流程与 **EMA_Chat** 辅助能力重构为 **Vue 3 Web** 端，对接 `EMA_Server`。

- 参与者业务 API：`/api/v1`（`client_type: web` → 库 **`ema_web`**）
- 管理员 API：`/api/web/v1`（用户 CRUD 等）

依据需求文档 `EMA需求说明/需求说明_web.docx`（大学生心理健康风险连续监测与早期预警 · Web 端一期）。

---

## 角色与准入流程

| 角色 | `users.role` | 登录后 |
|------|--------------|--------|
| 管理员 | `0` | 直接进入主界面；跳过知情同意与基线；可见「管理」 |
| 普通用户 | `1` 或空 | 登录 → 知情同意 → 基线测评（仅一次）→ 首页打卡 |

默认管理员（`init_db` 种子）：`admin` / `123456`。

登录成功会写入：

1. `user_login_logs`（服务端）
2. `behavior_logs`（前端 `trackEvent('auth','login')` → `POST /behavior/track-log`）

---

## 功能模块（对齐需求文档）

### 1. 登录 `/login`

用户名 + 密码校验 `ema_web.users`（`POST /api/v1/auth/login`）。

### 2. 知情同意 `/consent`

普通用户首次必填；内容对齐小程序知情同意条款。同意后进入基线页。

### 3. 基线测评 `/baseline`（仅一次）

绑定 `research_id`，采集基本信息、学业/生活、筛查量表等（`POST /baseline/submit-log`）。完成后进入首页。

### 4. 首页打卡进度 `/home`

今日任务进度条 + 五项任务列表：

| 任务 | 路由 | 说明 | 落库 |
|------|------|------|------|
| 每日 EMA | `/ema/questionnaire` | 8 项 0–10 分，约 30–60 秒 | `ema_questions` |
| 文本日记 | `/ema/diary` | 30–100 字 | `ema_diary` |
| 语音任务 | `/ema/voice` | 约每 2 天，5–60 秒；可跳过 | `ema_voice` |
| 视频任务 | `/ema/video` | 约每 4 天，5–60 秒；可跳过/不露脸 | `ema_video` |
| 运动步数 | `/ema/steps` | Web **手动输入**（无微信运动解密） | `ema_step` |

支持「开始今日打卡」「重新打卡」；会话同步 `POST /checkin/session/start|complete`；完成后 `POST /risk/snapshot`。

### 5. 使用行为打点

所有关键页面 view / 提交等通过 `utils/tracker.js` 上报 `POST /behavior/track-log`，写入 `behavior_logs`（需求中的「程序使用行为」）。

### 6. 记录 `/records`

按日期 + 会话展示本地采集记录（问卷/日记/语音/视频/步数）。

### 7. 趋势 `/trends`

`GET /trends/overview`：近 7 日 EMA、步数与风险摘要。

### 8. 对话 / 资源 / 我的

| 模块 | 路由 | 说明 |
|------|------|------|
| 对话 | `/chat` | 非诊断支持对话（研究辅助，不作临床诊断） |
| 资源 | `/resources` | 热线与自助资源 |
| 我的 | `/my` | 账号、知情同意查阅、退出（写 `logout_at`） |

### 9. 管理 `/users`（仅管理员）

用户增删改查：`/api/web/v1/users`。

---

## 目录结构（关键）

```
EMA_Web/src/
  api/          auth.js, ema.js, consent.js, http.js, adminUsers.js
  constants/    consent.js, ema.js
  layouts/      MainLayout.vue, TaskShell.vue
  utils/        ema.js, tracker.js, checkin.js, emaFlow.js, records.js
  views/
    Login.vue, Consent.vue, Baseline.vue, Home.vue, …
    ema/        Questionnaire.vue, Diary.vue, Voice.vue, Video.vue, Steps.vue
```

---

## 启动

```bash
# 1. 后端
cd EMA_Server
python scripts/init_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Web
cd EMA_Web
npm install
npm run dev
```

浏览器：`http://127.0.0.1:5174`

开发代理：`/api` → `http://127.0.0.1:8000`

### 环境变量（可选）

```env
# EMA_Web/.env
VITE_API_BASE=/api/v1
VITE_WEB_API_BASE=/api/web/v1
```

---

## 普通用户验收路径

1. 用管理员在「管理」中创建普通用户（`role=1`）
2. 该用户登录 → 知情同意 → 基线（填研究编号）→ 首页
3. 「开始今日打卡」依次完成问卷 → 日记 → 语音/视频（可跳过）→ 步数
4. 「记录」可见会话条目；「趋势」在有数据后展示

---

## 说明与限制

- Web 端步数为**手动录入**；微信运动解密仅小程序可用。
- 语音/视频依赖浏览器 `MediaRecorder` / `getUserMedia`，需 HTTPS 或 localhost。
- 上传格式多为 WebM（浏览器原生）；服务端按上传文件保存。
- 密码当前与库字段 `psw` 明文比对（与一期种子管理员一致）；生产环境建议改为哈希。
- 分库与鉴权见仓库根目录 `README.md`「客户端类型与分库」。
