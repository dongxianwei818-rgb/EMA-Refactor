"""web / ema_web ORM models (independent package)."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import WebBase as Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_user_name", "user_name"),
        Index("idx_users_research_id", "research_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="登录用户名")
    psw: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="用户密码")
    role: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=1, comment="0=管理员；1 或空=普通用户"
    )
    research_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    study_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    session_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="退出研究时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserLoginLog(Base):
    __tablename__ = "user_login_logs"
    __table_args__ = (Index("idx_login_log_user_time", "user_id", "logged_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="登出时间")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ConsentAuthorizationLog(Base):
    __tablename__ = "consent_authorization_logs"
    __table_args__ = (Index("idx_consent_auth_user_time", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, comment="accept / revoke / exit")
    event_info: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BaselineProfile(Base):
    __tablename__ = "baseline_profiles"
    __table_args__ = (Index("idx_baseline_research_id", "research_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    research_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    major: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    only_child: Mapped[str | None] = mapped_column(String(16), nullable=True)
    housing: Mapped[str | None] = mapped_column(String(16), nullable=True)
    course_pressure: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exam_pressure: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gpa_pressure: Mapped[str | None] = mapped_column(String(16), nullable=True)
    job_pressure: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sleep_habit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exercise_freq: Mapped[str | None] = mapped_column(String(32), nullable=True)
    social_freq: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phq9_1: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phq9_2: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gad7_1: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gad7_2: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pss_1: Mapped[str | None] = mapped_column(String(16), nullable=True)
    isi_1: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ucla_1: Mapped[str | None] = mapped_column(String(16), nullable=True)
    counsel_before: Mapped[str | None] = mapped_column(String(16), nullable=True)
    treatment_now: Mapped[str | None] = mapped_column(String(16), nullable=True)
    self_harm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="完成时间"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("user_id", "submission_type", "task_date", "session_id", "client_at", name="uk_submission"),
        Index("idx_submission_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    submission_type: Mapped[str] = mapped_column(String(32), nullable=False)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmaQuestion(Base):
    __tablename__ = "ema_questions"
    __table_args__ = (
        Index("idx_ema_question_user_time", "user_id", "answered_at"),
        Index("idx_ema_question_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    answered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="答题时间")
    mood: Mapped[int] = mapped_column(Integer, nullable=False)
    stress: Mapped[int] = mapped_column(Integer, nullable=False)
    anxiety: Mapped[int] = mapped_column(Integer, nullable=False)
    lonely: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep: Mapped[int] = mapped_column(Integer, nullable=False)
    fatigue: Mapped[int] = mapped_column(Integer, nullable=False)
    function: Mapped[int] = mapped_column(Integer, nullable=False)
    negative: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmaDiary(Base):
    __tablename__ = "ema_diary"
    __table_args__ = (
        Index("idx_ema_diary_user_time", "user_id", "written_at"),
        Index("idx_ema_diary_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    written_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="提交时间")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmaVoice(Base):
    __tablename__ = "ema_voice"
    __table_args__ = (
        Index("idx_ema_voice_user_time", "user_id", "recorded_at"),
        Index("idx_ema_voice_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="录音时间")
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, comment="录音时长（秒）")
    skip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否跳过录音")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="录音文件名，跳过时为空")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmaVideo(Base):
    __tablename__ = "ema_video"
    __table_args__ = (
        Index("idx_ema_video_user_time", "user_id", "recorded_at"),
        Index("idx_ema_video_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="录制时间")
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, comment="视频时长（秒）")
    skip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否跳过视频")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="视频文件名，跳过时为空")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DailyTaskSnapshot(Base):
    __tablename__ = "daily_task_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "task_date", "session_id", name="uk_daily_task"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    tasks: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StepsRecord(Base):
    __tablename__ = "steps_records"
    __table_args__ = (UniqueConstraint("user_id", "task_date", name="uk_steps_day"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmaStep(Base):
    __tablename__ = "ema_step"
    __table_args__ = (
        Index("idx_ema_step_user_time", "user_id", "recorded_at"),
        Index("idx_ema_step_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="提交时间")
    steps: Mapped[int] = mapped_column(Integer, nullable=False, comment="当日步数")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual", comment="werun/manual/mock")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SkipEvent(Base):
    __tablename__ = "skip_events"
    __table_args__ = (
        UniqueConstraint("user_id", "media_type", "client_at", name="uk_skip_event"),
        Index("idx_skip_user_type", "user_id", "media_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), default="skip", nullable=False)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CheckinDayState(Base):
    __tablename__ = "checkin_day_states"
    __table_args__ = (UniqueConstraint("user_id", "task_date", name="uk_checkin_day"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CheckinSession(Base):
    __tablename__ = "checkin_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "task_date", "session_id", name="uk_checkin_session"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VideoDoneEvent(Base):
    __tablename__ = "video_done_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BehaviorLog(Base):
    __tablename__ = "behavior_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "module", "action", "client_at", name="uk_behavior_log"),
        Index("idx_behavior_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    route: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BehaviorMeta(Base):
    __tablename__ = "behavior_meta"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    meta_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------- 预留：多模态特性分析 ----------


class TextFeature(Base):
    __tablename__ = "text_features"
    __table_args__ = (Index("idx_text_feature_user_date", "user_id", "task_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    submission_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VoiceFeature(Base):
    __tablename__ = "voice_features"
    __table_args__ = (Index("idx_voice_feature_user_date", "user_id", "task_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    submission_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VideoFeature(Base):
    __tablename__ = "video_features"
    __table_args__ = (Index("idx_video_feature_user_date", "user_id", "task_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    submission_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BehaviorFeature(Base):
    __tablename__ = "behavior_features"
    __table_args__ = (Index("idx_behavior_feature_user_date", "user_id", "task_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QuestionsFeature(Base):
    __tablename__ = "questions_features"
    __table_args__ = (Index("idx_questions_feature_user_date", "user_id", "task_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    submission_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StepFeature(Base):
    __tablename__ = "step_features"
    __table_args__ = (Index("idx_step_feature_user_date", "user_id", "task_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    submission_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------- 预留：风险与反馈 ----------


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "task_date", "session_id", "snapshot_type", name="uk_risk_snapshot"),
        Index("idx_risk_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    snapshot_type: Mapped[str] = mapped_column(String(32), nullable=False)
    result_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"
    __table_args__ = (
        UniqueConstraint("user_id", "task_date", "session_id", "feedback_type", name="uk_feedback_session"),
        Index("idx_feedback_user_date", "user_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    task_date: Mapped[str] = mapped_column(String(16), nullable=False, comment="任务日期 YYYY-MM-DD")
    session_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="当日第几次打卡会话")
    feedback_type: Mapped[str] = mapped_column(String(32), default="non_diagnostic", nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReferralRecord(Base):
    __tablename__ = "referral_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    referred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatMessage(Base):
    """EMA_Chat 对话消息（被试 ↔ 非诊断助手）。"""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("idx_chat_user_time", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="user / assistant / system / researcher")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
