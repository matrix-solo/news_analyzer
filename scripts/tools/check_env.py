#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ£æ¥ç¯ååéå è½?""""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from core.config.loader import get_env

def mask_key(key: str) -> str:
    """è±ææ¾ç¤ºAPI Key"""
    if not key:
        return "(æªè®¾ç½?"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"

def check_env():
    """æ£æ¥ç¯ååéå è½?""
    print("æ£æ¥ç¯ååéå è½?..")
    print("-" * 50)

    keys_to_check = [
        ("DEEPSEEK_API_KEY", "DeepSeek API"),
        ("ARK_API_KEY", "è±å API"),
        ("DOUBAO_API_KEY", "è±å API (å¤ç¨)"),
        ("QWEN_API_KEY", "éäåé® API"),
        ("DASHSCOPE_API_KEY", "DashScope API"),
        ("NEWS_API_KEY", "NewsAPI"),
    ]

    for key, name in keys_to_check:
        value = get_env(key)
        masked = mask_key(value)
        status = "â? if value else "â?
        print(f"{status} {name}: {masked}")

    print("-" * 50)
    print("æ£æ¥å®æï")

if __name__ == "__main__":
    check_env()

"""
    print("æ£æ¥ç¯ååéå è½?..")
    print("-" * 50)

    keys_to_check = [
        ("DEEPSEEK_API_KEY", "DeepSeek API"),
        ("ARK_API_KEY", "è±å API"),
        ("DOUBAO_API_KEY", "è±å API (å¤ç¨)"),
        ("QWEN_API_KEY", "éäåé® API"),
        ("DASHSCOPE_API_KEY", "DashScope API"),
        ("NEWS_API_KEY", "NewsAPI"),
    ]

    for key, name in keys_to_check:
        value = get_env(key)
        masked = mask_key(value)
        status = "â? if value else "â?
        print(f"{status} {name}: {masked}")

    print("-" * 50)
    print("æ£æ¥å®æï")

if __name__ == "__main__":
    check_env()
