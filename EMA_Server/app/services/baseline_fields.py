"""基线测评字段映射与序列化."""

from typing import Any

from app.models import BaselineProfile
from app.services.datetime_fields import datetime_to_ms

# 小程序 form 字段 id -> 数据库列名（researchId 使用 research_id 列）
BASELINE_FORM_TO_COLUMN: dict[str, str] = {
    "researchId": "research_id",
    "age": "age",
    "grade": "grade",
    "major": "major",
    "gender": "gender",
    "onlyChild": "only_child",
    "housing": "housing",
    "course_pressure": "course_pressure",
    "exam_pressure": "exam_pressure",
    "gpa_pressure": "gpa_pressure",
    "job_pressure": "job_pressure",
    "sleep_habit": "sleep_habit",
    "exercise_freq": "exercise_freq",
    "social_freq": "social_freq",
    "phq9_1": "phq9_1",
    "phq9_2": "phq9_2",
    "gad7_1": "gad7_1",
    "gad7_2": "gad7_2",
    "pss_1": "pss_1",
    "isi_1": "isi_1",
    "ucla_1": "ucla_1",
    "counsel_before": "counsel_before",
    "treatment_now": "treatment_now",
    "self_harm": "self_harm",
}

BASELINE_COLUMN_TO_FORM = {v: k for k, v in BASELINE_FORM_TO_COLUMN.items()}


def parse_baseline_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """将小程序提交的 profile 转为数据库列值。"""
    data: dict[str, Any] = {}
    for form_key, column in BASELINE_FORM_TO_COLUMN.items():
        raw = profile.get(form_key)
        if raw is None or raw == "":
            data[column] = None
            continue
        if column == "age":
            try:
                data[column] = int(raw)
            except (TypeError, ValueError):
                data[column] = None
        elif column == "research_id":
            data[column] = str(raw)
        else:
            data[column] = str(raw)
    return data


def apply_baseline_fields(target: BaselineProfile, fields: dict[str, Any]) -> None:
    for column, value in fields.items():
        setattr(target, column, value)


def baseline_completed_at_ms(baseline: BaselineProfile) -> int:
    return datetime_to_ms(baseline.completed_at) or 0


def baseline_to_profile_dict(baseline: BaselineProfile) -> dict[str, Any]:
    """转为小程序/风险评估使用的 profile 字典（camelCase 键）。"""
    result: dict[str, Any] = {"at": baseline_completed_at_ms(baseline)}
    for column, form_key in BASELINE_COLUMN_TO_FORM.items():
        result[form_key] = getattr(baseline, column)
    return result
