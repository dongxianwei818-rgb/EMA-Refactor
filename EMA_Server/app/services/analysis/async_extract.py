"""提交接口内的特性提取改为后台执行，避免阻塞 HTTP（模型冷启动可达数十秒）。"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from app.database import create_session

logger = logging.getLogger(__name__)


def schedule_feature_extract(client_type: str, label: str, work: Callable) -> None:
    """在独立 DB session 中后台跑提取；失败只记日志，不影响提交结果。"""

    def _run() -> None:
        db = create_session(client_type)
        try:
            work(db)
        except Exception:
            logger.exception("后台特性提取失败 (%s)", label)
        finally:
            db.close()

    threading.Thread(target=_run, name=f"ema-extract-{label}", daemon=True).start()


def schedule_text_features(client_type: str, diary_id: int) -> None:
    def work(db) -> None:
        from app.services.analysis import extract_text_features_for_diary

        extract_text_features_for_diary(db, diary_id)

    schedule_feature_extract(client_type, f"text:{diary_id}", work)


def schedule_questions_features(client_type: str, question_id: int) -> None:
    def work(db) -> None:
        from app.services.analysis import extract_questions_features_for_question

        extract_questions_features_for_question(db, question_id)

    schedule_feature_extract(client_type, f"questions:{question_id}", work)


def schedule_step_features(client_type: str, step_id: int) -> None:
    def work(db) -> None:
        from app.services.analysis import extract_step_features_for_step

        extract_step_features_for_step(db, step_id)

    schedule_feature_extract(client_type, f"step:{step_id}", work)


def schedule_voice_features(client_type: str, voice_id: int) -> None:
    def work(db) -> None:
        from app.services.analysis import extract_voice_features_for_voice

        extract_voice_features_for_voice(db, voice_id)

    schedule_feature_extract(client_type, f"voice:{voice_id}", work)


def schedule_video_features(client_type: str, video_id: int) -> None:
    def work(db) -> None:
        from app.services.analysis import extract_video_features_for_video

        extract_video_features_for_video(db, video_id)

    schedule_feature_extract(client_type, f"video:{video_id}", work)


def schedule_behavior_features(
    client_type: str, user_id: int, task_date: str, session_id: int
) -> None:
    def work(db) -> None:
        from app.services.analysis import extract_behavior_features_for_session

        extract_behavior_features_for_session(db, user_id, task_date, session_id)

    schedule_feature_extract(
        client_type, f"behavior:{user_id}:{task_date}:{session_id}", work
    )
