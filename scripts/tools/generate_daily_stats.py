#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ¯æ¥çè®¡æ¥åçæå?ç¨éïçæééãAIåæãæ¥åæ¨éçæ ¸å¿ææ çè®¡
"""

import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger("DailyStats")

class DailyStatsGenerator:
    """æ¯æ¥çè®¡æ¥åçæå?""

    def __init__(self, db_path: str = None, stats_dir: str = None):
        """
        åååçè®¡çæå¨

        Args:
            db_path: æ°æ®åºè·¯å¾?            stats_dir: çè®¡æ¥åè¾åºç®å½
        """
        self.db_path = db_path or str(Path(__file__).parent.parent / "data" / "news.db")
        self.stats_dir = Path(stats_dir or Path(__file__).parent.parent / "data" / "stats")
        self.stats_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, date: str = None) -> Dict[str, Any]:
        """
        çææå®æ¥æççè®¡æ¥å?        
        Args:
            date: æ¥æå­ç¬¦ä¸²ïYYYY-MM-DDïïéè®¤äå¤©

        Returns:
            çè®¡æ°æ®å­å¸
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        stats = {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "collection": self._get_collection_stats(date),
            "ai_analysis": self._get_ai_analysis_stats(date),
            "database": self._get_database_stats(),
            "report": self._get_report_stats(date),
        }

        # ä¿å­ JSON æ¥å
        json_path = self.stats_dir / f"stats_{date}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        # çæ Markdown æ¥å
        md_path = self.stats_dir / f"stats_{date}.md"
        self._generate_markdown_report(stats, md_path)

        logger.info(f"çè®¡æ¥åå·²çæ? {md_path}")

        return stats

    def _get_collection_stats(self, date: str) -> Dict[str, Any]:
    """è·åééçè®¡"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # å½æ¥ééæ°é
            cursor.execute(""""
                SELECT COUNT(*) FROM news 
                WHERE DATE(created_at) = ?
            """, (date,))
            total_collected = cursor.fetchone()[0]

            # ææ¥æºçè®?            cursor.execute("""
                SELECT source_name, COUNT(*) as count
                FROM news 
                WHERE DATE(created_at) = ?
                GROUP BY source_name
                ORDER BY count DESC
            """, (date,))
            by_source = dict(cursor.fetchall())

            # æéåçè®?            cursor.execute("""
                SELECT domain, COUNT(*) as count
                FROM news 
                WHERE DATE(created_at) = ? AND domain IS NOT NULL
                GROUP BY domain
                ORDER BY count DESC
            """, (date,))
            by_domain = dict(cursor.fetchall())

            return {
                "total_collected": total_collected,
                "successful_sources": len([s for s, c in by_source.items() if c > 0]),
                "failed_sources": 0,  # éè¦äæ¥å¿è£æ
                "by_source": by_source,
                "by_domain": by_domain,
            }

    def _get_ai_analysis_stats(self, date: str) -> Dict[str, Any]:
    """è·å AI åæçè®¡"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # å½æ¥å¤çæ°é
            cursor.execute(""""
                SELECT COUNT(*) FROM news 
                WHERE DATE(created_at) = ? AND score IS NOT NULL
            """, (date,))
            total_processed = cursor.fetchone()[0]

            # éè¿æ°éïscore >= 60ï?            cursor.execute("""
                SELECT COUNT(*) FROM news 
                WHERE DATE(created_at) = ? AND score >= 60
            """, (date,))
            passed = cursor.fetchone()[0]

            # æçæ°éïscore < 60ï?            cursor.execute("""
                SELECT COUNT(*) FROM news 
                WHERE DATE(created_at) = ? AND score IS NOT NULL AND score < 60
            """, (date,))
            rejected = cursor.fetchone()[0]

            # ååºæ°éïscore = 50ï?            cursor.execute("""
                SELECT COUNT(*) FROM news 
                WHERE DATE(created_at) = ? AND score = 50
            """, (date,))
            fallback = cursor.fetchone()[0]

            # å³ååæ°
            cursor.execute(""""
                SELECT AVG(score) FROM news 
                WHERE DATE(created_at) = ? AND score IS NOT NULL
            """, (date,))
            avg_score = cursor.fetchone()[0] or 0

            # æåç?            success_rate = (passed / total_processed * 100) if total_processed > 0 else 0

            return {
                "total_processed": total_processed,
                "passed": passed,
                "rejected": rejected,
                "fallback": fallback,
                "success_rate": round(success_rate, 1),
                "avg_score": round(avg_score, 1),
            }

    def _get_database_stats(self) -> Dict[str, Any]:
        """è·åæ°æ®åºçè®?""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # ææ°éæ°
            cursor.execute("SELECT COUNT(*) FROM news")
            total_news = cursor.fetchone()[0]

            # æè¿?24 å°æ¶
            cursor.execute(""""
                SELECT COUNT(*) FROM news 
                WHERE created_at > datetime('now', '-24 hours')
            """)
            recent_24h = cursor.fetchone()[0]

            # æè¿?7 å¤?            cursor.execute("""
                SELECT COUNT(*) FROM news 
                WHERE created_at > datetime('now', '-7 days')
            """)
            recent_7d = cursor.fetchone()[0]

            # æ°æ®åºå¤å°?            db_size = Path(self.db_path).stat().st_size / 1024 / 1024  # MB

            return {
                "total_news": total_news,
                "recent_24h": recent_24h,
                "recent_7d": recent_7d,
                "db_size_mb": round(db_size, 2),
            }

    def _get_report_stats(self, date: str) -> Dict[str, Any]:
    """è·åæ¥åçè®¡"""
        reports_dir = Path(__file__).parent.parent / "reports"

        # æ£æ¥å½æ¥æ¥åæ¯å¦å­å?        report_files = list(reports_dir.glob(f"daily_report_{date}*.md"))
        pdf_files = list(reports_dir.glob(f"daily_report_{date}*.pdf"))

        return {
            "generated": len(report_files) > 0,
            "email_sent": False,  # éè¦äæ¥å¿è£æ
            "report_files": len(report_files),
            "pdf_files": len(pdf_files),
        }

    def _generate_markdown_report(self, stats: Dict[str, Any], output_path: Path):
        """çæ Markdown æ åççè®¡æ¥å?""
        lines = [
            f"# æ¯æ¥çè®¡æ¥å - {stats['date']}",
            "",
            f"çææ¶é': {stats['generated_at']}",'
            "",
            "## ð ééçè®¡",
            "",
            f"- **æéé?*: {stats['collection']['total_collected']} æ?,"
            f"- **æåæº?*: {stats['collection']['successful_sources']} ä¸?,"
            "",
            "### ææ¥æºçè®?,"
            "",
        ]

        for source, count in list(stats['collection']['by_source'].items())[:10]:
            lines.append(f"- {source}: {count} æ?")

        lines.extend([
            "",
            "## ð¤ AI åæçè®¡",
            "",
            f"- **å¤çæ?*: {stats['ai_analysis']['total_processed']} æ?,"
            f"- **éè¿**: {stats['ai_analysis']['passed']} æ?({stats['ai_analysis']['success_rate']}%)",
            f"- **æç**: {stats['ai_analysis']['rejected']} æ?,"
            f"- **ååº**: {stats['ai_analysis']['fallback']} æ?,"
            f"- **å³åå?*: {stats['ai_analysis']['avg_score']}",
            "",
            "## ð¾ æ°æ®åºçè®?,"
            "",
            f"- **ææ°é?*: {stats['database']['total_news']} æ?,"
            f"- **æè¿?24h**: {stats['database']['recent_24h']} æ?,"
            f"- **æè¿?7d**: {stats['database']['recent_7d']} æ?,"
            f"- **æ°æ®åºå¤å°?*: {stats['database']['db_size_mb']} MB",
            "",
            "## ð æ¥åçè®¡",
            "",
            f"- **æ¥åçæ**: {'â? if stats['report']['generated'] else 'â?}",
            f"- **é®ä¶åé?*: {'â? if stats['report']['email_sent'] else 'â?}",
            "",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

def main():
    """ä¸å½æ?""
    import argparse

    parser = argparse.ArgumentParser(description="çææ¯æ¥çè®¡æ¥å")
    parser.add_argument("--date", help="æå®æ¥æïYYYY-MM-DDïïéè®¤äå¤©")
    parser.add_argument("--output", help="è¾åºç®å½")

    args = parser.parse_args()

    generator = DailyStatsGenerator(stats_dir=args.output)
    stats = generator.generate(date=args.date)

    print(f"\nð çè®¡æ¥åå·²çæ?")
    print(f"  - éé: {stats['collection']['total_collected']} æ?")
    print(f"  - AI éè¿: {stats['ai_analysis']['passed']} æ?({stats['ai_analysis']['success_rate']}%)")
    print(f"  - æ°æ®åº? {stats['database']['total_news']} æ?")

if __name__ == "__main__":
    main()
