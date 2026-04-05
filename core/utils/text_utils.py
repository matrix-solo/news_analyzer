#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理公共工具函数

收录整个项目中重复出现的文本处理逻辑，统一维护：
- get_news_title     从 news dict 取标题（兼容翻译/原始字段）
- get_news_content   从 news dict 取正文/摘要
- format_tags        将标签字段格式化为逗号分隔字符串
- parse_json_str     从 AI 响应文本中鲁棒解析 JSON
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Union


def get_news_title(news: Dict[str, Any]) -> str:
    """
    从 news dict 中取标题。
    优先取 translated_title，再取 title，默认空字符串。
    """
    return (news.get("translated_title") or news.get("title") or "").strip()


def get_news_content(news: Dict[str, Any], max_chars: int = 0) -> str:
    """
    从 news dict 中取正文/摘要。
    优先顺序：translated_content → summary → short_summary → content
    max_chars > 0 时截断。
    """
    text = (
        news.get("translated_content")
        or news.get("summary")
        or news.get("short_summary")
        or news.get("content")
        or ""
    ).strip()
    return text[:max_chars] if max_chars > 0 else text


def format_tags(tags: Union[List, str, None]) -> str:
    """
    将标签字段格式化为逗号分隔字符串。
    兼容 None / list / str / 其他类型。
    """
    if tags is None:
        return ""
    if isinstance(tags, list):
        return ", ".join(str(t) for t in tags if t is not None)
    if isinstance(tags, str):
        return tags
    return str(tags)


def parse_json_str(text: str) -> Any:
    """
    从 AI 响应文本中鲁棒解析 JSON。

    尝试顺序：
    1. 直接 json.loads
    2. 提取 ```json ... ``` 代码块
    3. 栈匹配找第一个完整的 JSON 数组
    4. 栈匹配找第一个完整的 JSON 对象
    5. 正则宽松匹配 [ ... ] 或 { ... }

    成功则返回解析后的对象；全部失败则返回空 dict {}。
    """
    # 1. 直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. ```json ... ```
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. 栈匹配 JSON 数组
    result = _stack_extract(text, "[", "]")
    if result is not None:
        return result

    # 4. 栈匹配 JSON 对象
    result = _stack_extract(text, "{", "}")
    if result is not None:
        return result

    # 5. 宽松正则
    for pattern in (r"\[[\s\S]*?\]", r"\{[\s\S]*?\}"):
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

    return {}


def _stack_extract(text: str, open_ch: str, close_ch: str) -> Any:
    """用括号栈从 text 中提取第一个完整的 JSON 结构。"""
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == open_ch:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_ch and start is not None:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except (json.JSONDecodeError, ValueError):
                    # 继续向后寻找下一个候选
                    start = None
    return None
