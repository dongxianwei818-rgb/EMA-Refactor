"""小程序端 FastAPI 路由。"""

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import models_for
from app.services.user_identity import user_principal
from app.schemas import (
    ApiResponse,
    BaselineSubmitRequest,
    BehaviorTrackRequest,
    ChatSendRequest,
    CheckinSessionCompleteRequest,
    CheckinSessionStartRequest,
    ConsentAuthorizationLogRequest,
    ConsentStatusResponse,
    EmaDiarySubmitRequest,
    EmaQuestionnaireSubmitRequest,
    EmaStepSubmitRequest,
    EmaSubmissionSubmitRequest,
    PasswordLoginRequest,
    RiskSnapshotSaveRequest,
    SyncPushRequest,
    UserProfileResponse,
    WeRunDecryptRequest,
    WxLoginRequest,
)
from app.services.analysis import (
    BehaviorFeatureExtractor,
    QuestionsFeatureExtractor,
    StepFeatureExtractor,
    TextFeatureExtractor,
    VideoFeatureExtractor,
    VoiceFeatureExtractor,
    extract_behavior_features_for_session,
    extract_questions_features_for_question,
    extract_step_features_for_step,
    extract_text_features_for_diary,
    extract_video_features_for_video,
    extract_voice_features_for_voice,
)
from app.services.auth_service import password_login, record_user_login, record_user_logout, wx_login
from app.services.baseline_service import submit_baseline_log
from app.services.behavior_service import record_behavior_event
from app.services.chat_service import list_messages as list_chat_messages
from app.services.chat_service import send_user_message as send_chat_message
from app.services.checkin_service import complete_checkin_session, start_checkin_session
from app.services.consent_service import get_consent_status, record_consent_authorization, user_has_consent
from app.services.daily_task_service import get_daily_tasks_for_user
from app.services.datetime_fields import parse_client_at, parse_optional_at
from app.services.ema_diary_service import submit_ema_diary
from app.services.ema_questionnaire_service import submit_ema_questionnaire
from app.services.ema_step_service import submit_ema_step
from app.services.ema_video_service import submit_ema_video, submit_ema_video_skip
from app.services.ema_voice_service import submit_ema_voice, submit_ema_voice_skip
from app.services.feedback_service import CAMPUS_RESOURCES, create_feedback_record, get_feedback
from app.services.risk_service import compute_risk_assessment, save_checkin_risk_snapshot
from app.services.session_fields import parse_task_date
from app.services.submission_service import submit_ema_submission
from app.services.sync_service import pull_user_data, push_local_data
from app.services.trends_service import get_trends_overview
from app.services.user_service import ResearchIdConflictError, exit_study
from app.services.werun_service import decrypt_werun_steps

router = APIRouter()


@router.post(
    "/auth/wx-login",
    response_model=ApiResponse,
    summary="客户端登录",
    description=(
        "使用 code 换取 openid 与 JWT。请求体须传 client_type（wechat|web|app），"
        "服务端按类型连接对应库（ema / ema_web / ema_app），并将 client_type 写入 JWT；"
        "后续请求凭 token 自动选库。"
    ),
)
async def auth_wx_login(body: WxLoginRequest):
    from app.client_types import set_current_client_type
    from app.database import create_session

    set_current_client_type(body.client_type)
    db = create_session(body.client_type)
    try:
        data = await wx_login(db, body.code, body.client_type)
        return ApiResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()


@router.post(
    "/auth/login",
    response_model=ApiResponse,
    summary="Web 用户名密码登录",
    description=(
        "校验 ema_web.users 的 user_name / psw，签发含 client_type=web 的 JWT。"
        "默认管理员：admin / 123456（role=0）。"
        "普通用户若 study_status=exited，密码正确则新建一条 active 参与记录"
        "（同名 user_name 允许多轮；唯一约束为 id+research_id），"
        "需重新知情同意并绑定基线。"
    ),
)
def auth_password_login(body: PasswordLoginRequest):
    from app.client_types import set_current_client_type
    from app.database import create_session

    set_current_client_type(body.client_type)
    db = create_session(body.client_type)
    try:
        data = password_login(db, body.user_name, body.psw, body.client_type)
        return ApiResponse(data=data, message="登录成功")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()


