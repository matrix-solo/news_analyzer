#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ°æ®åºç®¡çCLIå·¥å·

åè½ï?1. æ¥çæ°æ®åºçè®¡ä¿¡æ?2. æ¥è¯çå®æ°é
3. æ°æ®è'¨éæ£æ?4. æ°æ®å¯åº'
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase
from core.config.loader import PROJECT_ROOT

class DatabaseManager:
    """æ°æ®åºç®¡çå¨"""

    def __init__(self):
        self.db = NewsDatabase()

    def show_stats(self):
        """æ¾ç¤ºæ°æ®åºçè®¡ä¿¡æ?""
        stats = self.db.get_stats()

        print("\n" + "=" * 60)
        print("ð æ°æ®åºçè®¡ä¿¡æ?")
        print("=" * 60)
        print(f"\nð¦ ææ°éæ°: {stats['total_news']:,}")
        print(f"ð æè¿?4å°æ¶: {stats['recent_24h']:,}")
        print(f"ð æè¿?å¤? {stats['recent_7d']:,}")
        print(f"ð æè¿?0å¤? {stats['recent_30d']:,}")
        print(f"â?å·²å¤çæ°: {stats['processed']:,}")

        if stats['by_domain']:
            print("\nð éååå¸:")
            for domain, count in sorted(stats['by_domain'].items(), key=lambda x: -x[1]):
                bar = "â? * min(20, count // 5")
                print(f"  {domain:8s}: {count:5d} {bar}")

        print("\n" + "=" * 60)

    def show_recent(self, hours: int = 24, domain: str = None, limit: int = 20):
        """æ¾ç¤ºæè¿æ°é?""
        if domain:
            news_list = self.db.search_by_domain(domain, hours)
            print(f"\nð° æè¿{hours}å°æ¶ {domain} éåæ°é (å±{len(news_list)}æ?")
        else:
            news_list = self.db.get_recent_news(hours)
            print(f"\nð° æè¿{hours}å°æ¶æ°é (å±{len(news_list)}æ?")

        print("=" * 80)

        for i, news in enumerate(news_list[:limit], 1):
            title = news.get('translated_title') or news.get('title', 'æ æ é?')
            score = news.get('score', 0)
            source = news.get('source_name', 'æªç¥')
            domain_val = news.get('domain', 'å¶ä')
            pub_date = news.get('pub_date', '')[:10] if news.get('pub_date') else 'æªç¥'

            score_icon = "ð¥" if score >= 80 else "â­? if score >= 60 else "ð""

            print(f"\n{i}. {score_icon} [{score:.0f}å] {title[:50]}...")
            print(f"   æ¥æº: {source} | éå: {domain_val} | æ¥æ: {pub_date}")

        if len(news_list) > limit:
            print(f"\n... è¿æ {len(news_list) - limit} æ¡æ°éæªæ¾ç¤º")

        print("\n" + "=" * 80)

    def search(self, keyword: str, days: int = 30):
    """æç'æ°é"""
        keywords = [k.strip() for k in keyword.split(',')]
        news_list = self.db.search_by_keywords(keywords, days)

        print(f"\nð æç'çæ: '{keyword}' (è¿{days}å¤©ïå±{len(news_list)}æ?"')
        print("=" * 80)

        for i, news in enumerate(news_list[:20], 1):
            title = news.get('translated_title') or news.get('title', 'æ æ é?')
            score = news.get('score', 0)
            source = news.get('source_name', 'æªç¥')

            print(f"\n{i}. [{score:.0f}å] {title[:60]}...")
            print(f"   æ¥æº: {source}")

        if len(news_list) > 20:
            print(f"\n... è¿æ {len(news_list) - 20} æ¡çææªæ¾ç¤º")

        print("\n" + "=" * 80)

    def show_detail(self, news_id: str):
    """æ¾ç¤ºæ°éè¯¦æ"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM news WHERE id = ? OR id LIKE ?', (news_id, f'%{news_id}%'))
            row = cursor.fetchone()

            if not row:
                print(f"\nâ?æªæ¾å°æ°é? {news_id}")
                return

            news = dict(row)

            print("\n" + "=" * 60)
            print("ð æ°éè¯¦æ")
            print("=" * 60)

            print(f"\nð æ é: {news.get('title', 'æ?)}"')
            if news.get('translated_title'):
                print(f"ð è¯å: {news['translated_title']}")

            print(f"\nð° æ¥æº: {news.get('source_name', 'æªç¥')}")
            print(f"ð åå¸æ¶é': {news.get('pub_date', 'æªç¥')}"')
            print(f"ð é¾æ¥: {news.get('link', 'æ?)}"')

            print(f"\nð·ï¸?éå: {news.get('domain', 'å¶ä')}")
            tags = news.get('tags', '[]')
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            if tags:
                print(f"ð·ï¸?æ ç­¾: {', '.join(tags)}")

            print(f"\nâ­?çåè¯å: {news.get('score', 0):.1f}")
            print(f"   - ä¿¡æºå? {news.get('score_credibility', 0):.1f}")
            print(f"   - å½±åå? {news.get('score_importance', 0):.1f}")
            print(f"   - æ¶ææ? {news.get('score_timeliness', 0):.1f}")
            print(f"   - ä·åå: {news.get('score_impact', 0):.1f}")

            print("\nð 5W1H åæ:")
            print(f"   - ä½äºº: {news.get('who', 'æ?)}"')
            print(f"   - ä½äº: {news.get('what', 'æ?)}"')
            print(f"   - ä½æ¶: {news.get('when_time', 'æ?)}"')
            print(f"   - ä½å°: {news.get('where_place', 'æ?)}"')
            print(f"   - ä½å : {news.get('why', 'æ?)}"')
            print(f"   - å¦ä½: {news.get('how', 'æ?)}"')

            if news.get('summary'):
                print(f"\nð æè¦:\n{news['summary'][:500]}...")

            if news.get('content'):
                print(f"\nð åå®:\n{news['content'][:500]}...")

            print(f"\nð è£æææ³: {news.get('extraction_method', 'æªç¥')}")
            print(f"ð å¥åºæ¶é': {news.get('created_at', 'æªç¥')}"')

            print("\n" + "=" * 60)

    def check_quality(self):
        """æ£æ¥æ°æ®è'¨é?""
        print("\n" + "=" * 60)
        print("ð æ°æ®è'¨éæ£æ?"')
        print("=" * 60)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM news')
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM news WHERE domain IS NULL OR domain = ""')
            no_domain = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM news WHERE score IS NULL OR score = 0')
            no_score = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM news WHERE content IS NULL OR content = ""')
            no_content = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM news WHERE who IS NULL OR who = ""')
            no_who = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM news WHERE what IS NULL OR what = ""')
            no_what = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM news WHERE summary IS NULL OR summary = ""')
            no_summary = cursor.fetchone()[0]

                SELECT COUNT(*) FROM news 
                WHERE who IS NULL AND what IS NULL AND when_time IS NULL 
                AND where_place IS NULL AND why IS NULL AND how IS NULL
            no_5w1h = cursor.fetchone()[0]

        print(f"\nð¦ æè®°å½æ°: {total:,}")

        print("\nâ ï¸ æ°æ®çºå¤±çè®¡:")

        issues = []
        if no_domain > 0:
            pct = no_domain / total * 100
            issues.append(f"  - æ éåæ ç­? {no_domain:,} ({pct:.1f}%)")
        if no_score > 0:
            pct = no_score / total * 100
            issues.append(f"  - æ è¯å? {no_score:,} ({pct:.1f}%)")
        if no_content > 0:
            pct = no_content / total * 100
            issues.append(f"  - æ åå®? {no_content:,} ({pct:.1f}%)")
        if no_summary > 0:
            pct = no_summary / total * 100
            issues.append(f"  - æ æè¦? {no_summary:,} ({pct:.1f}%)")
        if no_5w1h > 0:
            pct = no_5w1h / total * 100
            issues.append(f"  - æ?W1H: {no_5w1h:,} ({pct:.1f}%)")

        if issues:
            print("\n".join(issues))
        else:
            print("  â?æ°æ®è'¨éè¯å¥½ïæ çºå¤±å­æ®µ"')

        quality_score = (total - no_domain - no_score - no_content) / total * 100 if total > 0 else 0
        print(f"\nð æ°æ®è'¨éè¯å: {quality_score:.1f}%"')

        print("\n" + "=" * 60)

    def export(self, output_file: str, days: int = 30, domain: str = None):
    """å¯åºæ°æ®"""
        if domain:
            news_list = self.db.search_by_domain(domain, days * 24)
        else:
            news_list = self.db.get_history_news(days)

        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)

        print(f"\nâ?å·²å¯å?{len(news_list)} æ¡æ°éå°: {output_path}")

    def show_rejected_stats(self):
        """æ¾ç¤ºè«æçæ°éçè®?""
        log_dir = PROJECT_ROOT / "data" / "filter_logs"

        if not log_dir.exists():
            print("\nâ?æªæ¾å°è¿æ¤æ¥å¿ç®å½?")
            return

        print("\n" + "=" * 60)
        print("ð è«æçæ°éçè®?")
        print("=" * 60)

        total_rejected = 0
        reason_counts = {}

        for log_file in log_dir.glob("ai_filter_*.jsonl"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            log = json.loads(line)
                            if log.get('action') == 'fact_check':
                                result = log.get('result', {})
                                if not result.get('is_factual', True):
                                    total_rejected += 1
                                    reason = result.get('content_type', 'æªç¥')
                                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                        except:
                            pass
            except:
                pass

        print(f"\nð¦ ææçæ°: {total_rejected:,}")

        if reason_counts:
            print("\nð æçåå åå¸:")
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                pct = count / total_rejected * 100 if total_rejected > 0 else 0
                print(f"  - {reason}: {count:,} ({pct:.1f}%)")

        print("\n" + "=" * 60)

def main():
    parser = argparse.ArgumentParser(description="æ°æ®åºç®¡çCLIå·¥å·")
    subparsers = parser.add_subparsers(dest="command", help="å¯ç¨å½ä¤")

    parser_stats = subparsers.add_parser("stats", help="æ¾ç¤ºæ°æ®åºçè®?")

    parser_recent = subparsers.add_parser("recent", help="æ¾ç¤ºæè¿æ°é?")
    parser_recent.add_argument("--hours", type=int, default=24, help="æ¶é'èå'ïå°æ¶ï")
    parser_recent.add_argument("--domain", type=str, help="æéåç­é?")
    parser_recent.add_argument("--limit", type=int, default=20, help="æ¾ç¤ºæ°é")

    parser_search = subparsers.add_parser("search", help="æç'æ°é"')
    parser_search.add_argument("keyword", help="æç'å³é®è¯ïéå·åéå¤ä¸ªï?")
    parser_search.add_argument("--days", type=int, default=30, help="æç'å¤©æ°"')

    parser_detail = subparsers.add_parser("detail", help="æ¾ç¤ºæ°éè¯¦æ")
    parser_detail.add_argument("news_id", help="æ°éID")

    parser_quality = subparsers.add_parser("quality", help="æ£æ¥æ°æ®è'¨é?")

    parser_export = subparsers.add_parser("export", help="å¯åºæ°æ®")
    parser_export.add_argument("output", help="è¾åºæä¶è·¯å¾")
    parser_export.add_argument("--days", type=int, default=30, help="å¯åºå¤©æ°")
    parser_export.add_argument("--domain", type=str, help="æéåç­é?")

    parser_rejected = subparsers.add_parser("rejected", help="æ¾ç¤ºè«æçæ°éçè®?")

    args = parser.parse_args()

    manager = DatabaseManager()

    if args.command == "stats":
        manager.show_stats()
    elif args.command == "recent":
        manager.show_recent(args.hours, args.domain, args.limit)
    elif args.command == "search":
        manager.search(args.keyword, args.days)
    elif args.command == "detail":
        manager.show_detail(args.news_id)
    elif args.command == "quality":
        manager.check_quality()
    elif args.command == "export":
        manager.export(args.output, args.days, args.domain)
    elif args.command == "rejected":
        manager.show_rejected_stats()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

"""
        log_dir = PROJECT_ROOT / "data" / "filter_logs"

        if not log_dir.exists():
            print("\nâ?æªæ¾å°è¿æ¤æ¥å¿ç®å½?")
            return

        print("\n" + "=" * 60)
        print("ð è«æçæ°éçè®?")
        print("=" * 60)

        total_rejected = 0
        reason_counts = {}

        for log_file in log_dir.glob("ai_filter_*.jsonl"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            log = json.loads(line)
                            if log.get('action') == 'fact_check':
                                result = log.get('result', {})
                                if not result.get('is_factual', True):
                                    total_rejected += 1
                                    reason = result.get('content_type', 'æªç¥')
                                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                        except:
                            pass
            except:
                pass

        print(f"\nð¦ ææçæ°: {total_rejected:,}")

        if reason_counts:
            print("\nð æçåå åå¸:")
            for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
                pct = count / total_rejected * 100 if total_rejected > 0 else 0
                print(f"  - {reason}: {count:,} ({pct:.1f}%)")

        print("\n" + "=" * 60)

def main():
    parser = argparse.ArgumentParser(description="æ°æ®åºç®¡çCLIå·¥å·")
    subparsers = parser.add_subparsers(dest="command", help="å¯ç¨å½ä¤")

    parser_stats = subparsers.add_parser("stats", help="æ¾ç¤ºæ°æ®åºçè®?")

    parser_recent = subparsers.add_parser("recent", help="æ¾ç¤ºæè¿æ°é?")
    parser_recent.add_argument("--hours", type=int, default=24, help="æ¶é'èå'ïå°æ¶ï")
    parser_recent.add_argument("--domain", type=str, help="æéåç­é?")
    parser_recent.add_argument("--limit", type=int, default=20, help="æ¾ç¤ºæ°é")

    parser_search = subparsers.add_parser("search", help="æç'æ°é"')
    parser_search.add_argument("keyword", help="æç'å³é®è¯ïéå·åéå¤ä¸ªï?")
    parser_search.add_argument("--days", type=int, default=30, help="æç'å¤©æ°"')

    parser_detail = subparsers.add_parser("detail", help="æ¾ç¤ºæ°éè¯¦æ")
    parser_detail.add_argument("news_id", help="æ°éID")

    parser_quality = subparsers.add_parser("quality", help="æ£æ¥æ°æ®è'¨é?")

    parser_export = subparsers.add_parser("export", help="å¯åºæ°æ®")
    parser_export.add_argument("output", help="è¾åºæä¶è·¯å¾")
    parser_export.add_argument("--days", type=int, default=30, help="å¯åºå¤©æ°")
    parser_export.add_argument("--domain", type=str, help="æéåç­é?")

    parser_rejected = subparsers.add_parser("rejected", help="æ¾ç¤ºè«æçæ°éçè®?")

    args = parser.parse_args()

    manager = DatabaseManager()

    if args.command == "stats":
        manager.show_stats()
    elif args.command == "recent":
        manager.show_recent(args.hours, args.domain, args.limit)
    elif args.command == "search":
        manager.search(args.keyword, args.days)
    elif args.command == "detail":
        manager.show_detail(args.news_id)
    elif args.command == "quality":
        manager.check_quality()
    elif args.command == "export":
        manager.export(args.output, args.days, args.domain)
    elif args.command == "rejected":
        manager.show_rejected_stats()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
