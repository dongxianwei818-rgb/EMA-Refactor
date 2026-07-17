"""Sync local mini program storage to MySQL."""

from datetime import datetime

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.client_types import get_current_client_type
from app.models import models_for
from app.services.baseline_fields import baseline_to_profile_dict
from app.services.behavior_service import sync_behavior_batch
from app.services.checkin_service import sync_checkin_sessions_from_state
from app.services.consent_service import latest_accept_consent, record_consent_authorization
from app.services.daily_task_service import upsert_daily_tasks_batch
from app.services.datetime_fields import datetime_to_ms, ms_to_datetime, parse_client_at
from app.services.session_fields import parse_task_date
from app.services.submission_service import upsert_submission
from app.services.user_identity import auth_principal, user_principal
from app.services.user_service import ResearchIdConflictError, create_participation_user, save_baseline


def _upsert_daily_tasks(db: Session, user_id: int, daily_tasks: dict, checkin_day: dict | None = None) -> int:
    return upsert_daily_tasks_batch(db, user_id, daily_tasks, checkin_day)


def _sync_submissions(db: Session, user_id: int, submissions: list) -> int:
    count = 0
    for item in submissions or []:
        client_at = parse_client_at(item)
        upsert_submission(
            db,
            user_id,
            item.get("type"),
            parse_task_date(item, client_at),
            item.get("sessionId") or 1,
            client_at,
            item.get("payload") or {},
            commit=False,
        )
        count += 1
    return count


def _sync_skips(db: Session, user_id: int, media_type: str, skips: list) -> int:
    SkipEvent = models_for(db=db).SkipEvent
    count = 0
    for item in skips or []:
        client_at = parse_client_at(item)
        stmt = mysql_insert(SkipEvent).values(
            user_id=user_id,
            media_type=media_type,
            task_date=parse_task_date(item, client_at),
            session_id=item.get("sessionId") or 1,
            reason=item.get("reason") or "skip",
            client_at=client_at,
        )
        stmt = stmt.on_duplicate_key_update(reason=stmt.inserted.reason)
        db.execute(stmt)
        count += 1
    return count


def _sync_steps(db: Session, user_id: int, steps_history: list, steps_baseline: int | None) -> int:
    StepsRecord = models_for(db=db).StepsRecord
    count = 0
    for item in steps_history or []:
        task_date = item.get("date")
        if not task_date:
            continue
        client_at = parse_client_at(item)
        existing = (
            db.query(StepsRecord)
            .filter(StepsRecord.user_id == user_id, StepsRecord.task_date == task_date)
            .first()
        )
        if existing:
            existing.steps = item.get("steps") or 0
            existing.client_at = client_at
        else:
            db.add(
                StepsRecord(
                    user_id=user_id,
                    task_date=task_date,
                    steps=item.get("steps") or 0,
                    client_at=client_at,
                )
            )
        count += 1
    return count


def _sync_video_dates(db: Session, user_id: int, video_dates: list) -> int:
    VideoDoneEvent = models_for(db=db).VideoDoneEvent
    count = 0
    for ts in video_dates or []:
        client_at = ms_to_datetime(ts) or datetime.now()
        db.add(VideoDoneEvent(user_id=user_id, client_at=client_at))
        count += 1
    return count


