# -*- coding: utf-8 -*-
"""统一默认值管理模块

P-11/P-12 修复：解决两处 _fill_default_values 默认值不一致的问题
"""

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
