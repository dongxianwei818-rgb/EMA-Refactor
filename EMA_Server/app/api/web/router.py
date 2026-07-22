"""Web 管理端 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_web_admin, get_web_db
from app.schemas import (
    ApiResponse,
    FeedbackCreateRequest,
    WebUserCreateRequest,
    WebUserUpdateRequest,
)
from app.services.admin_risk_service import (
    get_user_risk_warning,
    list_user_risk_options,
    list_user_risk_warnings,
)
from app.services.admin_trends_service import (
    get_user_trends_overview,
    list_user_trend_summaries,
)
from app.services.feedback_service import create_feedback_record
from app.services.web_user_admin_service import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter()


@router.get(
    "/health",
    response_model=ApiResponse,
    summary="Web API 健康检查",
    description="确认 Web 管理端 API 路由可用。",
)
def web_health():
    return ApiResponse(message="web api ready")


@router.post(
    "/feedback",
    response_model=ApiResponse,
    summary="录入反馈记录",
    description="研究人员在 Web 端为用户录入非诊断性反馈，写入 feedback_records 表。",
)
def web_feedback_create(
    body: FeedbackCreateRequest,
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    try:
        data = create_feedback_record(
            db,
            user_id=body.user_id,
            task_date=body.task_date,
            session_id=body.session_id,
            feedback_type=body.feedback_type,
            content=body.content,
        )
        return ApiResponse(data=data, message="反馈已录入")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/users",
    response_model=ApiResponse,
    summary="用户列表",
    description="管理员分页查询 ema_web 用户。",
)
def web_users_list(
    keyword: str | None = Query(default=None, description="用户名模糊搜索"),
    role: int | None = Query(default=None, description="角色筛选：0/1"),
    study_status: str | None = Query(default=None, description="研究状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    data = list_users(
        db,
        keyword=keyword,
        role=role,
        study_status=study_status,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=data)


@router.get(
    "/users/{user_id}",
    response_model=ApiResponse,
    summary="用户详情",
)
def web_users_get(
    user_id: int,
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    try:
        return ApiResponse(data=get_user(db, user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/users",
    response_model=ApiResponse,
    summary="创建用户",
)
def web_users_create(
    body: WebUserCreateRequest,
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    try:
        data = create_user(
            db,
            user_name=body.user_name,
            psw=body.psw,
            role=body.role,
            research_id=body.research_id,
            study_status=body.study_status,
        )
        return ApiResponse(data=data, message="用户已创建")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put(
    "/users/{user_id}",
    response_model=ApiResponse,
    summary="更新用户",
)
def web_users_update(
    user_id: int,
    body: WebUserUpdateRequest,
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    payload = body.model_dump(exclude_unset=True)
    try:
        data = update_user(
            db,
            user_id,
            user_name=payload.get("user_name"),
            psw=payload.get("psw"),
            role=payload.get("role"),
            research_id=payload.get("research_id"),
            study_status=payload.get("study_status"),
            research_id_set="research_id" in payload,
        )
        return ApiResponse(data=data, message="用户已更新")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/users/{user_id}",
    response_model=ApiResponse,
    summary="删除用户",
)
def web_users_delete(
    user_id: int,
    db: Session = Depends(get_web_db),
    admin=Depends(get_current_web_admin),
):
    try:
        data = delete_user(db, user_id, operator_id=admin.id)
        return ApiResponse(data=data, message="用户已删除")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/trends/users",
    response_model=ApiResponse,
    summary="普通用户趋势分析列表",
    description="按风险指数从高到低返回普通用户趋势摘要，供管理员总览。",
)
def web_trends_users_list(
    keyword: str | None = Query(default=None, description="用户名/研究编号模糊搜索"),
    study_status: str | None = Query(default=None, description="研究状态"),
    level: str | None = Query(default=None, description="风险等级：high/medium/low/unknown"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    data = list_user_trend_summaries(
        db,
        keyword=keyword,
        study_status=study_status,
        level=level,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=data)


@router.get(
    "/trends/users/{user_id}/overview",
    response_model=ApiResponse,
    summary="指定用户趋势分析详情",
    description="管理员查看某一普通用户的完整趋势概览（风险/特征/历史）。",
)
def web_trends_user_overview(
    user_id: int,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    try:
        return ApiResponse(data=get_user_trends_overview(db, user_id, days=days))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/risk/users",
    response_model=ApiResponse,
    summary="普通用户风险预警列表",
    description="按风险等级严重程度从高到低返回普通用户风险预警摘要。",
)
def web_risk_users_list(
    keyword: str | None = Query(default=None, description="用户名/研究编号模糊搜索"),
    study_status: str | None = Query(default=None, description="研究状态"),
    level: str | None = Query(default=None, description="风险等级：high/medium/low/unknown"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    data = list_user_risk_warnings(
        db,
        keyword=keyword,
        study_status=study_status,
        level=level,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=data)


@router.get(
    "/risk/users/options",
    response_model=ApiResponse,
    summary="风险预警用户切换列表",
    description="返回可切换查看的普通用户简表（按风险等级排序）。",
)
def web_risk_users_options(
    exclude_user_id: int | None = Query(default=None, description="排除当前用户"),
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    return ApiResponse(data=list_user_risk_options(db, exclude_user_id=exclude_user_id))


@router.get(
    "/risk/users/{user_id}",
    response_model=ApiResponse,
    summary="指定用户风险预警详情",
    description="管理员查看某一普通用户的完整风险预警数据。",
)
def web_risk_user_detail(
    user_id: int,
    db: Session = Depends(get_web_db),
    _admin=Depends(get_current_web_admin),
):
    try:
        return ApiResponse(data=get_user_risk_warning(db, user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