def push_local_data(db: Session, user, payload: dict) -> dict:
    stats = {
        "submissions": 0,
        "daily_tasks": 0,
        "steps": 0,
        "skips": 0,
        "behavior_logs": 0,
        "video_dates": 0,
    }
    effective_user = user
    participation_recreated = False
    m = models_for(user=user, db=db)
    ConsentAuthorizationLog = m.ConsentAuthorizationLog

    if payload.get("login_count") is not None:
        effective_user.login_count = max(effective_user.login_count, int(payload["login_count"]))

    if payload.get("consent") and payload["consent"].get("at"):
        client_at = ms_to_datetime(payload["consent"]["at"])
        if client_at:
            if effective_user.study_status == "exited":
                effective_user = create_participation_user(db, effective_user)
                participation_recreated = True
                m = models_for(user=effective_user, db=db)
                ConsentAuthorizationLog = m.ConsentAuthorizationLog
            exists = (
                db.query(ConsentAuthorizationLog)
                .filter(
                    ConsentAuthorizationLog.user_id == effective_user.id,
                    ConsentAuthorizationLog.status == "accept",
                    ConsentAuthorizationLog.client_at == client_at,
                )
                .first()
            )
            if not exists:
                record_consent_authorization(
                    db,
                    effective_user,
                    "accept",
                    {"source": "sync"},
                    client_at,
                )

    if payload.get("baseline"):
        baseline = payload["baseline"]
        research_id = baseline.get("researchId") or baseline.get("research_id")
        if research_id:
            try:
                _, target_user = save_baseline(
                    db,
                    effective_user,
                    research_id,
                    baseline,
                )
                if target_user.id != effective_user.id:
                    effective_user = target_user
                    participation_recreated = True
            except ResearchIdConflictError:
                raise

    stats["submissions"] = _sync_submissions(db, effective_user.id, payload.get("submissions"))
    stats["daily_tasks"] = _upsert_daily_tasks(
        db, effective_user.id, payload.get("daily_tasks"), payload.get("checkin_day")
    )
    stats["steps"] = _sync_steps(
        db, effective_user.id, payload.get("steps_history"), payload.get("steps_baseline")
    )
    stats["skips"] = _sync_skips(db, effective_user.id, "video", payload.get("video_skips"))
    stats["skips"] += _sync_skips(db, effective_user.id, "voice", payload.get("voice_skips"))
    sync_checkin_sessions_from_state(db, effective_user.id, payload.get("checkin_day"))
    stats["behavior_logs"] = sync_behavior_batch(
        db, effective_user.id, payload.get("behavior_logs"), payload.get("behavior_meta")
    )
    stats["video_dates"] = _sync_video_dates(db, effective_user.id, payload.get("video_dates"))

    db.commit()
    db.refresh(effective_user)

    if participation_recreated:
        from app.dependencies import create_access_token

        stats["user_id"] = effective_user.id
        stats["token"] = create_access_token(
            auth_principal(effective_user), effective_user.id, get_current_client_type()
        )
        stats["participation_recreated"] = True
    return stats


