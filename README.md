# EMA Server

心理健康 **EMA（Ecological Momentary Assessment）** 监测项目后端，基于 **Python 3.10+**、**FastAPI**、**SQLAlchemy**、**MySQL**、**微信小程序**、**VUE 3**。

为微信小程序 `EMA_WeChat`、Web 端 `EMA_Web`、App 端 `EMA_APP` 提供：用户身份与参与生命周期、EMA 多模态数据采集与持久化、本地缓存同步、多模态特性分析、风险评估与非诊断反馈；并预留 Web 管理端扩展能力。

按客户端类型分库且**模型包独立、无共用表**：`wechat` → `ema`，`web` → `ema_web`，`app` → `ema_app`（登录写入 JWT 的 `client_type`，后续请求按 token 选库；建表按各端自己的 `Base.metadata`）。

---

## 目录结构

```
EMA_Server/
├── app/
│   ├── main.py                      # FastAPI 入口，挂载 /api/v1 与 /api/web/v1
│   ├── config.py                    # 环境变量与特性分析参数（含分库库名）
│   ├── client_types.py              # client_type 常量与校验（wechat/web/app）
│   ├── database.py                  # 多 Engine / Session；WechatBase / WebBase / AppBase
│   ├── dependencies.py              # JWT（含 client_type）、get_db、get_current_user
│   ├── models/                      # 按 client 拆分的独立 ORM（无共用表）
│   │   ├── __init__.py              # models_for(client_type)；兼容导出 wechat 模型
│   │   ├── wechat/
│   │   │   ├── __init__.py          # 导出 wechat 模型类
│   │   │   └── tables.py            # wechat → ema（挂 WechatBase）
│   │   ├── web/
│   │   │   ├── __init__.py
│   │   │   └── tables.py            # web → ema_web（挂 WebBase）
│   │   └── app/
│   │       ├── __init__.py
│   │       └── tables.py            # app → ema_app（挂 AppBase）
│   ├── schemas/__init__.py          # Pydantic 请求/响应（ApiResponse 统一外壳）
│   ├── api/
│   │   ├── v1/router.py             # 小程序 / Web / App 共用业务 API（见下文）
│   │   └── web/router.py            # Web 管理端预留 API
│   └── services/
│       ├── auth_service.py          # 登录、登录/登出流水（按 client_type 写对应库）
│       ├── user_service.py          # 用户参与生命周期、research_id 绑定
│       ├── consent_service.py       # 知情同意流水
│       ├── baseline_service.py      # 基线测评提交
│       ├── checkin_service.py       # 打卡会话开始/完成
│       ├── submission_service.py    # 统一步骤提交、submissions 写入
│       ├── ema_questionnaire_service.py
│       ├── ema_diary_service.py
│       ├── ema_voice_service.py     # 语音上传 → files/voice/
│       ├── ema_video_service.py     # 视频上传 → files/video/
│       ├── ema_step_service.py      # 步数打卡（werun/manual/mock）
│       ├── behavior_service.py      # behavior_logs / behavior_meta
│       ├── sync_service.py          # 小程序 Storage 批量 push/pull
│       ├── daily_task_service.py    # 当日任务快照
│       ├── trends_service.py        # 趋势页聚合
│       ├── risk_service.py          # 风险评估与快照
│       ├── feedback_service.py      # 非诊断反馈与资源推荐
│       ├── werun_service.py         # 微信运动 encryptedData 解密
│       ├── wechat_session.py        # jscode2session
│       ├── datetime_fields.py       # 客户端时间解析
│       ├── session_fields.py        # task_date / session_id
│       └── analysis/                # 多模态特性提取（见「预留功能模块」）
│           ├── text_feature_extractor.py
│           ├── questions_feature_extractor.py
│           ├── voice_feature_extractor.py + voice_acoustic.py
│           ├── video_feature_extractor.py + video_visual.py
│           ├── step_feature_extractor.py + step_metrics.py
│           ├── behavior_feature_extractor.py + behavior_metrics.py
│           └── __init__.py          # 统一导出与 enqueue_* 占位
├── sql/
│   ├── 01_create_database.sql
│   └── 02_create_tables.sql         # 建表参考脚本（默认 USE ema；与 wechat ORM 对齐）
├── scripts/init_db.py               # 建库 + 按 client 对各自 Base.metadata.create_all
├── files/                           # 运行时媒体目录（voice/、video/）
├── requirements.txt
├── .env / .env.example
└── README.md
```

**分层约定**

| 层级              | 职责                                                 |
| ----------------- | ---------------------------------------------------- |
| `api/*/router.py` | HTTP 路由、鉴权依赖、ApiResponse 包装                |
| `services/*`      | 业务逻辑、跨表编排                                   |
| `models/<client>/` | 按 client 独立 ORM，无共用表；用 `models_for()` 取模型 |
| `schemas/`        | 入参校验与 OpenAPI 文档                              |
| `analysis/*`      | 从原始 EMA 数据提取 `*_features`，可引用其他表上下文 |

---

## 快速启动

### 1. 安装依赖

```bash
cd EMA_Server
```

### 2. 新建虚拟环境

```bash
python -m venv .venv   # Mac/Linux 也可用 python3 -m venv .venv
```

### 3. 激活

```powershell
#Windows激活（每次新开终端都要做）
.\.venv\Scripts\Activate.ps1
或：
.\.venv\Scripts\activate
若 Activate.ps1 报错，PowerShell 可能禁止运行脚本，可临时放开,再执行激活脚本：
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Mac / Linux** — 激活：
source .venv/bin/activate
```

### 4. 安装

