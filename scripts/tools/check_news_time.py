#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ£æ¥æ°æ®åºä¸­çæ°éåå¸æ¶é''
"""

import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase

def check_database_news():
    """æ£æ¥æ°æ®åºä¸­çæ°é"""
    db = NewsDatabase()

    recent_news = db.get_recent_news(hours=24*7)

    if recent_news:
        print(f'æè¿?å¤©æ°éææ°: {len(recent_news)} æ?')
        print(f'\nææ?0æ¡æ°é?')
        for i, news in enumerate(recent_news[:10], 1):
            pub_date = news.get('pub_date', 'N/A')
            title = news.get('title', 'N/A')[:60]
            source = news.get('source_name', 'N/A')
            domain = news.get('domain', 'N/A')
            print(f'{i}. [{pub_date}] {title}... ({source} - {domain})')

        latest_pub_date = recent_news[0].get('pub_date')
        if latest_pub_date:
            print(f'\nææ°æ°éåå¸æ¶é? {latest_pub_date}')

            try:
                latest_time = datetime.fromisoformat(latest_pub_date.replace('Z', '+00:00'))
                now = datetime.now()
                time_diff = now - latest_time.replace(tzinfo=None)
                print(f'è·ç¦ç°å¨: {time_diff}')
                print(f'å°æ¶æ? {time_diff.total_seconds() / 3600:.1f} å°æ¶')
            except Exception as e:
                print(f'æ¶é'è£æéè¯¯: {e}'')

        recent_24h = db.get_recent_news(hours=24)
        print(f'\næè¿?4å°æ¶æ°é: {len(recent_24h)} æ?')

        recent_12h = db.get_recent_news(hours=12)
        print(f'æè¿?2å°æ¶æ°é: {len(recent_12h)} æ?')

        recent_6h = db.get_recent_news(hours=6)
        print(f'æè¿?å°æ¶æ°é: {len(recent_6h)} æ?')

    else:
        print('æ°æ®åºä¸­æ²¡ææ°é')

    stats = db.get_stats()
    print(f'\næ°æ®åºçè®?')
    print(f'  æé: {stats["total_news"]} æ?')
    print(f'  æè¿?4å°æ¶: {stats["recent_24h"]} æ?')
    print(f'  æè¿?å¤? {stats["recent_7d"]} æ?')

if __name__ == "__main__":
    check_database_news()
