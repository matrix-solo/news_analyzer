# -*- coding: utf-8 -*-
"""统一默认值管理模块

P-11/P-12 修复：解决两处 _fill_default_values 默认值不一致的问题
"""

import re

class DefaultValues:
    """默认值常量类"""

    # 评分默认值 (5.0 表示中等/未知)
    SCORE_DEFAULT = 5.0

    # 文本默认值
    TEXT_UNKNOWN = '暂无信息'
    TEXT_NO_TRANSLATION = '暂无翻译'
    TEXT_NO_SUMMARY = '暂无摘要'
    TEXT_NO_WHO = '暂无信息'
    TEXT_NO_WHAT = '暂无信息'
    TEXT_NO_WHEN = '暂无信息'
    TEXT_NO_WHERE = '暂无信息'
    TEXT_NO_WHY = '暂无信息'
    TEXT_NO_HOW = '暂无信息'

    # 领域默认值
    DOMAIN_DEFAULT = '社会'

    # 5W1H 字段列表
    W5H1_FIELDS = ['who', 'what', 'when', 'where', 'why', 'how']

    @classmethod
    def get_text_default(cls, field: str) -> str:
        mapping = {
            'who': cls.TEXT_NO_WHO,
            'what': cls.TEXT_NO_WHAT,
            'when': cls.TEXT_NO_WHEN,
            'where': cls.TEXT_NO_WHERE,
            'why': cls.TEXT_NO_WHY,
            'how': cls.TEXT_NO_HOW,
            'translation': cls.TEXT_NO_TRANSLATION,
            'summary': cls.TEXT_NO_SUMMARY,
        }
        return mapping.get(field, cls.TEXT_UNKNOWN)

    @classmethod
    def get_score_default(cls, field: str) -> float:
        return cls.SCORE_DEFAULT


# 5W1H 无效值黑名单
_INVALID_5W1H_VALUES = frozenset({
    '', '无', '未知', '不详', '未提及', '不清楚',
    '暂不确定', '待确认', '待定', 'N/A', 'n/a', '-',
    'none', 'None', 'null', 'NULL',
})

# 推测性前缀模式
_SPECULATIVE_PREFIX_RE = re.compile(
    r'^(可能是|据推测|似乎|大概|也许|疑似|可能)\s*'
)


def normalize_5w1h(value) -> str:
    """统一 5W1H 字段值：
    - None / 空字符串 / 黑名单值 → '暂无信息'
    - 推测性前缀去除，保留事实部分
    """
    if value is None:
        return DefaultValues.TEXT_UNKNOWN

    v = str(value).strip()
    if not v or v in _INVALID_5W1H_VALUES:
        return DefaultValues.TEXT_UNKNOWN

    # 去除推测性前缀，保留事实描述
    cleaned = _SPECULATIVE_PREFIX_RE.sub('', v).strip()
    if cleaned and cleaned not in _INVALID_5W1H_VALUES:
        return cleaned

    return DefaultValues.TEXT_UNKNOWN
