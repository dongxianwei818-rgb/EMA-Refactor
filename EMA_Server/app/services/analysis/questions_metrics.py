"""EMA 问卷量表字段定义。"""

from __future__ import annotations

# 7 项 0-10 分量表：(字段名, 中文标签, 是否越高越 distress)
SCALE_METRICS: tuple[tuple[str, str, bool], ...] = (
    ("mood", "心情", False),  # 越低越 distress
    ("stress", "压力", True),
    ("anxiety", "焦虑", True),
    ("lonely", "孤独感", True),
    ("sleep", "睡眠质量", False),  # 越低越 distress（睡眠差）
    ("fatigue", "疲劳", True),
    ("function", "功能受影响", True),
)

SCALE_FIELDS: tuple[str, ...] = tuple(m[0] for m in SCALE_METRICS)

METRIC_LABELS: dict[str, str] = {m[0]: m[1] for m in SCALE_METRICS}

# 第 8 项：消极想法（分类）
NEGATIVE_THOUGHT_MAP: dict[str, float] = {
    "是": 1.0,
    "否": 0.0,
    "不愿回答": 0.5,
}
