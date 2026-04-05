#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志配置"""
import logging

def setup_logging(level: int = logging.INFO, log_file: str = None):
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