#### Windows：

- 安装ffmpeg

> 语音 AAC 解码需要系统自身安装的ffmpeg 可执行文件（PyAV 失败时的备用）。

方式一：手动下载（最通用，推荐）

> 打开 https://www.gyan.dev/ffmpeg/builds/
> 下载 ffmpeg-release-essentials.zip（或 full 版）；
> 解压到固定目录，例如：
> C:\Tools\ffmpeg
> 解压后应有：C:\Tools\ffmpeg\bin\ffmpeg.exe
> 加入 PATH（当前用户） — 在 PowerShell 中执行：

方式二：命令安装

```
scoop install ffmpeg
#或者
choco install ffmpeg
```

- 验证ffmpeg安装

```
ffmpeg -version
```

- 安装Python依赖

```
.\.venv\Scripts\python -m pip install --only-binary av -r requirements.txt

```

#### Mac / Linux：

系统音频依赖

> 语音 AAC 解码需要系统自身安装的ffmpeg 可执行文件（PyAV 失败时的备用）。**通常不需要 pkgconf**；`av` 在常见平台有预编译 wheel，用下方脚本安装即可跳过源码编译。

```bash
#安装 ffmpeg CLI（系统级，先于 pip）
#快速安装 ffmpeg CLI（静态二进制 / apt，无需 brew 拉取大量依赖）
#ffmpeg 的作用：微信小程序录音是 AAC 格式。代码优先用 PyAV 解码，失败时回退到系统 #ffmpeg 命令行解码。只需要可执行文件，不需要 ffmpeg 开发头文件。

bash scripts/install_audio_deps.sh

# 如需要（若终端提示 PATH 未包含 ffmpeg：）
export PATH="$HOME/.local/bin:$PATH" # 持久化写入 ~/.zshrc 或 ~/.bashrc

# 安装 Python 依赖（优先 PyAV wheel，避免 pkgconf + ffmpeg 开发库）
bash scripts/install_requirements.sh

# 等价于：
.venv/bin/python -m pip install --only-binary av -r requirements.txt

# --only-binary av 是关键：
# 强制使用 PyAV 预编译 wheel（你当前环境已装 av 14.2.0）
# 跳过 brew install pkgconf ffmpeg 那套编译链
# 通常 不需要 pkgc
```

仅当 `install_requirements.sh` 提示当前 Python/平台无 wheel、需要编译 PyAV 时，再安装编译依赖：

```bash
# macOS
brew install pkgconf ffmpeg
```

- 未激活时也可直接安装（两平台通用）：

```bash
# Windows
.\.venv\Scripts\python -m pip install -r requirements.txt

# Mac / Linux
.venv/bin/python -m pip install --only-binary av -r requirements.txt
```

### 5. 安装数据库和建表

- 初始化 MySQL
  > 使用 root 账户执行建库脚本，创建 **`ema` / `ema_web` / `ema_app`** 三个库与用户 `dxw`。三端数据隔离；表结构由各自 `models/<client>/tables.py` 决定（可不同）。

```bash
# Windows
copy .env.example .env
.\.venv\Scripts\python scripts\init_db.py

# macOS / Linux
cp .env.example .env
.venv/bin/python scripts/init_db.py
```

`init_db.py` 会一次性建齐三库，并对每个 `client_type` 调用对应 `Base.metadata.create_all`（`WechatBase` → `ema`，`WebBase` → `ema_web`，`AppBase` → `ema_app`）。或者：

```bash
mysql -u root -p < sql/01_create_database.sql
python scripts/init_db.py
# 手工 SQL：02 默认 USE ema（对齐 wechat ORM）；web/app 需改库名或按各自 tables.py 维护脚本：
# mysql -u dxw -p ema < sql/02_create_tables.sql
# mysql -u dxw -p ema_web < sql/02_create_tables.sql
# mysql -u dxw -p ema_app < sql/02_create_tables.sql
```

**数据库配置（默认）**

| 项 / 客户端 | 值 / 库名 |
| ----------- | --------- |
| 用户名      | `dxw`     |
| 密码        | `1qaz!QAZ` |
| `wechat` 小程序 | `ema`（`DB_NAME`） |
| `web`（EMA_Web） | `ema_web`（`DB_NAME_WEB`） |
| `app`（EMA_APP） | `ema_app`（`DB_NAME_APP`） |

### 6. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：`GET http://127.0.0.1:8000/health`
- Swagger：`http://127.0.0.1:8000/docs`

### 7. 心理健康 EMA 监测小程序

依据《微信小程序-需求说明》实现的 8 大功能模块，原生微信小程序，无需 npm。

#### 功能对照

| 模块           | 实现要点                                                                                                                   |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **1 知情同意** | 11 项：研究目的、采集内容、用途、语音/视频、步数、风险预测、反馈、通知辅导员、退出、保存期限、联系方式                     |
| **2 基线测评** | 仅研究编号；基本信息（年龄/性别/年级/专业/独生/住宿）；学业四维压力；生活方式；PHQ/GAD/PSS/ISI/UCLA 筛查简版；风险信息可选 |
| **3 每日 EMA** | 同意知情同意后当天可打卡；8 项 0–10 分 + 消极想法三选一                                                                    |
| **4 文本日记** | 30–100 字；轮换固定提示语                                                                                                  |
| **5 语音**     | 自然化提示；30–60 秒；记录时长供行为分析                                                                                   |
| **6 视频**     | 每周 2 次；固定问题、拍摄提示、不露脸、可跳过（记录跳过率）                                                                |
| **7 步数**     | 个人基线、7 日均值、相对偏离、连续低步数天数                                                                               |
| **8 行为埋点** | 打卡时段、缺测天数、日记字数、语音时长、视频跳过、打开次数、任务耗时                                                       |

