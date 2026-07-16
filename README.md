# EMA-Web
心理健康 EMA 监测项目后端服务，基于**微信小程序**、 **VUE 3**、 **Python 3.10+**、**FastAPI**、**SQLAlchemy**、**MySQL**。

为微信小程序 `EMA_WeChat`、Web 端 `EMA_Web`、App 端 `EMA_APP` 提供：用户身份与参与生命周期、EMA 多模态数据采集与持久化、本地缓存同步、多模态特性分析、风险评估与非诊断反馈；并预留 Web 管理端扩展能力。
按客户端类型分库：`wechat` → `ema`，`web` → `ema_web`，`app` → `ema_app`（登录写入 JWT 的 `client_type`，后续请求按 token 选库）。
