#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
åææ°éæºåå¸éç?åºäºæ°æ®åºä¸­çåå²æ°æ®çè®¡åæºçå®éåå¸éç
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase

def analyze_source_frequency():
    """åæåæºçåå¸éç?""
    db = NewsDatabase()

    # è·åæè¿?å¤©çæ°é
    recent_news = db.get_recent_news(hours=24*7)

    # çè®¡åæºçåå¸éç?    source_stats = defaultdict(lambda: {
        'total': 0,
        'dates': set(),
        'hours': defaultdict(int),
        'pub_dates': []
    })

    for news in recent_news:
        source = news.get('source_name', 'Unknown')
        pub_date_str = news.get('pub_date', '')

        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                # è½¬æä¸ºæ æ¶åºçdatetimeä¥ä¾¿æ¯è¾
                pub_date = pub_date.replace(tzinfo=None)
                source_stats[source]['total'] += 1
                source_stats[source]['dates'].add(pub_date.date())
                source_stats[source]['hours'][pub_date.hour] += 1
                source_stats[source]['pub_dates'].append(pub_date)
            except:
                pass

    # è®¡ç®æ¯ä¸ªæºçå³ååå¸éç
    print('=' * 80)
    print('æ°éæºåå¸éççè®¡ïæè¿?å¤©ï')
    print('=' * 80)
    print()

    results = []
    for source, stats in sorted(source_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        total = stats['total']
        days = len(stats['dates'])
        avg_per_day = total / max(days, 1)
        avg_per_hour = total / (days * 24)

        # è®¡ç®åå¸é'éïå°æ¶ï
        if len(stats['pub_dates']) > 1:
            sorted_dates = sorted(stats['pub_dates'])
            intervals = [(sorted_dates[i+1] - sorted_dates[i]).total_seconds() / 3600 
                         for i in range(len(sorted_dates)-1)]
            avg_interval = sum(intervals) / len(intervals)
        else:
            avg_interval = 24

        results.append({
            'source': source,
            'total': total,
            'days': days,
            'avg_per_day': round(avg_per_day, 1),
            'avg_per_hour': round(avg_per_hour, 2),
            'avg_interval_hours': round(avg_interval, 1)
        })

    # è¾åºçæ
    for r in results[:20]:  # æ¾ç¤ºå?0ä¸ªæº
        print(f"{r['source']:30s} | Total: {r['total']:4d} | Days: {r['days']} | Daily: {r['avg_per_day']:5.1f} | Hourly: {r['avg_per_hour']:4.2f} | Interval: {r['avg_interval_hours']:5.1f}h")

    print()
    print('=' * 80)
    print('åºè®®åç')
    print('=' * 80)

    # æ æ®åå¸éçåç
    high_freq = [r for r in results if r['avg_interval_hours'] <= 4]
    mid_freq = [r for r in results if 4 < r['avg_interval_hours'] <= 8]
    low_freq = [r for r in results if r['avg_interval_hours'] > 8]

    print(f"\né«éçïå³åé'é â?å°æ¶ïåºè®®æ¯4å°æ¶ééï? {len(high_freq)} ä¸ªæº"')
    for r in high_freq:
        print(f"  - {r['source']} (interval {r['avg_interval_hours']}h)")

    print(f"\nä¸­éçïå³åé'é 4-8å°æ¶ïåºè®®æ¯8å°æ¶ééï? {len(mid_freq)} ä¸ªæº"')
    for r in mid_freq[:10]:
        print(f"  - {r['source']} (interval {r['avg_interval_hours']}h)")

    print(f"\nä½éçïå³åé'é >8å°æ¶ïåºè®®æ¯12å°æ¶ééï? {len(low_freq)} ä¸ªæº"')
    for r in low_freq[:10]:
        print(f"  - {r['source']} (interval {r['avg_interval_hours']}h)")

    # ä¿å­çæå°JSON
    output_file = project_root / 'data' / 'source_frequency_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'period': '7 days',
            'high_freq': high_freq,
            'mid_freq': mid_freq,
            'low_freq': low_freq,
            'all_sources': results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nåæçæå·²ä¿å­å°: {output_file}")

if __name__ == "__main__":
    analyze_source_frequency()

"""
    db = NewsDatabase()

    # è·åæè¿?å¤©çæ°é
    recent_news = db.get_recent_news(hours=24*7)

    # çè®¡åæºçåå¸éç?    source_stats = defaultdict(lambda: {
        'total': 0,
        'dates': set(),
        'hours': defaultdict(int),
        'pub_dates': []
    })

    for news in recent_news:
        source = news.get('source_name', 'Unknown')
        pub_date_str = news.get('pub_date', '')

        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                # è½¬æä¸ºæ æ¶åºçdatetimeä¥ä¾¿æ¯è¾
                pub_date = pub_date.replace(tzinfo=None)
                source_stats[source]['total'] += 1
                source_stats[source]['dates'].add(pub_date.date())
                source_stats[source]['hours'][pub_date.hour] += 1
                source_stats[source]['pub_dates'].append(pub_date)
            except:
                pass

    # è®¡ç®æ¯ä¸ªæºçå³ååå¸éç
    print('=' * 80)
    print('æ°éæºåå¸éççè®¡ïæè¿?å¤©ï')
    print('=' * 80)
    print()

    results = []
    for source, stats in sorted(source_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        total = stats['total']
        days = len(stats['dates'])
        avg_per_day = total / max(days, 1)
        avg_per_hour = total / (days * 24)

        # è®¡ç®åå¸é'éïå°æ¶ï
        if len(stats['pub_dates']) > 1:
            sorted_dates = sorted(stats['pub_dates'])
            intervals = [(sorted_dates[i+1] - sorted_dates[i]).total_seconds() / 3600 
                         for i in range(len(sorted_dates)-1)]
            avg_interval = sum(intervals) / len(intervals)
        else:
            avg_interval = 24

        results.append({
            'source': source,
            'total': total,
            'days': days,
            'avg_per_day': round(avg_per_day, 1),
            'avg_per_hour': round(avg_per_hour, 2),
            'avg_interval_hours': round(avg_interval, 1)
        })

    # è¾åºçæ
    for r in results[:20]:  # æ¾ç¤ºå?0ä¸ªæº
        print(f"{r['source']:30s} | Total: {r['total']:4d} | Days: {r['days']} | Daily: {r['avg_per_day']:5.1f} | Hourly: {r['avg_per_hour']:4.2f} | Interval: {r['avg_interval_hours']:5.1f}h")

    print()
    print('=' * 80)
    print('åºè®®åç')
    print('=' * 80)

    # æ æ®åå¸éçåç
    high_freq = [r for r in results if r['avg_interval_hours'] <= 4]
    mid_freq = [r for r in results if 4 < r['avg_interval_hours'] <= 8]
    low_freq = [r for r in results if r['avg_interval_hours'] > 8]

    print(f"\né«éçïå³åé'é â?å°æ¶ïåºè®®æ¯4å°æ¶ééï? {len(high_freq)} ä¸ªæº"')
    for r in high_freq:
        print(f"  - {r['source']} (interval {r['avg_interval_hours']}h)")

    print(f"\nä¸­éçïå³åé'é 4-8å°æ¶ïåºè®®æ¯8å°æ¶ééï? {len(mid_freq)} ä¸ªæº"')
    for r in mid_freq[:10]:
        print(f"  - {r['source']} (interval {r['avg_interval_hours']}h)")

    print(f"\nä½éçïå³åé'é >8å°æ¶ïåºè®®æ¯12å°æ¶ééï? {len(low_freq)} ä¸ªæº"')
    for r in low_freq[:10]:
        print(f"  - {r['source']} (interval {r['avg_interval_hours']}h)")

    # ä¿å­çæå°JSON
    output_file = project_root / 'data' / 'source_frequency_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'period': '7 days',
            'high_freq': high_freq,
            'mid_freq': mid_freq,
            'low_freq': low_freq,
            'all_sources': results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nåæçæå·²ä¿å­å°: {output_file}")

if __name__ == "__main__":
    analyze_source_frequency()
