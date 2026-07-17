"""Multimodal analysis modules."""

from typing import Any

from sqlalchemy.orm import Session

from app.models import models_for
from app.services.analysis.behavior_feature_extractor import BehaviorFeatureExtractor
from app.services.analysis.questions_feature_extractor import QuestionsFeatureExtractor
from app.services.analysis.step_feature_extractor import StepFeatureExtractor
from app.services.analysis.text_feature_extractor import TextFeatureExtractor
from app.services.analysis.video_feature_extractor import VideoFeatureExtractor
from app.services.analysis.voice_feature_extractor import VoiceFeatureExtractor


def extract_text_features_for_diary(db: Session, diary_id: int) -> Any | None:
    """从指定 ema_diary 记录提取文本特性并写入 text_features。"""
    return TextFeatureExtractor(db).process_diary_by_id(diary_id)


def extract_text_features_from_diary_row(db: Session, diary) -> Any:
    """从 EmaDiary ORM 实例提取文本特性。"""
    return TextFeatureExtractor(db).process_diary(diary)


def extract_questions_features_for_question(db: Session, question_id: int) -> Any | None:
    """从指定 ema_questions 记录提取 EMA 趋势特性并写入 questions_features。"""
    return QuestionsFeatureExtractor(db).process_questionnaire_by_id(question_id)


def extract_questions_features_from_question_row(db: Session, record) -> Any:
    """从 EmaQuestion ORM 实例提取 EMA 趋势特性。"""
    return QuestionsFeatureExtractor(db).process_questionnaire(record)


def extract_voice_features_for_voice(db: Session, voice_id: int) -> Any | None:
    """从指定 ema_voice 记录提取语音特性并写入 voice_features。"""
    return VoiceFeatureExtractor(db).process_voice_by_id(voice_id)


def extract_voice_features_from_voice_row(db: Session, voice) -> Any:
    """从 EmaVoice ORM 实例提取语音特性。"""
    return VoiceFeatureExtractor(db).process_voice(voice)


def extract_video_features_for_video(db: Session, video_id: int) -> Any | None:
    """从指定 ema_video 记录提取视频特性并写入 video_features。"""
    return VideoFeatureExtractor(db).process_video_by_id(video_id)


def extract_video_features_from_video_row(db: Session, video) -> Any:
    """从 EmaVideo ORM 实例提取视频特性。"""
    return VideoFeatureExtractor(db).process_video(video)


def extract_step_features_for_step(db: Session, step_id: int) -> Any | None:
    """从指定 ema_step 记录提取步数特性并写入 step_features。"""
    return StepFeatureExtractor(db).process_step_by_id(step_id)


def extract_step_features_from_step_row(db: Session, record) -> Any:
    """从 EmaStep ORM 实例提取步数特性。"""
    return StepFeatureExtractor(db).process_step(record)


def extract_behavior_features_for_session(
    db: Session, user_id: int, task_date: str, session_id: int = 1
) -> Any:
    """从 behavior_logs / behavior_meta 提取行为特性并写入 behavior_features。"""
    return BehaviorFeatureExtractor(db).process_session(user_id, task_date, session_id)


def enqueue_text_analysis(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int = 1,
    submission_id: int | None = None,
) -> Any:
    TextFeature = models_for(db=db).TextFeature
    row = TextFeature(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        submission_id=submission_id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def enqueue_voice_analysis(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int = 1,
    submission_id: int | None = None,
) -> Any:
    VoiceFeature = models_for(db=db).VoiceFeature
    row = VoiceFeature(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        submission_id=submission_id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def enqueue_video_analysis(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int = 1,
    submission_id: int | None = None,
) -> Any:
    VideoFeature = models_for(db=db).VideoFeature
    row = VideoFeature(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        submission_id=submission_id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def enqueue_behavior_analysis(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int = 1,
) -> Any:
    BehaviorFeature = models_for(db=db).BehaviorFeature
    row = BehaviorFeature(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def enqueue_questions_analysis(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int = 1,
    submission_id: int | None = None,
) -> Any:
    QuestionsFeature = models_for(db=db).QuestionsFeature
    row = QuestionsFeature(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        submission_id=submission_id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def enqueue_step_analysis(
    db: Session,
    user_id: int,
    task_date: str,
    session_id: int = 1,
    submission_id: int | None = None,
) -> Any:
    StepFeature = models_for(db=db).StepFeature
    row = StepFeature(
        user_id=user_id,
        task_date=task_date,
        session_id=session_id,
        submission_id=submission_id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


__all__ = [
    "TextFeatureExtractor",
    "QuestionsFeatureExtractor",
    "VoiceFeatureExtractor",
    "VideoFeatureExtractor",
    "StepFeatureExtractor",
    "BehaviorFeatureExtractor",
    "extract_text_features_for_diary",
    "extract_text_features_from_diary_row",
    "extract_questions_features_for_question",
    "extract_questions_features_from_question_row",
    "extract_voice_features_for_voice",
    "extract_voice_features_from_voice_row",
    "extract_video_features_for_video",
    "extract_video_features_from_video_row",
    "extract_step_features_for_step",
    "extract_step_features_from_step_row",
    "extract_behavior_features_for_session",
    "enqueue_text_analysis",
    "enqueue_voice_analysis",
    "enqueue_video_analysis",
    "enqueue_behavior_analysis",
    "enqueue_questions_analysis",
    "enqueue_step_analysis",
]
