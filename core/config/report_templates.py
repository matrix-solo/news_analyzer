#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告模板配置"""

DEFAULT_TEMPLATE = "default"
MINIMAL_TEMPLATE = "minimal"
DETAILED_TEMPLATE = "detailed"

REPORT_TEMPLATES = {
    "default": {"max_articles": 10, "include_analysis": True},
    "minimal": {"max_articles": 5, "include_analysis": False},
    "detailed": {"max_articles": 15, "include_analysis": True},
}

def get_template(name: str = "default") -> dict:
    return REPORT_TEMPLATES.get(name, REPORT_TEMPLATES["default"])