@router.post(
    "/auth/login-log",
    response_model=ApiResponse,
    summary="记录登录",
    description="小程序进入前台时写入登录流水，并递增用户登录次数。",
)
def auth_login_log(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    data = record_user_login(db, user)
    return ApiResponse(data=data, message="已记录登录信息")


@router.post(
    "/auth/logout-log",
    response_model=ApiResponse,
    summary="记录登出",
    description="小程序进入后台时更新最近一条登录记录的 logout_at。",
)
def auth_logout_log(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    data = record_user_logout(db, user)
    message = "已记录登出信息" if data.get("updated") else "无未结束的登录会话"
    return ApiResponse(data=data, message=message)


@router.post(
    "/behavior/track-log",
    response_model=ApiResponse,
    summary="行为打点",
    description="实时上报页面浏览、按钮点击等行为事件，写入 behavior_logs 表。",
)
def behavior_track_log(
    body: BehaviorTrackRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = record_behavior_event(
        db,
        user.id,
        module=body.module,
        action=body.action,
        extra=body.extra,
        route=body.route,
        hour=body.hour,
        client_at=parse_client_at(body.model_dump()),
        behavior_meta=body.behavior_meta,
    )
    return ApiResponse(data=data, message="已记录行为打点")


@router.post(
    "/checkin/session/start",
    response_model=ApiResponse,
    summary="开始打卡会话",
    description="记录当日新一轮打卡会话的开始时间，并初始化打卡状态。",
)
def checkin_session_start(
    body: CheckinSessionStartRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = start_checkin_session(
            db,
            user,
            task_date=body.task_date,
            session_id=body.session_id,
            started_at=parse_client_at(body.model_dump()),
            checkin_day=body.checkin_day,
        )
        return ApiResponse(data=data, message="已记录打卡会话")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/checkin/session/complete",
    response_model=ApiResponse,
    summary="完成打卡会话",
    description="当日全部 EMA 任务完成后，记录打卡会话的完成时间。",
)
def checkin_session_complete(
    body: CheckinSessionCompleteRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = complete_checkin_session(
            db,
            user,
            task_date=body.task_date,
            session_id=body.session_id,
            completed_at=parse_client_at(body.model_dump()),
            checkin_day=body.checkin_day,
        )
        return ApiResponse(data=data, message="已记录打卡完成")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/users/me",
    response_model=ApiResponse,
    summary="当前用户信息",
    description="获取当前登录用户的基本资料、研究状态及是否已完成知情同意与基线测评。",
)
def get_me(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    m = models_for(user=user, db=db)
    BaselineProfile = m.BaselineProfile
    principal = user_principal(user)
    has_baseline = db.query(BaselineProfile).filter(BaselineProfile.user_id == user.id).count() > 0
    return ApiResponse(
        data=UserProfileResponse(
            user_id=user.id,
            openid=principal,
            user_name=getattr(user, "user_name", None),
            role=getattr(user, "role", None),
            research_id=user.research_id,
            login_count=user.login_count,
            study_status=user.study_status,
            has_consent=user_has_consent(db, user.id, user=user),
            has_baseline=has_baseline,
        )
    )


@router.get(
    "/consent/status",
    response_model=ApiResponse,
    summary="查询知情同意状态",
    description="从 consent_authorization_logs 读取当前用户最新授权流水，判断是否已同意。",
)
def consent_status(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    data = get_consent_status(db, user.id, user=user)
    return ApiResponse(data=ConsentStatusResponse(**data))


@router.post(
    "/consent/accept-log",
    response_model=ApiResponse,
    summary="记录知情同意",
    description="用户同意知情同意与隐私授权时写入 consent_authorization_logs。",
)
def consent_accept_log(
    body: ConsentAuthorizationLogRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = record_consent_authorization(
            db, user, "accept", body.event_info, parse_client_at(body.model_dump())
        )
        return ApiResponse(data=data, message="已记录知情同意")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/consent/revoke-log",
    response_model=ApiResponse,
    summary="记录撤回授权",
    description="用户撤回知情同意时写入授权流水，并更新研究状态。",
)
def consent_revoke_log(
    body: ConsentAuthorizationLogRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = record_consent_authorization(
            db, user, "revoke", body.event_info, parse_client_at(body.model_dump())
        )
        return ApiResponse(data=data, message="已记录撤回授权")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/consent/exit-log",
    response_model=ApiResponse,
    summary="记录退出研究",
    description="用户退出研究时写入 status=exit 的授权流水，记录 logout_at，保留 research_id。",
)
def consent_exit_log(
    body: ConsentAuthorizationLogRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = exit_study(db, user, body.event_info, parse_client_at(body.model_dump()))
        return ApiResponse(data=data, message="已记录退出研究")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/consent/accept",
    response_model=ApiResponse,
    summary="同意知情同意（兼容）",
    description="与 accept-log 相同，保留旧路径兼容。",
)
def accept_consent(
    body: ConsentAuthorizationLogRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = record_consent_authorization(db, user, "accept", body.event_info, parse_client_at(body.model_dump()))
    return ApiResponse(data=data, message="已记录知情同意")


@router.post(
    "/consent/revoke",
    response_model=ApiResponse,
    summary="撤回授权（兼容）",
    description="与 revoke-log 相同，保留旧路径兼容。",
)
def revoke_consent(
    body: ConsentAuthorizationLogRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = record_consent_authorization(db, user, "revoke", body.event_info, parse_client_at(body.model_dump()))
    return ApiResponse(data=data, message="已记录撤回授权")


@router.post(
    "/baseline/submit-log",
    response_model=ApiResponse,
    summary="提交基线测评",
    description="保存 onboarding 基线问卷至 baseline_profiles，并绑定 research_id。",
)
def baseline_submit_log(
    body: BaselineSubmitRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submit_baseline_log(db, user, body.model_dump(exclude_none=True))
        return ApiResponse(data=data, message="基线测评已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ResearchIdConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/baseline",
    response_model=ApiResponse,
    summary="提交基线测评（简化）",
    description="与 submit-log 相同，响应仅返回 research_id。",
)
def submit_baseline(
    body: dict,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submit_baseline_log(db, user, body)
        return ApiResponse(data={"research_id": data["research_id"]}, message="基线测评已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ResearchIdConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/ema/submission/submit",
    response_model=ApiResponse,
    summary="EMA 步骤统一提交",
    description="按步骤类型（问卷/日记/语音跳过/视频跳过/步数）写入 submissions 及对应结构化表，并同步 daily_task_snapshots。",
)
def ema_submission_submit(
    body: EmaSubmissionSubmitRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submit_ema_submission(db, user, body.model_dump(exclude_none=True))
        return ApiResponse(data=data, message="EMA 步骤已同步")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/ema/questionnaire/submit-log",
    response_model=ApiResponse,
    summary="提交 EMA 问卷",
    description="保存每日 8 项 EMA 量表答案至 ema_questions 表。",
)
def ema_questionnaire_submit_log(
    body: EmaQuestionnaireSubmitRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submit_ema_questionnaire(db, user, body.model_dump(exclude_none=True))
        return ApiResponse(data=data, message="EMA 问卷已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/ema/diary/submit-log",
    response_model=ApiResponse,
    summary="提交文本日记",
    description="保存 30–100 字文本日记至 ema_diary 表。",
)
def ema_diary_submit_log(
    body: EmaDiarySubmitRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submit_ema_diary(db, user, body.model_dump(exclude_none=True))
        return ApiResponse(data=data, message="文本日志已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/analysis/text/extract/{diary_id}",
    response_model=ApiResponse,
    summary="提取日记文本特性",
    description="根据 ema_diary 记录提取六类文本特性并写入 text_features 表。",
)
def analysis_text_extract_diary(
    diary_id: int,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmaDiary = models_for(user=user, db=db).EmaDiary
    diary = (
        db.query(EmaDiary)
        .filter(EmaDiary.id == diary_id, EmaDiary.user_id == user.id)
        .first()
    )
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    try:
        row = extract_text_features_for_diary(db, diary_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="日记不存在")
    return ApiResponse(
        data={
            "text_feature_id": row.id,
            "status": row.status,
            "task_date": row.task_date,
            "session_id": row.session_id,
            "features": row.features,
        },
        message="文本特性已提取",
    )


@router.get(
    "/analysis/text/features",
    response_model=ApiResponse,
    summary="查询文本特性",
    description="按 task_date、session_id 查询当前用户的 text_features 记录。",
)
def analysis_text_features_list(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    TextFeature = models_for(user=user, db=db).TextFeature
    q = db.query(TextFeature).filter(TextFeature.user_id == user.id)
    if task_date:
        q = q.filter(TextFeature.task_date == task_date)
    if session_id is not None:
        q = q.filter(TextFeature.session_id == session_id)
    rows = q.order_by(TextFeature.id.desc()).limit(50).all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "task_date": r.task_date,
                "session_id": r.session_id,
                "status": r.status,
                "features": r.features,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )


@router.post(
    "/analysis/text/extract-pending",
    response_model=ApiResponse,
    summary="批量提取待处理日记",
    description="为尚未生成 text_features 的 ema_diary 批量执行文本特性提取。",
)
def analysis_text_extract_pending(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = TextFeatureExtractor(db).process_pending_diaries(user_id=user.id, limit=limit)
    return ApiResponse(data={"processed": count}, message=f"已处理 {count} 条日记")


@router.post(
    "/analysis/questions/extract/{question_id}",
    response_model=ApiResponse,
    summary="提取问卷 EMA 趋势特性",
    description="根据 ema_questions 记录对 7 项 0-10 分量表计算 EMA 趋势并写入 questions_features 表。",
)
def analysis_questions_extract(
    question_id: int,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmaQuestion = models_for(user=user, db=db).EmaQuestion
    record = (
        db.query(EmaQuestion)
        .filter(EmaQuestion.id == question_id, EmaQuestion.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="问卷记录不存在")
    try:
        row = extract_questions_features_for_question(db, question_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="问卷记录不存在")
    return ApiResponse(
        data={
            "questions_feature_id": row.id,
            "status": row.status,
            "task_date": row.task_date,
            "session_id": row.session_id,
            "features": row.features,
        },
        message="问卷 EMA 趋势特性已提取",
    )


@router.get(
    "/analysis/questions/features",
    response_model=ApiResponse,
    summary="查询问卷 EMA 趋势特性",
    description="按 task_date、session_id 查询当前用户的 questions_features 记录。",
)
def analysis_questions_features_list(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    QuestionsFeature = models_for(user=user, db=db).QuestionsFeature
    q = db.query(QuestionsFeature).filter(QuestionsFeature.user_id == user.id)
    if task_date:
        q = q.filter(QuestionsFeature.task_date == task_date)
    if session_id is not None:
        q = q.filter(QuestionsFeature.session_id == session_id)
    rows = q.order_by(QuestionsFeature.id.desc()).limit(50).all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "task_date": r.task_date,
                "session_id": r.session_id,
                "status": r.status,
                "features": r.features,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )


@router.post(
    "/analysis/questions/extract-pending",
    response_model=ApiResponse,
    summary="批量提取待处理问卷",
    description="为尚未生成 questions_features 的 ema_questions 批量执行 EMA 趋势提取。",
)
def analysis_questions_extract_pending(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = QuestionsFeatureExtractor(db).process_pending_questionnaires(user_id=user.id, limit=limit)
    return ApiResponse(data={"processed": count}, message=f"已处理 {count} 条问卷")


@router.post(
    "/analysis/questions/recompute",
    response_model=ApiResponse,
    summary="重算问卷 EMA 趋势",
    description="从指定日期起按时间顺序重算当前用户全部 questions_features（补历史或调参后使用）。",
)
def analysis_questions_recompute(
    from_date: str | None = Query(default=None, description="起始日期 YYYY-MM-DD，留空则全量重算"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = QuestionsFeatureExtractor(db).recompute_user_from_date(user.id, from_date)
    return ApiResponse(data={"processed": count}, message=f"已重算 {count} 条问卷趋势")


@router.post(
    "/analysis/voice/extract/{voice_id}",
    response_model=ApiResponse,
    summary="提取语音特性",
    description="根据 ema_voice 录音提取语速、停顿、音高、响度、单调性及转写语义特性，写入 voice_features。",
)
def analysis_voice_extract(
    voice_id: int,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmaVoice = models_for(user=user, db=db).EmaVoice
    voice = (
        db.query(EmaVoice)
        .filter(EmaVoice.id == voice_id, EmaVoice.user_id == user.id)
        .first()
    )
    if not voice:
        raise HTTPException(status_code=404, detail="语音记录不存在")
    try:
        row = extract_voice_features_for_voice(db, voice_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="语音记录不存在")
    return ApiResponse(
        data={
            "voice_feature_id": row.id,
            "status": row.status,
            "task_date": row.task_date,
            "session_id": row.session_id,
            "features": row.features,
        },
        message="语音特性已提取",
    )


@router.get(
    "/analysis/voice/features",
    response_model=ApiResponse,
    summary="查询语音特性",
    description="按 task_date、session_id 查询当前用户的 voice_features 记录。",
)
def analysis_voice_features_list(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    VoiceFeature = models_for(user=user, db=db).VoiceFeature
    q = db.query(VoiceFeature).filter(VoiceFeature.user_id == user.id)
    if task_date:
        q = q.filter(VoiceFeature.task_date == task_date)
    if session_id is not None:
        q = q.filter(VoiceFeature.session_id == session_id)
    rows = q.order_by(VoiceFeature.id.desc()).limit(50).all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "task_date": r.task_date,
                "session_id": r.session_id,
                "status": r.status,
                "features": r.features,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )


@router.post(
    "/analysis/voice/extract-pending",
    response_model=ApiResponse,
    summary="批量提取待处理语音",
    description="为尚未生成 voice_features 的 ema_voice 批量执行语音特性提取。",
)
def analysis_voice_extract_pending(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = VoiceFeatureExtractor(db).process_pending_voices(user_id=user.id, limit=limit)
    return ApiResponse(data={"processed": count}, message=f"已处理 {count} 条语音")


@router.post(
    "/analysis/video/extract/{video_id}",
    response_model=ApiResponse,
    summary="提取视频特性",
    description="根据 ema_video 录制提取面部动作、头姿、眼神、表情活跃度及完成率特性，写入 video_features。",
)
def analysis_video_extract(
    video_id: int,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmaVideo = models_for(user=user, db=db).EmaVideo
    video = (
        db.query(EmaVideo)
        .filter(EmaVideo.id == video_id, EmaVideo.user_id == user.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="视频记录不存在")
    try:
        row = extract_video_features_for_video(db, video_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="视频记录不存在")
    return ApiResponse(
        data={
            "video_feature_id": row.id,
            "status": row.status,
            "task_date": row.task_date,
            "session_id": row.session_id,
            "features": row.features,
        },
        message="视频特性已提取",
    )


@router.get(
    "/analysis/video/features",
    response_model=ApiResponse,
    summary="查询视频特性",
    description="按 task_date、session_id 查询当前用户的 video_features 记录。",
)
def analysis_video_features_list(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    VideoFeature = models_for(user=user, db=db).VideoFeature
    q = db.query(VideoFeature).filter(VideoFeature.user_id == user.id)
    if task_date:
        q = q.filter(VideoFeature.task_date == task_date)
    if session_id is not None:
        q = q.filter(VideoFeature.session_id == session_id)
    rows = q.order_by(VideoFeature.id.desc()).limit(50).all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "task_date": r.task_date,
                "session_id": r.session_id,
                "status": r.status,
                "features": r.features,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )


@router.post(
    "/analysis/video/extract-pending",
    response_model=ApiResponse,
    summary="批量提取待处理视频",
    description="为尚未生成 video_features 的 ema_video 批量执行视频特性提取。",
)
def analysis_video_extract_pending(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = VideoFeatureExtractor(db).process_pending_videos(user_id=user.id, limit=limit)
    return ApiResponse(data={"processed": count}, message=f"已处理 {count} 条视频")


@router.post(
    "/analysis/step/extract/{step_id}",
    response_model=ApiResponse,
    summary="提取步数特性",
    description="根据 ema_step 记录计算个体化步数基线、波动、连续低步数及周末/工作日节律，写入 step_features。",
)
def analysis_step_extract(
    step_id: int,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmaStep = models_for(user=user, db=db).EmaStep
    record = (
        db.query(EmaStep)
        .filter(EmaStep.id == step_id, EmaStep.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="步数记录不存在")
    try:
        row = extract_step_features_for_step(db, step_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="步数记录不存在")
    return ApiResponse(
        data={
            "step_feature_id": row.id,
            "status": row.status,
            "task_date": row.task_date,
            "session_id": row.session_id,
            "features": row.features,
        },
        message="步数特性已提取",
    )


@router.get(
    "/analysis/step/features",
    response_model=ApiResponse,
    summary="查询步数特性",
    description="按 task_date、session_id 查询当前用户的 step_features 记录。",
)
def analysis_step_features_list(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    StepFeature = models_for(user=user, db=db).StepFeature
    q = db.query(StepFeature).filter(StepFeature.user_id == user.id)
    if task_date:
        q = q.filter(StepFeature.task_date == task_date)
    if session_id is not None:
        q = q.filter(StepFeature.session_id == session_id)
    rows = q.order_by(StepFeature.id.desc()).limit(50).all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "task_date": r.task_date,
                "session_id": r.session_id,
                "status": r.status,
                "features": r.features,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )


@router.post(
    "/analysis/step/extract-pending",
    response_model=ApiResponse,
    summary="批量提取待处理步数",
    description="为尚未生成 step_features 的 ema_step 批量执行步数特性提取。",
)
def analysis_step_extract_pending(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = StepFeatureExtractor(db).process_pending_steps(user_id=user.id, limit=limit)
    return ApiResponse(data={"processed": count}, message=f"已处理 {count} 条步数记录")


@router.post(
    "/analysis/behavior/extract",
    response_model=ApiResponse,
    summary="提取行为特性",
    description="根据 behavior_logs / behavior_meta 及同轮 EMA 数据提取小程序使用行为特性，写入 behavior_features。",
)
def analysis_behavior_extract(
    task_date: str = Query(..., description="任务日期 YYYY-MM-DD"),
    session_id: int = Query(default=1, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        row = extract_behavior_features_for_session(db, user.id, task_date, session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ApiResponse(
        data={
            "behavior_feature_id": row.id,
            "status": row.status,
            "task_date": row.task_date,
            "session_id": row.session_id,
            "features": row.features,
        },
        message="行为特性已提取",
    )


@router.get(
    "/analysis/behavior/features",
    response_model=ApiResponse,
    summary="查询行为特性",
    description="按 task_date、session_id 查询当前用户的 behavior_features 记录。",
)
def analysis_behavior_features_list(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    BehaviorFeature = models_for(user=user, db=db).BehaviorFeature
    q = db.query(BehaviorFeature).filter(BehaviorFeature.user_id == user.id)
    if task_date:
        q = q.filter(BehaviorFeature.task_date == task_date)
    if session_id is not None:
        q = q.filter(BehaviorFeature.session_id == session_id)
    rows = q.order_by(BehaviorFeature.id.desc()).limit(50).all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "task_date": r.task_date,
                "session_id": r.session_id,
                "status": r.status,
                "features": r.features,
                "computed_at": r.computed_at.strftime("%Y-%m-%d %H:%M:%S") if r.computed_at else None,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )


@router.post(
    "/analysis/behavior/extract-pending",
    response_model=ApiResponse,
    summary="批量提取待处理行为特性",
    description="为已完成打卡但尚未生成 behavior_features 的会话批量执行行为特性提取。",
)
def analysis_behavior_extract_pending(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = BehaviorFeatureExtractor(db).process_pending_sessions(user_id=user.id, limit=limit)
    return ApiResponse(data={"processed": count}, message=f"已处理 {count} 条行为特性")


@router.post(
    "/ema/step/submit-log",
    response_model=ApiResponse,
    summary="提交步数打卡",
    description="保存当日步数至 ema_step 表，来源可为微信运动、手动输入或 mock。",
)
def ema_step_submit_log(
    body: EmaStepSubmitRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submit_ema_step(db, user, body.model_dump(exclude_none=True))
        return ApiResponse(data=data, message="步数打卡已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/ema/voice/submit-log",
    response_model=ApiResponse,
    summary="提交语音录音",
    description="上传 AAC 录音文件或标记跳过；文件保存至服务端，元数据写入 ema_voice 表。",
)
async def ema_voice_submit_log(
    skip: bool = Form(False, description="是否跳过录音"),
    file: UploadFile | None = File(default=None, description="录音文件（AAC）"),
    duration_sec: int = Form(0, description="录音时长（秒）"),
    recorded_at: str | None = Form(default=None, description="录音时间，格式 YYYY-MM-DD HH:mm:ss"),
    recorded_at_ms: str | None = Form(default=None, description="录音时间（毫秒，兼容旧版）"),
    session_id: int = Form(1, description="当日第几次打卡会话"),
    task_date: str | None = Form(default=None, description="任务日期 YYYY-MM-DD"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sid = session_id if session_id >= 1 else 1
    at = parse_client_at({"recorded_at": recorded_at, "recorded_at_ms": recorded_at_ms})
    td = parse_task_date({"task_date": task_date}, at)
    try:
        if skip:
            data = submit_ema_voice_skip(db, user, at, sid, td)
            return ApiResponse(data=data, message="已记录跳过录音")
        if file is None:
            raise HTTPException(status_code=400, detail="未上传录音文件")
        data = await submit_ema_voice(db, user, file, duration_sec, at, sid, td)
        return ApiResponse(data=data, message="语音录音已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/ema/video/submit-log",
    response_model=ApiResponse,
    summary="提交视频录制",
    description="上传 MP4 视频文件或标记跳过；文件保存至服务端，元数据写入 ema_video 表。",
)
async def ema_video_submit_log(
    skip: bool = Form(False, description="是否跳过视频"),
    file: UploadFile | None = File(default=None, description="视频文件（MP4）"),
    duration_sec: int = Form(0, description="视频时长（秒）"),
    recorded_at: str | None = Form(default=None, description="录制时间，格式 YYYY-MM-DD HH:mm:ss"),
    recorded_at_ms: str | None = Form(default=None, description="录制时间（毫秒，兼容旧版）"),
    session_id: int = Form(1, description="当日第几次打卡会话"),
    task_date: str | None = Form(default=None, description="任务日期 YYYY-MM-DD"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sid = session_id if session_id >= 1 else 1
    at = parse_client_at({"recorded_at": recorded_at, "recorded_at_ms": recorded_at_ms})
    td = parse_task_date({"task_date": task_date}, at)
    try:
        if skip:
            data = submit_ema_video_skip(db, user, at, sid, td)
            return ApiResponse(data=data, message="已记录跳过视频")
        if file is None:
            raise HTTPException(status_code=400, detail="未上传视频文件")
        data = await submit_ema_video(db, user, file, duration_sec, at, sid, td)
        return ApiResponse(data=data, message="视频录制已保存")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/study/exit",
    response_model=ApiResponse,
    summary="退出研究",
    description="退出研究：记录 logout_at、保留 research_id；重新登录后绑定编号时更新当前参与记录。",
)
def study_exit(
    body: ConsentAuthorizationLogRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = exit_study(db, user, body.event_info, parse_client_at(body.model_dump()))
    return ApiResponse(data=data, message="已退出研究")


@router.post(
    "/sync/push",
    response_model=ApiResponse,
    summary="推送本地数据",
    description="将小程序本地缓存（基线、步数、跳过记录、打卡状态等）批量同步至服务端。",
)
def sync_push(
    body: SyncPushRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        stats = push_local_data(db, user, body.model_dump())
        return ApiResponse(data=stats, message="同步成功")
    except ResearchIdConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/sync/pull",
    response_model=ApiResponse,
    summary="拉取服务端数据",
    description="从服务端拉取用户基线、知情同意、提交记录等数据，供小程序恢复本地状态。",
)
def sync_pull(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    return ApiResponse(data=pull_user_data(db, user))


@router.get(
    "/risk/assessment",
    response_model=ApiResponse,
    summary="获取风险评估",
    description="基于基线、近期 EMA 与行为数据计算当前风险等级、预测与预警（不写入快照）。",
)
def risk_assessment(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    return ApiResponse(data=compute_risk_assessment(db, user, save_snapshot=False))


@router.post(
    "/risk/snapshot",
    response_model=ApiResponse,
    summary="保存风险快照",
    description="打卡完成后计算风险评估，并将 current/forecast/alerts 写入 risk_snapshots 表。",
)
def risk_snapshot_save(
    body: RiskSnapshotSaveRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = save_checkin_risk_snapshot(
        db,
        user,
        body.task_date,
        body.session_id,
        parse_optional_at(body.model_dump(), "computed_at"),
    )
    return ApiResponse(data=data, message="风险评估快照已保存")


@router.get(
    "/daily-tasks",
    response_model=ApiResponse,
    summary="获取每日任务进度",
    description="从 daily_task_snapshots 读取指定日期与会话的任务完成状态。",
)
def daily_tasks_get(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD，默认当天"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号，默认 1"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    td = task_date or parse_task_date({}, None)
    sid = session_id if session_id is not None and session_id >= 1 else 1
    return ApiResponse(data=get_daily_tasks_for_user(db, user.id, td, sid))


@router.get(
    "/trends/overview",
    response_model=ApiResponse,
    summary="趋势页概览",
    description="聚合近 N 日 EMA 量表、步数趋势、行为统计与风险快照，供趋势页展示。",
)
def trends_overview(
    days: int = Query(default=7, ge=1, le=30, description="统计天数，1–30"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    safe_days = max(1, min(days, 30))
    return ApiResponse(data=get_trends_overview(db, user, safe_days))


@router.get(
    "/feedback",
    response_model=ApiResponse,
    summary="获取反馈记录",
    description="只读查询当前用户的非诊断性反馈，可按 task_date、session_id 筛选。",
)
def feedback_get(
    task_date: str | None = Query(default=None, description="任务日期 YYYY-MM-DD"),
    session_id: int | None = Query(default=None, ge=1, description="打卡会话编号"),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApiResponse(data=get_feedback(db, user, task_date, session_id))


@router.get(
    "/resources",
    response_model=ApiResponse,
    summary="校园资源列表",
    description="返回预设的校园心理支持资源与联系方式。",
)
def get_resources():
    return ApiResponse(data=CAMPUS_RESOURCES)


@router.post(
    "/steps/werun",
    response_model=ApiResponse,
    summary="解密微信运动步数",
    description="使用 session_key 解密微信运动 encryptedData，返回最近 30 天步数。",
)
async def decrypt_werun(
    body: WeRunDecryptRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = await decrypt_werun_steps(
            db, user, body.code, body.encryptedData, body.iv
        )
        return ApiResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/chat/messages",
    response_model=ApiResponse,
    summary="获取 EMA_Chat 会话历史",
)
def chat_messages_get(
    limit: int = Query(default=50, ge=1, le=200),
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ApiResponse(data=list_chat_messages(db, user, limit=limit))


@router.post(
    "/chat/send",
    response_model=ApiResponse,
    summary="发送 EMA_Chat 消息并获取非诊断回复",
)
def chat_send(
    body: ChatSendRequest,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = send_chat_message(db, user, body.content)
        return ApiResponse(data=data, message="已回复")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