#### 流程

1. 首次：知情同意 → **立即**基线测评（**仅一次**）→ 首页
2. 基线完成后当天即可「开始今日打卡」
3. 未同意/未完成基线时自动跳转对应页面；基线不可重复提交
4. 打卡：问卷 → 日记 → 语音 → 视频 → 步数
5. 底部工具栏：**首页** | **我的**

#### 开发

1. 微信开发者工具打开 `EMA` 目录
2. 配置 `project.config.json` 中的 `appid`
3. 编译运行

#### 目录

```
utils/constants.js  — 题项与文案
utils/ema.js        — 流程与存储
utils/tracker.js    — 模块8埋点
pages/onboarding/   — 模块1、2（知情权+基础信息与基线测评）
pages/ema/          — 模块3–7
pages/home|records|my/
```

在 `EMA_WeChat/utils/constants.js` 中设置：

```javascript
API_BASE_URL: "http://127.0.0.1:8000/api/v1";
```

开发环境可在 `.env` 中设置 `MOCK_WX_LOGIN=true`，此时 `code` 会映射为 `mock_openid_{code}`。

---

#### 用户与研究编号规则

- 每个微信用户以 **openid** 作为唯一 `user_id` 关联所有数据。
- **一个用户只能绑定一个研究编号**（`research_id` 全局唯一）。
- 若需更换研究编号：在小程序「我的 → 退出研究」，服务端解除绑定后可重新入组。
- 研究编号冲突时接口返回 **HTTP 409**。

#### 用户与参与生命周期

| 概念           | 说明                                                                                   |
| -------------- | -------------------------------------------------------------------------------------- |
| `openid`       | 微信用户标识，可对应多条 `users` 参与记录                                              |
| `users.id`     | 业务主键，JWT 中 `uid`；**所有 EMA 数据按 user_id 关联**                               |
| `research_id`  | 研究编号，**同一 openid 重新入组可再次绑定**；仅阻止**其他 openid 的 active 用户**占用 |
| `study_status` | `active` / `exited` 等                                                                 |
| `logout_at`    | 退出研究时间；退出后 **保留** 历史 `research_id` 与业务数据                            |

典型流程：微信登录 → 知情同意 → 绑定 `research_id` + 基线 → 每日打卡 →（可选）退出研究 → 再次登录可新建参与或重绑同一编号。

认证：除 `POST /auth/wx-login` 外，请求头需 `Authorization: Bearer <token>`。

#### 客户端类型与分库

登录及后续业务按 `client_type` 连接不同 MySQL 库，数据互不混用；ORM 亦按端拆分，**无共用表 / 无跨端 Base**：

| `client_type` | 客户端     | 数据库    | ORM 包 / Base              |
| ------------- | ---------- | --------- | -------------------------- |
| `wechat`      | EMA_WeChat | `ema`     | `models/wechat` + `WechatBase` |
| `web`         | EMA_Web    | `ema_web` | `models/web` + `WebBase`   |
| `app`         | EMA_APP    | `ema_app` | `models/app` + `AppBase`   |

1. **登录**：`POST /auth/wx-login` 请求体必传 `client_type`（及 `code`）；服务端连对应库签发 JWT，payload 含 `sub`（openid）、`uid`、`client_type`；登录与 `get_current_user` 通过 `models_for(client_type)` 取该端 `User` 等模型。
2. **后续请求**：`get_db` 优先读 JWT 中的 `client_type` 选库；可选请求头 `X-Client-Type`（若同时携带须与 token 一致）。无 token 且无请求头时默认 `wechat`。
3. **客户端约定**：小程序登录传 `wechat`；EMA_Web 登录与 HTTP 拦截器传 `web`；App 传 `app`。
4. **改表结构**：只改对应端的 `app/models/<client>/tables.py`，再跑 `python scripts/init_db.py`（或对该库做迁移）。不要从其他端包 `import` 模型。
5. **取模型**：业务代码在已知 `client_type` 时用 `models_for`；`from app.models import User` 仍兼容导出 **wechat** 模型，表结构分叉后跨端逻辑应改为 `models_for(...)`：

```python
from app.models import models_for

m = models_for("web")          # 或 models_for()，读当前请求 ContextVar
user = db.query(m.User).filter(m.User.id == uid).first()
```

6. **注意**：旧 token 若无 `client_type` 会落到默认库 `ema`；换端或升级后请重新登录。

---

# API 模块说明

## 业务 API（`/api/v1`）

小程序 / Web / App 共用此前缀；实际读写的数据库由 JWT（或登录时的 `client_type`）决定。

所有成功响应均为统一结构：`{ "code": 0, "message": "...", "data": { ... } }`。

### 认证与用户

| 方法 | 路径               | 说明                                                                 |
| ---- | ------------------ | -------------------------------------------------------------------- |
| POST | `/auth/wx-login`   | body：`code` + **`client_type`**（`wechat`\|`web`\|`app`）→ 对应库 + JWT |
| POST | `/auth/login-log`  | 进入前台，写登录流水（当前 token 对应库）                            |
| POST | `/auth/logout-log` | 进入后台，更新 logout_at                                             |
| GET  | `/users/me`        | 当前用户资料、同意/基线状态                                          |

### 知情同意与基线

