#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ£æ¥æ°æ®åºä¸­æ ç­¾çå®éæ ¼å¼
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase

def check_tags():
    db = NewsDatabase()

    # è·åæè¿çæ°é»
    news_list = db.get_recent_news(hours=24)
    news_list = news_list[:10]  # åªåå?0æ?    
    print("=" * 80)
    print("æ£æ¥æ°é»æ ç­¾æ ¼å¼?")
    print("=" * 80)

    for news in news_list:
        print(f"\næ é¢: {news.get('title', 'N/A')[:50]}...")
        print(f"æ¥æº: {news.get('source_name', 'N/A')}")
        print(f"tags: {news.get('tags', 'None')}")
        print(f"core_tags: {news.get('core_tags', 'None')}")
        print(f"æ ç­¾ç±»å: tags={type(news.get('tags'))}, core_tags={type(news.get('core_tags'))}")

    db.close()

if __name__ == "__main__":
    check_tags()
