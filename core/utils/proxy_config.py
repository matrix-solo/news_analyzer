#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代理配置"""
import os

def get_proxy_config() -> dict:
    http_proxy = os.getenv("HTTP_PROXY", "")
    https_proxy = os.getenv("HTTPS_PROXY", "")
    if http_proxy or https_proxy:
        return {"http": http_proxy, "https": https_proxy}
    return {}