| 方法 | 路径                   | 说明               |
| ---- | ---------------------- | ------------------ |
| GET  | `/consent/status`      | 最新授权状态       |
| POST | `/consent/accept-log`  | 记录同意（流水表） |
| POST | `/consent/revoke-log`  | 记录撤回           |
| POST | `/consent/exit-log`    | 记录退出研究       |
| POST | `/consent/accept`      | 兼容旧版同意       |
| POST | `/consent/revoke`      | 兼容旧版撤回       |
| POST | `/baseline/submit-log` | 提交基线（结构化） |
| POST | `/baseline`            | 兼容旧版基线       |
| POST | `/study/exit`          | 退出研究           |

### 打卡与 EMA 采集

| 方法 | 路径                            | 说明                                        | 写入表                                 |
| ---- | ------------------------------- | ------------------------------------------- | -------------------------------------- |
| POST | `/checkin/session/start`        | 开始打卡会话                                | `checkin_sessions`                     |
| POST | `/checkin/session/complete`     | 完成打卡（**触发 behavior_features 提取**） | `checkin_sessions`                     |
| POST | `/ema/submission/submit`        | 统一步骤提交                                | `submissions` + 各 `ema_*`             |
| POST | `/ema/questionnaire/submit-log` | 8 项问卷                                    | `ema_questions` → `questions_features` |
| POST | `/ema/diary/submit-log`         | 文本日记                                    | `ema_diary` → `text_features`          |
| POST | `/ema/voice/submit-log`         | 语音上传/跳过                               | `ema_voice` → `voice_features`         |
| POST | `/ema/video/submit-log`         | 视频上传/跳过                               | `ema_video` → `video_features`         |
| POST | `/ema/step/submit-log`          | 步数打卡                                    | `ema_step` → `step_features`           |
| POST | `/steps/werun`                  | 解密微信运动步数                            | 供客户端填入步数                       |
| GET  | `/daily-tasks`                  | 当日任务完成态                              | `daily_task_snapshots`                 |

### 行为打点

| 方法 | 路径                  | 说明                                     |
| ---- | --------------------- | ---------------------------------------- |
| POST | `/behavior/track-log` | 实时行为事件 + 可选 `behavior_meta` 快照 |

### 数据同步

| 方法 | 路径         | 说明                                         |
| ---- | ------------ | -------------------------------------------- |
| POST | `/sync/push` | 批量上传本地 Storage                         |
| GET  | `/sync/pull` | 拉取服务端历史（基线、同意、submissions 等） |

### 多模态特性分析（`/analysis/*`）

提交 EMA 数据时会**自动提取**对应特性；也可手动补跑：

| 前缀                    | 说明                   |
| ----------------------- | ---------------------- |
| `/analysis/text/*`      | 日记文本特性           |
| `/analysis/questions/*` | 问卷 EMA 趋势          |
| `/analysis/voice/*`     | 语音声学 + 转写        |
| `/analysis/video/*`     | 面部视觉特性           |
| `/analysis/step/*`      | 微信运动步数个体化基线 |
| `/analysis/behavior/*`  | 小程序使用行为         |

典型端点：`POST .../extract/{id}`、`GET .../features`、`POST .../extract-pending`。

### 风险、趋势与反馈

| 方法 | 路径               | 说明                                   |
| ---- | ------------------ | -------------------------------------- |
| GET  | `/risk/assessment` | 当前风险 + 7 日预测 + 预警（可不落库） |
| POST | `/risk/snapshot`   | 打卡完成后保存风险快照                 |
| GET  | `/trends/overview` | 趋势页聚合（问卷、步数、行为统计）     |
| GET  | `/feedback`        | 非诊断性反馈                           |
| GET  | `/resources`       | 校园心理资源列表                       |

### Web 管理端预留（`/api/web/v1`）

| 方法 | 路径        | 说明                            |
| ---- | ----------- | ------------------------------- |
| GET  | `/health`   | Web API 健康检查                |
| POST | `/feedback` | 研究人员录入 `feedback_records` |

---

## 数据同步（小程序 → MySQL）

### 两条写入路径

```
EMA_WeChat
    │
    ├─ 实时 API（主路径）
    │     ema_*.js / checkin.js / tracker.js
    │         ──► POST /ema/*、/checkin/*、/behavior/track-log ...
    │         ──► 写入 ema_*、submissions、behavior_logs 等，并触发 *_features 提取
    │
    └─ 批量同步（补传 / 入组状态）
          sync.js pushToServer()
              ──► POST /sync/push
              ──► 写入 consent、baseline、步数历史、跳过记录、打卡日状态等
```

- **实时 API**：问卷、日记、语音、视频、步数、打卡会话、行为打点等，在提交时直接落库（见各 `ema_*.js`、`tracker.js`）。
- **批量同步**：`EMA_WeChat/utils/sync.js` 在登录 / onboarding 成功后由 `app.js` 调用，主要用于 consent、baseline 与本地缓存的步数/跳过/打卡状态。

### `sync.js` 当前 payload（`collectPayload()`）

| payload 字段                  | 本地 Storage 键                         | 服务端处理                                     |
| ----------------------------- | --------------------------------------- | ---------------------------------------------- |
| `consent`                     | `ema_consent`（via `ema.getConsent()`） | `consent_authorization_logs`                   |
| `baseline`                    | `ema_baseline`                          | `baseline_profiles` + `research_id` 绑定       |
| `login_count`                 | `ema_login_count`                       | 更新 `users.login_count`                       |
| `steps_history`               | `ema_steps_history`                     | `steps_records`                                |
| `steps_baseline`              | `ema_steps_baseline`                    | 步数个体基线参考                               |
| `video_skips` / `voice_skips` | `ema_video_skips` / `ema_voice_skips`   | `skip_events`                                  |
| `checkin_day`                 | `ema_checkin_day`                       | `checkin_day_states` + 补全 `checkin_sessions` |
| `video_dates`                 | `ema_video_dates`                       | `video_done_events`                            |

