#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""监控数据结构"""
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class MonitoringData:
    source_name: str
    success_count: int = 0
    failure_count: int = 0
    last_error: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
