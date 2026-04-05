#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ£æ¥è¯åæ°æ®ç»æ?"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase

def check_score():
    db = NewsDatabase()

    # è·åæè¿çæ°é»
    news_list = db.get_recent_news(hours=24)

    print("=" * 80)
    print("æ£æ¥è¯åæ°æ®ç»æ?")
    print("=" * 80)

    for news in news_list[:5]:
        print(f"\næ é¢: {news.get('title', 'N/A')[:50]}...")
        print(f"æ¥æº: {news.get('source_name', 'N/A')}")
        print(f"final_score: {news.get('final_score', 'None')}")
        print(f"score_reason: {news.get('score_reason', 'None')}")
        # æ£æ¥æ¯å¦æè¯¦ç»è¯åå­æ®µ
        print(f"ææå­æ®? {list(news.keys())}")

if __name__ == "__main__":
    check_score()