### 服务端额外支持的 push 字段（预留 / 扩展）

`sync_service.push_local_data` 还接受以下字段；当前小程序 `sync.js` **尚未**打包上传，可按需扩展 `collectPayload()`：

| payload 字段                      | 用途                                                      |
| --------------------------------- | --------------------------------------------------------- |
| `submissions`                     | `submissions` 表（统一步骤流水）                          |
| `daily_tasks`                     | `daily_task_snapshots`                                    |
| `behavior_logs` / `behavior_meta` | 行为批量补传（日常以 `/behavior/track-log` 实时写入为主） |

时间字段：客户端传 `client_at`（`YYYY-MM-DD HH:mm:ss`）或兼容 `*_ms` 毫秒时间戳，由 `datetime_fields.parse_client_at` 统一解析。

退出研究后再次同步同意/基线时，可能创建**新参与记录**并返回新 `token`（`participation_recreated`）。

### `GET /sync/pull`

返回当前 `user_id` 下的 consent、baseline、submissions 等，供换机或重装后恢复（`pullFromServer()`）。

---

## 特性分析功能模块

### 1. 多模态特性分析（`app/services/analysis/`）

各特性表结构一致：`user_id`、`task_date`、`session_id`、`status`、`features`(JSON)、`created_at`（`behavior_features` 另有 `computed_at`）。

| 模块          | 表                   | 数据源                            | 自动触发       | 核心类                      |
| ------------- | -------------------- | --------------------------------- | -------------- | --------------------------- |
| 问卷 EMA 趋势 | `questions_features` | `ema_questions`                   | 问卷提交后     | `QuestionsFeatureExtractor` |
| 文本特性      | `text_features`      | `ema_diary`                       | 日记提交后     | `TextFeatureExtractor`      |
| 语音特性      | `voice_features`     | `ema_voice`                       | 语音提交后     | `VoiceFeatureExtractor`     |
| 视频特性      | `video_features`     | `ema_video`                       | 视频提交后     | `VideoFeatureExtractor`     |
| 步数特性      | `step_features`      | `ema_step`                        | 步数提交后     | `StepFeatureExtractor`      |
| 行为特性      | `behavior_features`  | `behavior_logs` + `behavior_meta` | **打卡完成时** | `BehaviorFeatureExtractor`  |

提取器均可**参考其他表**（同轮问卷、基线、其他 `*_features`）生成 `context_enrichment` 与 `composite_signals`，供后续 ML 或规则引擎使用。

`enqueue_*_analysis()` 用于预写 `status=pending` 占位，便于未来接入异步任务队列。

#### 环境变量（节选）

```env
# 问卷 EMA
QUESTIONS_EMA_SPAN=7
QUESTIONS_EMA_HISTORY_DAYS=30

# 文本（可选语义向量）
TEXT_EMBEDDING_MODEL=

# 语音
VOICE_ASR_MODEL=
VOICE_STORAGE_MODE=lightweight
VOICE_DELETE_AUDIO_AFTER_EXTRACT=false

# 视频
VIDEO_FACE_BACKEND=mediapipe
VIDEO_STORAGE_MODE=lightweight

# 步数（个体化基线，非绝对阈值）
STEP_BASELINE_WINDOW_DAYS=14
STEP_LOW_RATIO=0.4

# 行为
BEHAVIOR_ON_TIME_MINUTES=60
```

