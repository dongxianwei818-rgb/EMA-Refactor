# 心理健康 EMA 监测小程序

依据《微信小程序-需求说明》实现的 8 大功能模块，原生微信小程序，无需 npm。

## 功能对照

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

## 流程

1. 首次：知情同意 → **立即**基线测评（**仅一次**）→ 首页
2. 基线完成后当天即可「开始今日打卡」
3. 未同意/未完成基线时自动跳转对应页面；基线不可重复提交
4. 打卡：问卷 → 日记 → 语音 → 视频 → 步数
5. 底部工具栏：**首页** | **我的**

## 开发

1. 微信开发者工具打开 `EMA` 目录
2. 配置 `project.config.json` 中的 `appid`
3. 编译运行

## 目录

```
utils/constants.js  — 题项与文案
utils/ema.js        — 流程与存储
utils/tracker.js    — 模块8埋点
pages/onboarding/   — 模块1、2（知情权+基础信息与基线测评）
pages/ema/          — 模块3–7
pages/home|records|my/
```

## 后端对接（待办）

- `getWeRunData` 服务端解密
- 语音/视频上传与特征提取、LLM embedding
- 缺测模式与风险模型、异常预警

数据现仅存本地 Storage，键名见 `utils/ema.js` 中 `KEY` 对象。

## 在 EMA_WeChat/utils/constants.js 中设置：

API*BASE_URL: "http://127.0.0.1:8000/api/v1";
开发环境可在 .env 中设置 MOCK_WX_LOGIN=true，此时 code 会映射为 mock_openid*{code}。

## 用户与研究编号规则

- 每个微信用户以 **openid** 作为唯一 `user_id` 关联所有数据。
- **一个用户只能绑定一个研究编号**（`research_id` 全局唯一）。
- 若需更换研究编号：在小程序「我的 → 退出研究」，服务端解除绑定后可重新入组。
- 研究编号冲突时接口返回 **HTTP 409**。

## 用户与参与生命周期

| 概念           | 说明                                                                                   |
| -------------- | -------------------------------------------------------------------------------------- |
| `openid`       | 微信用户标识，可对应多条 `users` 参与记录                                              |
| `users.id`     | 业务主键，JWT 中 `uid`；**所有 EMA 数据按 user_id 关联**                               |
| `research_id`  | 研究编号，**同一 openid 重新入组可再次绑定**；仅阻止**其他 openid 的 active 用户**占用 |
| `study_status` | `active` / `exited` 等                                                                 |
| `logout_at`    | 退出研究时间；退出后 **保留** 历史 `research_id` 与业务数据                            |

典型流程：微信登录 → 知情同意 → 绑定 `research_id` + 基线 → 每日打卡 →（可选）退出研究 → 再次登录 → 新建参与或重绑同一编号。

认证：除 `POST /auth/wx-login` 外，请求头需 `Authorization: Bearer <token>`。

小程序登录传 `client_type: "wechat"`，数据写入服务端库 **`ema`**（与 Web/`ema_web`、App/`ema_app` 隔离）。JWT 含 `client_type`，后续请求按 token 选库。详见仓库根目录 `README.md`「客户端类型与分库」。

# API 模块说明

## 小程序 API（`/api/v1`）

所有成功响应均为统一结构：`{ "code": 0, "message": "...", "data": { ... } }`。

### 认证与用户

| 方法 | 路径               | 说明                                              |
| ---- | ------------------ | ------------------------------------------------- |
| POST | `/auth/wx-login`   | `code` + `client_type: "wechat"` → openid + JWT   |
| POST | `/auth/login-log`  | 进入前台，写登录流水                              |
| POST | `/auth/logout-log` | 进入后台，更新 logout_at                          |
| GET  | `/users/me`        | 当前用户资料、同意/基线状态                       |

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
