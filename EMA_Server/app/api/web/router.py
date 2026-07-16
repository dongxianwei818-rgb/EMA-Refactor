"""Web 管理端预留 API。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import ApiResponse, FeedbackCreateRequest
from app.services.feedback_service import create_feedback_record

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
    db: Session = Depends(get_db),
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