特性详解（公式、指标列表）见本文末尾 [附录：特性提取说明](#附录特性提取说明)。

### 2. 风险评估（`app/services/risk_service.py`）

| 能力     | 说明                                                                       |
| -------- | -------------------------------------------------------------------------- |
| 当前风险 | 基线筛查分 + 最新 EMA 问卷 + 行为/缺测/跳过等信号                          |
| 7 日预测 | 基于近期问卷序列的趋势推演（可替换为 ML）                                  |
| 异常预警 | 消极想法、连续缺测、步数偏离、媒体跳过等                                   |
| 快照     | `POST /risk/snapshot` 写入 `risk_snapshots`（current / forecast / alerts） |

小程序端：`EMA_WeChat/utils/risk.js`（本地规则）+ `risk_api.js`（服务端评估）。

### 3. 反馈与转介（`app/services/feedback_service.py`）

| 能力       | 说明                                                               |
| ---------- | ------------------------------------------------------------------ |
| 非诊断反馈 | `GET /feedback`，含免责声明，**不作临床诊断**                      |
| 资源推荐   | `GET /resources` 或反馈内嵌 `CAMPUS_RESOURCES`                     |
| Web 录入   | `POST /api/web/v1/feedback` → `feedback_records`                   |
| 高风险转介 | 表 `referral_records` 已建；**自动写入逻辑预留**，供管理端人工跟进 |

---

## 环境变量

见 `.env.example`，主要分组：

| 分组     | 变量                                                                 |
| -------- | -------------------------------------------------------------------- |
| MySQL    | `DB_HOST`、`DB_PORT`、`DB_NAME`（wechat）、`DB_NAME_WEB`、`DB_NAME_APP`、`DB_USER`、`DB_PASSWORD` |
| 微信     | `WECHAT_APP_ID`、`WECHAT_APP_SECRET`、`MOCK_WX_LOGIN`                |
| JWT      | `JWT_SECRET`、`JWT_EXPIRE_MINUTES`（payload 含 `client_type`）       |
| 服务     | `API_PREFIX`、`WEB_API_PREFIX`、`CORS_ORIGINS`、`FILES_DIR`          |
| 特性分析 | 见上一节                                                             |

---

## 与 EMA_WeChat 的关系

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ EMA_WeChat   │  │   EMA_Web    │  │   EMA_APP    │
│ client=wechat│  │ client=web   │  │ client=app   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │ Bearer JWT      │                 │
       │ (含 client_type)│                 │
       └────────────┬────┴─────────┬───────┘
                    ▼              ▼
         ┌─────────────────────────────────────┐
         │         EMA_Server (FastAPI)         │
         │  /api/v1  按 JWT.client_type 选库    │
         │  models_for() → 对应端独立 ORM       │
         └──────┬──────────┬──────────┬────────┘
                ▼          ▼          ▼
             MySQL      MySQL      MySQL
              ema      ema_web    ema_app
           WechatBase   WebBase   AppBase
```

**数据归属原则**：以 JWT 中 `uid`（`users.id`）为准写入**当前 `client_type` 对应库**；openid 仅用于登录识别。特性分析结果在 `*_features` 表，按 `task_date` + `session_id` 与原始 EMA 行对齐。不同客户端库之间用户与业务数据隔离；表定义彼此独立，可按端演进。

### 小程序模块 ↔ 服务端对照

| 小程序 utils                 | 服务端                                | 用途            |
| ---------------------------- | ------------------------------------- | --------------- |
| `auth.js`                    | `auth_service`                        | 登录、login-log |
| `onboarding.js`              | `consent_service`、`baseline_service` | 入组流程        |
| `consent.js`                 | `/consent/*`                          | 知情同意        |
| `baseline.js`                | `/baseline/*`                         | 基线测评        |
| `checkin.js`                 | `checkin_service`                     | 打卡会话        |
| `ema_submission.js`          | `submission_service`                  | 统一步骤提交    |
| `ema_questionnaire.js`       | `ema_questionnaire_service`           | 问卷            |
| `ema_diary.js`               | `ema_diary_service`                   | 日记            |
| `ema_voice.js`               | `ema_voice_service`                   | 语音文件        |
| `ema_video.js`               | `ema_video_service`                   | 视频文件        |
| `ema_step.js` / `werun.js`   | `ema_step_service`、`werun_service`   | 步数            |
| `tracker.js` / `behavior.js` | `behavior_service`                    | 行为打点        |
| `sync.js`                    | `sync_service`                        | 本地缓存同步    |
| `risk.js` / `risk_api.js`    | `risk_service`                        | 风险评估        |
| `trends_api.js`              | `trends_service`                      | 趋势页          |
| `daily_tasks_api.js`         | `daily_task_service`                  | 任务状态        |
| `constants.js`               | `config.api_prefix`                   | API 根地址      |

---

## 开发说明

- **按端改模型**：修改 `app/models/wechat|web|app/tables.py` 之一；三端无共用表，禁止跨包引用。`init_db.py` 按 `get_base(client_type).metadata.create_all` 分别建表。
- **SQL 脚本**：`sql/02_create_tables.sql` 默认对齐 **wechat / ema**；web、app 表结构若已分叉，以对应 `tables.py` 为准，或单独维护 SQL。
- **取模型**：优先 `models_for(client_type)`；`from app.models import X` 仅为 wechat 兼容导出。
- 媒体文件存于 `files/voice/`、`files/video/`，生产环境建议对象存储 + HTTPS。
- 生产环境关闭 `MOCK_WX_LOGIN`，配置真实微信凭证。
- 登录必须传 `client_type`；换端或升级后若 token 无该字段，请重新登录以免落到默认库 `ema`。
- OpenAPI 文档以 `/docs` 为准，本 README 为架构索引。

---

## 附录：特性提取说明

### 问卷 EMA（`questions_features`）

- 对 7 项 0–10 分量表分别计算 EMA：`alpha = 2/(span+1)`，默认 `span=7`。
- 第 8 项「消极想法」单独统计近 7 日「是」的次数、连续「是」天数、 `对观测序列计算的EMAnegative_ema`。
- 参考 `baseline_profiles`、`text_features` 等同轮数据做一致性校验。

### 文本（`text_features`）

情绪词、自我指向、绝望感、压力事件、语言复杂度、语义向量（可选 `TEXT_EMBEDDING_MODEL`，否则 lexical-proxy）。

### 语音（`voice_features`）

语速、停顿、音高、响度、单调性、转写语义；可选 `faster-whisper` + ffmpeg。

### 视频（`video_features`）

FAU 代理、头姿、眼神回避、表情幅度、面部活动量、完成率/露脸意愿；MediaPipe + OpenCV。

### 步数（`step_features`）

强调**相对个人基线**的偏离（中位数基线、连续低步数、周末/工作日节律），非固定步数阈值。

### 行为（`behavior_features`）

打卡时间/节律、依从性、连续缺测、日记字数与语音时长趋势、跳过率、打开次数、任务耗时；**缺测模式本身作为信号**。

## 附录：EMA question 特性提取

### EMA 公式：

```bash
alpha = 2 / (span + 1)，默认 span=7；
按有数据的日历日聚合（同日多条取均值），消除单日波动。

第 8 项（消极想法：是/否/不愿回答）：
单独统计为negative_ema：近 7 日「是」的次数、连续「是」天数、对观测序列计算的EMAnegative_ema。
```

### 提取特性

| 字段     | 含义       |
| -------- | ---------- |
| mood     | 心情       |
| stress   | 压力       |
| anxiety  | 焦虑       |
| lonely   | 孤独感     |
| sleep    | 睡眠质量   |
| fatigue  | 疲劳       |
| function | 功能受影响 |

### 上下文增强（提高精度）：

1. baseline_profiles：个性化低情绪阈值（PHQ-9 基线高则阈值更严）
2. 同轮 text_features：问卷与日记文本一致性
3. 同轮 ema_diary：是否有日记
4. 综合信号：持续低 mood EMA、压力上升趋势、多维 distress、消极想法频次等。

### 触发方式

- 自动：提交问卷（submit_ema_questionnaire）后自动提取，返回 questions_feature_id / questions_feature_status
- API：

```
POST /analysis/questions/extract/{question_id}
GET /analysis/questions/features
POST /analysis/questions/extract-pending — 批量补跑
POST /analysis/questions/recompute?from_date= — 全量/增量重算
```

### 配置（.env 可选）

```
QUESTIONS_EMA_SPAN=7 # 平滑窗口，越大越平滑
QUESTIONS_EMA_HISTORY_DAYS=30 # trend_curves 保留点数
```

## 附录：文本特性提取

### 提取特性

| 特性       | 实现方式                                                  |
| ---------- | --------------------------------------------------------- |
| 情绪词     | 积极/消极词表匹配 + 情绪极性得分                          |
| 自我指向   | 代词与自我相关短语匹配                                    |
| 绝望感     | 绝望词表 + 问卷/基线上下文加权                            |
| 压力事件   | 学业/关系等压力词表 + 基线背景                            |
| 语言复杂度 | 字数、句长、重复表达                                      |
| 语义向量   | 可选 SentenceTransformer；未配置时用 768 维 lexical-proxy |

### 上下文增强（提高准确度）：

1. 同 user_id + task_date + session_id 的 ema_questions（如 mood 低但文本无消极词时补充信号）
2. baseline_profiles（学业/生活背景，辅助压力事件识别）
   综合风险信号 + 文本与问卷一致性评分
3. 可选：启用真实语义向量在 .env 中设置：

```bash
TEXT_EMBEDDING_MODEL=shibing624/text2vec-base-chinese
```

并安装依赖：

```bash
pip install sentence-transformers
```

未配置时仍可用 lexical-proxy 向量，不影响其他五类特性。

### 触发方式

- 自动：日记提交（ema_diary_service.submit_ema_diary）后自动提取，返回 text_feature_id / text_feature_status

- 手动/API：

```
POST /api/v1/analysis/text/extract/{diary_id} — 单条提取
GET /api/v1/analysis/text/features — 查询
POST /api/v1/analysis/text/extract-pending — 批量补跑未处理日记
```

### .env 配置：

sentence-transformers 会连带安装 torch、transformers 等，体积较大；首次加载模型还会下载权重。

在 .env 中设置TEXT_EMBEDDING_MODEL分如下3中类型：

1. 如果未设置 TEXT_EMBEDDING_MODEL，提取器将使用内置的 lexical-proxy-v1 向量。

   TEXT_EMBEDDING_MODEL=

2. 如果设置了 TEXT_EMBEDDING_MODEL，提取器将使用指定的模型。

   首次提取时会从 Hugging Face 下载模型,需要较长时间,
   国内下载模型时可设置HF_ENDPOINT=https://hf-mirror.com（需先 pip install sentence-transformers）

   HF_ENDPOINT=https://hf-mirror.com
   TEXT_EMBEDDING_MODEL=shibing624/text2vec-base-chinese

3. 如果提前下载了模型，可以设置TEXT_EMBEDDING_MODEL=你的模型路径
   本地模型（已下载到 models/text2vec-base-chinese，无需联网）
   TEXT_EMBEDDING_MODEL=models/text2vec-base-chinese

## 附录：语音特性提取

### 六类特性（对应图示）

| 特性       | 实现                                       |
| ---------- | ------------------------------------------ |
| 语速       | onset 密度 + 转写后字/分钟（有 ASR 时）    |
| 停顿时长   | RMS 能量 VAD，统计停顿次数/总时长/占比     |
| 音高变化   | librosa pyin → std、range、variation_score |
| 能量/响度  | RMS dB 均值、动态范围                      |
| 声音单调性 | 音高平坦 + 能量平坦综合得分                |
| 语音转文本 | 可选 faster-whisper；未配置则仅声学特征    |

### 上下文增强（提高精度）

1. 同轮 ema_questions / questions_features：问卷与 EMA 趋势对照
2. 同轮 ema_diary / text_features：文本与语音一致性
3. baseline_profiles：基线自伤风险等
4. 个人历史基线：对比该用户历史语速/单调性，识别相对变慢
5. 综合信号：抑郁相关声学模式（慢语速+高停顿/单调）、情感平淡、语音与问卷不一致等。

### 触发方式

- 自动：上传/跳过语音提交后自动提取，返回 voice_feature_id / voice_feature_status

- API：

```
POST /analysis/voice/extract/{voice_id}
GET /analysis/voice/features
POST /analysis/voice/extract-pending
```

### 轻量版 / 研究版

#### .env 配置：

lightweight（轻量版）：只存转写 + 声学特征，不在 features 中长期保留原始路径，提取特性后，可以删除原始 AAC

research（研究版）：知情同意后可在 features 中保留 raw_audio_path

```
VOICE_STORAGE_MODE=lightweight # lightweight | research
VOICE_ASR_MODEL= # 如 base 启用 faster-whisper
VOICE_ASR_LANGUAGE=zh
VOICE_DELETE_AUDIO_AFTER_EXTRACT=false
lightweight：只存转写 + 声学特征，不在 features 中长期保留原始路径
research：知情同意后可在 features 中保留 raw_audio_path
（可选）提取后删除原始 AAC（轻量版）
```

## 附录：视频特性提取

### 六类特性（对应图示）

| 特性         | 实现                                                   |
| ------------ | ------------------------------------------------------ |
| 面部动作单元 | 嘴宽/眉距等 landmark 代理：微笑、皱眉、眼部活动        |
| 头部姿态     | pitch/yaw/roll；低头比例、转头比例、稳定性             |
| 眼神方向     | 面部偏离中心 + 偏航 → 回避得分                         |
| 表情变化幅度 | 关键点方差 → expression_range_score                    |
| 面部活动量   | 帧间 landmark 位移 → sluggish / normal / active        |
| 视频完成率   | 时长比例 + 露脸比例；低完成/不露脸 → reluctance_signal |

默认用 MediaPipe Face Mesh；不可用时回退 OpenCV Haar 人脸检测。

### 上下文增强

1. 同轮 ema_questions / questions_features
2. 同轮 voice_features：视频–语音多模态一致性
3. 同轮 text_features / ema_diary
4. baseline_profiles：基线自伤风险
5. 个人历史基线：对比历史面部活动量、露脸比例

### 触发方式

- 自动：视频上传/跳过后自动提取，返回 video_feature_id / video_feature_status

- API：

```
POST /analysis/video/extract/{video_id}
GET /analysis/video/features
POST /analysis/video/extract-pending
```

### 配置（.env 可选）

```
VIDEO_SAMPLE_FPS=2.0
VIDEO_MAX_FRAMES=120
VIDEO_FACE_BACKEND=mediapipe
VIDEO_STORAGE_MODE=lightweight
VIDEO_DELETE_AFTER_EXTRACT=false
lightweight：只存视觉特征 JSON
research：知情同意后可保留原始视频路径
```

### 新增依赖

```
pip install -r EMA_Server/requirements.txt
新增：mediapipe（会连带安装 opencv-contrib-python 提供 cv2；numpy 已有）。勿与 opencv-python-headless 同装。
```

## 附录：微信步数特性提取

### 六项特性（对应图示）

| 指标            | 实现                                      |
| --------------- | ----------------------------------------- |
| 每日总步数      | 当日步数 + 个体化活动水平标签             |
| 近 7 天平均     | 可配置窗口（默认 7 天）                   |
| 步数波动        | 14 日 CV、规律性得分                      |
| 连续低步数天数  | 相对个人基线 × step_low_ratio（默认 40%） |
| 与个人基线差异  | 绝对/相对偏离、percent_change             |
| 周末/工作日差异 | 28 日窗口内 weekday vs weekend 均值对比   |

### 设计原则：

不用固定步数阈值，而用个人历史中位数基线（默认前 14 天）。
例如 A 平时 1 万步降到 2000 会触发 sharp_drop，B 平时 2000 步则不会误判。

### 上下文增强

1. 同轮 ema_questions：疲劳/情绪与步数一致性
2. 同轮 questions_features：EMA 持续低情绪 + 步数下降
3. baseline_profiles：运动频率、睡眠习惯

### 触发方式

- 自动：提交步数后自动提取，返回 step_feature_id / step_feature_status

- API：

```
POST /analysis/step/extract/{step_id}
GET /analysis/step/features
POST /analysis/step/extract-pending
```

### 配置（.env 可选）

```
STEP_BASELINE_WINDOW_DAYS=14
STEP_SHORT_AVG_DAYS=7
STEP_LOW_RATIO=0.4
STEP_RHYTHM_WINDOW_DAYS=28
```

## 附录：用户小程序使用行为特性

### 八类特性（对应图示）

| 指标         | 数据来源                                        | 含义                              |
| ------------ | ----------------------------------------------- | --------------------------------- |
| 打卡时间     | behavior_meta.checkinTimes + behavior_logs.hour | 均值、标准差、深夜占比 → 昼夜节律 |
| 按时完成     | checkin_sessions 起止时间                       | 依从性 / 拖延 / 负担感            |
| 连续缺测天数 | ema_questions 历史                              | 回避、低动力、压力信号            |
| 文本字数变化 | meta.diaryWordCounts                            | 表达意愿趋势                      |
| 语音时长变化 | meta.voiceDurations                             | 表达活跃度趋势                    |
| 视频跳过率   | meta + skip_events + ema_voice/video            | 回避 / 隐私顾虑                   |
| 打开次数     | meta.openCount、recheckin                       | 关注自身 / 求助倾向               |
| 任务耗时     | meta.taskDurations + logs                       | 迟疑、拖延、负担感                |

### 缺测模式

单独计算 missingness_pattern（缺测本身作为创新信号，不是“垃圾数据”）。

### 上下文增强:

1. 同轮 ema_questions / questions_features
2. 同轮 step_features（活动下降 + 行为回避）
3. baseline_profiles（自伤风险 + 媒体回避）
4. 多模态一致性评分（distress 与 avoidance 是否同步）

### 触发方式

- 自动：打卡会话完成（complete_checkin_session）后提取，返回 behavior_feature_id

- API：

```
POST /analysis/behavior/extract?task_date=&session_id=
GET /analysis/behavior/features
POST /analysis/behavior/extract-pending — 补跑已完成打卡但未生成特性的会话
```

### 配置（.env 可选）

```
BEHAVIOR_ON_TIME_MINUTES=60
BEHAVIOR_LATE_HOUR_START=22
BEHAVIOR_LATE_HOUR_END=5
```
