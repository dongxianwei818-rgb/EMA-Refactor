"""Pydantic 请求/响应模型。"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiResponse(BaseModel):
    """统一 API 响应结构。"""

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="ok", description="提示信息")
    data: Any = Field(default=None, description="响应数据")


class WxLoginRequest(BaseModel):
    """登录请求（小程序 / Web / App 共用 wx-login 换 token）。"""

    code: str = Field(..., description="wx.login 返回的临时登录凭证（Web/App 可用 mock code）")
    client_type: str = Field(
        ...,
        description="客户端类型：wechat | web | app，决定连接的数据库",
        pattern="^(wechat|web|app)$",
    )


class PasswordLoginRequest(BaseModel):
    """Web 端用户名密码登录。"""

    user_name: str = Field(..., min_length=1, max_length=64, description="登录用户名")
    psw: str = Field(..., min_length=1, max_length=128, description="登录密码")
    client_type: str = Field(
        default="web",
        description="客户端类型，密码登录仅支持 web",
        pattern="^web$",
    )


class WxLoginResponse(BaseModel):
    """登录响应。"""

    openid: str = Field(..., description="用户 openid")
    token: str = Field(..., description="JWT 访问令牌（含 client_type）")
    user_id: int = Field(..., description="用户 ID")
    client_type: str = Field(..., description="客户端类型")


class PasswordLoginResponse(BaseModel):
    """Web 密码登录响应。"""

    user_name: str = Field(..., description="登录用户名")
    token: str = Field(..., description="JWT 访问令牌（含 client_type）")
    user_id: int = Field(..., description="用户 ID")
    client_type: str = Field(..., description="客户端类型")
    role: Optional[int] = Field(default=None, description="0=管理员；1 或空=普通用户")
    research_id: Optional[str] = Field(default=None, description="研究编号")
    study_status: str = Field(..., description="研究状态")
    has_consent: bool = Field(..., description="是否已知情同意")
    has_baseline: bool = Field(..., description="是否已完成基线")


class LoginLogResponse(BaseModel):
    """登录流水响应。"""

    login_log_id: int = Field(..., description="登录记录 ID")
    user_id: int = Field(..., description="用户 ID")
    openid: str = Field(..., description="用户 openid")
    logged_at: str = Field(..., description="登录时间")
    login_count: int = Field(..., description="累计登录次数")


class LogoutLogResponse(BaseModel):
    """登出流水响应。"""

    login_log_id: Optional[int] = Field(default=None, description="对应登录记录 ID")
    user_id: int = Field(..., description="用户 ID")
    openid: str = Field(..., description="用户 openid")
    logged_at: Optional[str] = Field(default=None, description="登录时间")
    logout_at: Optional[str] = Field(default=None, description="登出时间")
    updated: bool = Field(..., description="是否成功更新登出时间")


class ConsentPayload(BaseModel):
    """知情同意时间（兼容）。"""

    at: int = Field(..., description="同意时间戳（毫秒，兼容旧版）")


class ConsentAuthorizationLogRequest(BaseModel):
    """知情同意/授权流水请求。"""

    event_info: Optional[dict[str, Any]] = Field(default=None, description="事件详情 JSON")
    client_at: Optional[str] = Field(default=None, description="客户端操作时间 YYYY-MM-DD HH:mm:ss")


class ConsentAuthorizationLogResponse(BaseModel):
    """知情同意/授权流水响应。"""

    user_id: int = Field(..., description="用户 ID")
    openid: str = Field(..., description="用户 openid")
    status: str = Field(..., description="状态：accept / revoke / exit")
    event_info: dict[str, Any] = Field(..., description="事件详情")
    client_at: str = Field(..., description="客户端操作时间")
    at: int = Field(..., description="客户端时间（毫秒，兼容）")
    created_at: str = Field(..., description="服务端入库时间")


class BaselinePayload(BaseModel):
    """基线测评载荷（兼容）。"""

    research_id: str = Field(..., description="研究编号")
    profile: dict[str, Any] = Field(..., description="基线问卷答案")
    at: Optional[int] = Field(default=None, description="完成时间（毫秒，兼容）")


class BaselineSubmitRequest(BaseModel):
    """基线测评提交请求。"""

    researchId: str = Field(..., description="研究编号")
    age: Optional[Any] = Field(default=None, description="年龄")
    grade: Optional[str] = Field(default=None, description="年级")
    major: Optional[str] = Field(default=None, description="专业大类")
    gender: Optional[str] = Field(default=None, description="性别")
    onlyChild: Optional[str] = Field(default=None, description="是否独生")
    housing: Optional[str] = Field(default=None, description="住宿情况")
    course_pressure: Optional[str] = Field(default=None, description="课程压力")
    exam_pressure: Optional[str] = Field(default=None, description="考试压力")
    gpa_pressure: Optional[str] = Field(default=None, description="绩点压力")
    job_pressure: Optional[str] = Field(default=None, description="就业压力")
    sleep_habit: Optional[str] = Field(default=None, description="睡眠习惯")
    exercise_freq: Optional[str] = Field(default=None, description="运动频率")
    social_freq: Optional[str] = Field(default=None, description="社交频率")
    phq9_1: Optional[str] = Field(default=None, description="PHQ-9：做事提不起劲")
    phq9_2: Optional[str] = Field(default=None, description="PHQ-9：心情低落")
    gad7_1: Optional[str] = Field(default=None, description="GAD-7：紧张焦虑")
    gad7_2: Optional[str] = Field(default=None, description="GAD-7：不能停止担心")
    pss_1: Optional[str] = Field(default=None, description="PSS：感到无法控制")
    isi_1: Optional[str] = Field(default=None, description="ISI：入睡困难")
    ucla_1: Optional[str] = Field(default=None, description="UCLA：缺乏陪伴感")
    counsel_before: Optional[str] = Field(default=None, description="既往心理咨询")
    treatment_now: Optional[str] = Field(default=None, description="当前治疗/用药")
    self_harm: Optional[str] = Field(default=None, description="近一月自伤想法")
    client_at: Optional[str] = Field(default=None, description="完成时间 YYYY-MM-DD HH:mm:ss")


class BehaviorTrackRequest(BaseModel):
    """行为打点请求。"""

    module: str = Field(..., min_length=1, max_length=32, description="模块名，如 home、voice")
    action: str = Field(..., min_length=1, max_length=64, description="动作名，如 view、submit")
    extra: Optional[dict[str, Any]] = Field(default=None, description="附加参数")
    route: Optional[str] = Field(default=None, max_length=128, description="页面路由")
    hour: Optional[int] = Field(default=None, ge=0, le=23, description="发生时刻（小时 0–23）")
    client_at: str = Field(..., description="客户端时间 YYYY-MM-DD HH:mm:ss")
    behavior_meta: Optional[dict[str, Any]] = Field(default=None, description="行为汇总元信息")


class CheckinSessionStartRequest(BaseModel):
    """开始打卡会话请求。"""

    task_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期 YYYY-MM-DD")
    session_id: int = Field(..., ge=1, description="当日第几次打卡会话")
    started_at: str = Field(..., description="会话开始时间 YYYY-MM-DD HH:mm:ss")
    checkin_day: Optional[dict[str, Any]] = Field(default=None, description="当日打卡状态 JSON")


class CheckinSessionCompleteRequest(BaseModel):
    """完成打卡会话请求。"""

    task_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期 YYYY-MM-DD")
    session_id: int = Field(..., ge=1, description="当日第几次打卡会话")
    completed_at: str = Field(..., description="会话完成时间 YYYY-MM-DD HH:mm:ss")
    checkin_day: Optional[dict[str, Any]] = Field(default=None, description="当日打卡状态 JSON")


class RiskSnapshotSaveRequest(BaseModel):
    """风险快照保存请求。"""

    task_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期 YYYY-MM-DD")
    session_id: int = Field(..., ge=1, description="当日第几次打卡会话")
    computed_at: Optional[str] = Field(default=None, description="计算时间 YYYY-MM-DD HH:mm:ss")


class FeedbackCreateRequest(BaseModel):
    """Web 端反馈录入请求。"""

    user_id: int = Field(..., ge=1, description="用户 ID")
    task_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期 YYYY-MM-DD")
    session_id: int = Field(default=1, ge=1, description="打卡会话编号")
    feedback_type: str = Field(default="non_diagnostic", max_length=32, description="反馈类型")
    content: dict[str, Any] = Field(..., description="反馈内容 JSON")


class ChatSendRequest(BaseModel):
    """EMA_Chat 发送消息。"""

    content: str = Field(..., min_length=1, max_length=2000, description="用户消息")


class SyncPushRequest(BaseModel):
    """本地数据批量同步请求。"""

    consent: Optional[dict[str, Any]] = Field(default=None, description="知情同意状态")
    baseline: Optional[dict[str, Any]] = Field(default=None, description="基线测评数据")
    login_count: Optional[int] = Field(default=None, description="本地登录次数")
    submissions: list[dict[str, Any]] = Field(default_factory=list, description="EMA 提交记录")
    daily_tasks: dict[str, Any] = Field(default_factory=dict, description="每日任务完成状态")
    steps_history: list[dict[str, Any]] = Field(default_factory=list, description="步数历史")
    steps_baseline: Optional[int] = Field(default=None, description="步数基线")
    video_skips: list[dict[str, Any]] = Field(default_factory=list, description="视频跳过记录")
    voice_skips: list[dict[str, Any]] = Field(default_factory=list, description="语音跳过记录")
    checkin_day: Optional[dict[str, Any]] = Field(default=None, description="当日打卡状态")
    video_dates: list[int] = Field(default_factory=list, description="视频完成时间戳列表")
    behavior_logs: list[dict[str, Any]] = Field(default_factory=list, description="行为日志")
    behavior_meta: Optional[dict[str, Any]] = Field(default=None, description="行为元信息")


class UserProfileResponse(BaseModel):
    """用户资料响应。"""

    user_id: int = Field(..., description="参与记录 id")
    openid: str = Field(
        default="",
        description="身份冗余字段：wechat/app 为 openid；web 为 users.id 字符串",
    )
    user_name: Optional[str] = Field(default=None, description="登录用户名（web）")
    role: Optional[int] = Field(default=None, description="0=管理员；1 或空=普通用户（web）")
    research_id: Optional[str] = Field(default=None, description="研究编号")
    login_count: int = Field(..., description="累计登录次数")
    study_status: str = Field(..., description="研究状态")
    has_consent: bool = Field(..., description="是否已同意知情同意")
    has_baseline: bool = Field(..., description="是否已完成基线测评")


class ConsentStatusResponse(BaseModel):
    """知情同意与授权状态响应。"""

    user_id: int = Field(..., description="参与记录 id")
    has_consent: bool = Field(..., description="最新流水是否为 accept")
    status: Optional[str] = Field(default=None, description="最新流水状态：accept / revoke / exit")
    client_at: Optional[str] = Field(default=None, description="客户端授权时间")
    at: Optional[int] = Field(default=None, description="客户端授权时间毫秒戳")


class WeRunDecryptRequest(BaseModel):
    """微信运动解密请求。"""

    code: str = Field(..., description="wx.login 返回的 code，用于刷新 session_key")
    encryptedData: str = Field(..., description="微信运动加密数据")
    iv: str = Field(..., description="加密算法初始向量")


class EmaQuestionnaireSubmitRequest(BaseModel):
    """EMA 问卷提交请求。"""

    mood: int = Field(..., ge=0, le=10, description="心情 0–10")
    stress: int = Field(..., ge=0, le=10, description="压力 0–10")
    anxiety: int = Field(..., ge=0, le=10, description="焦虑 0–10")
    lonely: int = Field(..., ge=0, le=10, description="孤独感 0–10")
    sleep: int = Field(..., ge=0, le=10, description="睡眠质量 0–10")
    fatigue: int = Field(..., ge=0, le=10, description="疲劳 0–10")
    function: int = Field(..., ge=0, le=10, description="功能受影响 0–10")
    negative: str = Field(..., description="消极想法：是/否/不愿回答")
    session_id: Optional[int] = Field(default=1, ge=1, description="打卡会话编号")
    task_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期")
    answered_at: Optional[str] = Field(default=None, description="答题时间 YYYY-MM-DD HH:mm:ss")
    client_at: Optional[str] = Field(default=None, description="客户端时间（同 answered_at）")


class EmaDiarySubmitRequest(BaseModel):
    """文本日记提交请求。"""

    text: str = Field(..., min_length=30, max_length=100, description="日记正文 30–100 字")
    length: int = Field(..., ge=30, le=100, description="字数")
    session_id: Optional[int] = Field(default=1, ge=1, description="打卡会话编号")
    task_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期")
    written_at: Optional[str] = Field(default=None, description="提交时间 YYYY-MM-DD HH:mm:ss")
    client_at: Optional[str] = Field(default=None, description="客户端时间（同 written_at）")


class EmaStepSubmitRequest(BaseModel):
    """步数打卡提交请求。"""

    steps: int = Field(..., ge=0, description="当日步数")
    source: str = Field(default="manual", pattern="^(werun|manual|mock)$", description="来源：werun/manual/mock")
    session_id: Optional[int] = Field(default=1, ge=1, description="打卡会话编号")
    task_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期")
    recorded_at: Optional[str] = Field(default=None, description="提交时间 YYYY-MM-DD HH:mm:ss")
    client_at: Optional[str] = Field(default=None, description="客户端时间（同 recorded_at）")


class EmaSubmissionSubmitRequest(BaseModel):
    """EMA 步骤统一提交请求。"""

    model_config = ConfigDict(json_schema_extra={"example": {"type": "questionnaire", "payload": {}, "session_id": 1}})

    type: str = Field(..., pattern="^(questionnaire|diary|voice|video|steps)$", description="步骤类型")
    payload: dict[str, Any] = Field(default_factory=dict, description="步骤数据 JSON")
    session_id: Optional[int] = Field(default=1, ge=1, description="打卡会话编号")
    task_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期")
    client_at: Optional[str] = Field(default=None, description="客户端提交时间 YYYY-MM-DD HH:mm:ss")


# ---------- Web 管理端：用户管理 ----------


class WebUserCreateRequest(BaseModel):
    """管理员创建用户。"""

    user_name: str = Field(..., min_length=1, max_length=64, description="登录用户名")
    psw: str = Field(..., min_length=1, max_length=128, description="登录密码")
    role: Optional[int] = Field(default=1, description="0=管理员；1=普通用户")
    research_id: Optional[str] = Field(default=None, max_length=64, description="研究编号")
    study_status: str = Field(default="active", max_length=32, description="研究状态")


class WebUserUpdateRequest(BaseModel):
    """管理员更新用户（未传字段不修改）。"""

    user_name: Optional[str] = Field(default=None, min_length=1, max_length=64, description="登录用户名")
    psw: Optional[str] = Field(default=None, min_length=1, max_length=128, description="新密码，不传则不改")
    role: Optional[int] = Field(default=None, description="0=管理员；1=普通用户")
    research_id: Optional[str] = Field(default=None, max_length=64, description="研究编号")
    study_status: Optional[str] = Field(default=None, max_length=32, description="研究状态")


class WebUserItem(BaseModel):
    """用户列表项（不含密码明文展示时可脱敏）。"""

    id: int
    user_name: str
    role: Optional[int] = None
    research_id: Optional[str] = None
    login_count: int = 0
    study_status: str = "active"
    logout_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