def pull_user_data(db: Session, user) -> dict:
    m = models_for(user=user, db=db)
    BaselineProfile = m.BaselineProfile
    Submission = m.Submission
    DailyTaskSnapshot = m.DailyTaskSnapshot
    StepsRecord = m.StepsRecord
    SkipEvent = m.SkipEvent
    CheckinDayState = m.CheckinDayState
    CheckinSession = m.CheckinSession
    VideoDoneEvent = m.VideoDoneEvent
    BehaviorMeta = m.BehaviorMeta
    BehaviorLog = m.BehaviorLog

    baseline = db.query(BaselineProfile).filter(BaselineProfile.user_id == user.id).first()
    consent = latest_accept_consent(db, user.id, user=user)
    submissions = (
        db.query(Submission)
        .filter(Submission.user_id == user.id)
        .order_by(Submission.client_at.desc())
        .limit(300)
        .all()
    )

    # 每日任务：每个日期取最大 session_id 的快照（对应当前会话进度）
    snapshots = (
        db.query(DailyTaskSnapshot)
        .filter(DailyTaskSnapshot.user_id == user.id)
        .order_by(DailyTaskSnapshot.task_date.desc(), DailyTaskSnapshot.session_id.desc())
        .limit(90)
        .all()
    )
    daily_tasks: dict[str, dict] = {}
    for row in snapshots:
        if row.task_date not in daily_tasks:
            daily_tasks[row.task_date] = _normalize_tasks_for_pull(row.tasks)

    steps_rows = (
        db.query(StepsRecord)
        .filter(StepsRecord.user_id == user.id)
        .order_by(StepsRecord.task_date.desc())
        .limit(90)
        .all()
    )
    steps_history = [
        {
            "date": r.task_date,
            "steps": r.steps,
            "at": datetime_to_ms(r.client_at),
        }
        for r in steps_rows
    ]
    steps_baseline = None
    if len(steps_history) >= 3:
        sample = steps_history[: min(7, len(steps_history))]
        steps_baseline = round(sum(x["steps"] for x in sample) / len(sample))

    skips = (
        db.query(SkipEvent)
        .filter(SkipEvent.user_id == user.id)
        .order_by(SkipEvent.client_at.desc())
        .limit(500)
        .all()
    )
    video_skips = []
    voice_skips = []
    for s in skips:
        item = {
            "at": datetime_to_ms(s.client_at),
            "date": s.task_date,
            "sessionId": s.session_id,
            "reason": s.reason or "skip",
        }
        if s.media_type == "video":
            video_skips.append(item)
        elif s.media_type == "voice":
            voice_skips.append(item)

    today = datetime.now().strftime("%Y-%m-%d")
    checkin_day = None
    day_state = (
        db.query(CheckinDayState)
        .filter(CheckinDayState.user_id == user.id, CheckinDayState.task_date == today)
        .first()
    )
    sessions = (
        db.query(CheckinSession)
        .filter(CheckinSession.user_id == user.id, CheckinSession.task_date == today)
        .order_by(CheckinSession.session_id.asc())
        .all()
    )
    session_list = [
        {
            "id": s.session_id,
            "startedAt": datetime_to_ms(s.started_at),
            "completedAt": datetime_to_ms(s.completed_at) if s.completed_at else None,
        }
        for s in sessions
    ]
    if day_state and isinstance(day_state.state_data, dict):
        checkin_day = dict(day_state.state_data)
        checkin_day["date"] = today
        # 以 checkin_sessions 表为准补齐会话列表与当前 sessionId
        if session_list:
            by_id = {s["id"]: s for s in session_list}
            for s in checkin_day.get("sessions") or []:
                sid = s.get("id")
                if sid is None:
                    continue
                if sid not in by_id:
                    by_id[sid] = {
                        "id": sid,
                        "startedAt": s.get("startedAt"),
                        "completedAt": s.get("completedAt"),
                    }
            session_list = sorted(by_id.values(), key=lambda x: x["id"])
            checkin_day["sessions"] = session_list
            checkin_day["sessionId"] = max(
                int(day_state.session_id or 1),
                max((s["id"] for s in session_list), default=1),
            )
        else:
            checkin_day.setdefault("sessionId", day_state.session_id or 1)
            checkin_day.setdefault("sessions", [])
    elif session_list:
        checkin_day = {
            "date": today,
            "sessionId": session_list[-1]["id"],
            "sessions": session_list,
        }

    video_done = (
        db.query(VideoDoneEvent)
        .filter(VideoDoneEvent.user_id == user.id)
        .order_by(VideoDoneEvent.client_at.desc())
        .limit(100)
        .all()
    )
    video_dates = [datetime_to_ms(v.client_at) for v in video_done if v.client_at]

    meta_row = db.query(BehaviorMeta).filter(BehaviorMeta.user_id == user.id).first()
    behavior_meta = meta_row.meta_data if meta_row and isinstance(meta_row.meta_data, dict) else {}

    logs = (
        db.query(BehaviorLog)
        .filter(BehaviorLog.user_id == user.id)
        .order_by(BehaviorLog.client_at.desc())
        .limit(300)
        .all()
    )
    behavior_logs = [
        {
            "module": log.module,
            "action": log.action,
            "extra": log.extra or {},
            "route": log.route or "",
            "hour": log.hour,
            "at": datetime_to_ms(log.client_at),
        }
        for log in logs
    ]

    return {
        "openid": user_principal(user),
        "research_id": user.research_id,
        "login_count": user.login_count,
        "study_status": user.study_status,
        "consent": {"at": datetime_to_ms(consent.client_at)} if consent else None,
        "baseline": baseline_to_profile_dict(baseline) if baseline else None,
        "submissions": [
            {
                "type": s.submission_type,
                "date": s.task_date,
                "sessionId": s.session_id,
                "payload": s.payload,
                "at": datetime_to_ms(s.client_at),
            }
            for s in submissions
        ],
        "daily_tasks": daily_tasks,
        "checkin_day": checkin_day,
        "steps_history": steps_history,
        "steps_baseline": steps_baseline,
        "video_skips": video_skips,
        "voice_skips": voice_skips,
        "video_dates": video_dates,
        "behavior_meta": behavior_meta,
        "behavior_logs": behavior_logs,
    }


def _normalize_tasks_for_pull(tasks: dict | None) -> dict:
    defaults = {
        "questionnaire": False,
        "diary": False,
        "voice": False,
        "video": False,
        "steps": False,
        "videoSkipped": False,
        "voiceSkipped": False,
    }
    if not tasks or not isinstance(tasks, dict):
        return dict(defaults)
    merged = dict(defaults)
    for key in defaults:
        if key in tasks:
            merged[key] = bool(tasks[key])
    return merged
