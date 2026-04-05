#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全工具"""
import hashlib

def hash_content(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def sanitize_url(url: str) -> str:
    return url.strip()
