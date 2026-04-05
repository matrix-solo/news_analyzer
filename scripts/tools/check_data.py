#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""æ£æ¥æ°æ®åºç¶æ?""

import sys
sys.path.insert(0, 'c:\\Users\\matrix\\Desktop\\news_workflow\\news_analyzer')

from core.storage.database import get_db

def check_data():
    db = get_db()

    # è·åæè¿?8å°æ¶çæ°é?    recent = db.get_recent_news(hours=48)
    print(f"æè¿?8å°æ¶æ°é: {len(recent)}æ?")

    # çè®¡éå
    domain_counts = {}
    unclassified = []

    for news in recent:
        domain = news.get('domain')
        if not domain:
            unclassified.append(news)
            domain = 'æªåç±?'
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    print("\néååå¸:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"  {domain}: {count}æ?")

    print(f"\næªåç±æ°é? {len(unclassified)}æ?")

    # æ£æ¥æ¿æ²ãçæµãçæ
    print("\néçæ£æ?")
    for domain in ['æ¿æ²', 'çæµ', 'çæ']:
        count = domain_counts.get(domain, 0)
        status = "â? if count > 0 else "â?
        print(f"{status} {domain}: {count}æ?")

if __name__ == "__main__":
    check_data()

"""

import sys
sys.path.insert(0, 'c:\\Users\\matrix\\Desktop\\news_workflow\\news_analyzer')

from core.storage.database import get_db

def check_data():
    db = get_db()

    # è·åæè¿?8å°æ¶çæ°é?    recent = db.get_recent_news(hours=48)
    print(f"æè¿?8å°æ¶æ°é: {len(recent)}æ?")

    # çè®¡éå
    domain_counts = {}
    unclassified = []

    for news in recent:
        domain = news.get('domain')
        if not domain:
            unclassified.append(news)
            domain = 'æªåç±?'
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    print("\néååå¸:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"  {domain}: {count}æ?")

    print(f"\næªåç±æ°é? {len(unclassified)}æ?")

    # æ£æ¥æ¿æ²ãçæµãçæ
    print("\néçæ£æ?")
    for domain in ['æ¿æ²', 'çæµ', 'çæ']:
        count = domain_counts.get(domain, 0)
        status = "â? if count > 0 else "â?
        print(f"{status} {domain}: {count}æ?")

if __name__ == "__main__":
    check_data()
