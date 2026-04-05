#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ°æ®è¿çèæ¬ïJSON æ°æ® â?SQLite æ°æ®åº?å°ç°æç JSON æ°æ®è¿çå°æ°ç?SQLite æ°æ®åº?""""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config.loader import PROJECT_ROOT
from core.storage.database import NewsDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Migration")

def migrate_analysis_pool(db: NewsDatabase):
    """è¿çå¾åææ± æ°æ®"""
    analysis_pool_dir = Path(PROJECT_ROOT) / "data" / "analysis_pool"

    if not analysis_pool_dir.exists():
        logger.info("å¾åææ± ç®å½ä¸å­å¨ïè·³è¿")
        return 0

    total_migrated = 0

    for pool_file in analysis_pool_dir.glob("pool_*.json"):
        logger.info(f"å¤çæä¶: {pool_file.name}")

        try:
            with open(pool_file, 'r', encoding='utf-8') as f:
                news_list = json.load(f)

            if not isinstance(news_list, list):
                logger.warning(f"  è·³è¿: ä¸æ¯åè¡¨æ å")
                continue

            migrated = 0
            for news in news_list:
                # æåºæ°æ®åºè®°å½?                db_news = {
                    'news_id': news.get('news_id'),
                    'title': news.get('title'),
                    'translated_title': news.get('translated_title'),
                    'link': news.get('link'),
                    'source': news.get('source_type'),
                    'source_name': news.get('source_name'),
                    'pub_date': news.get('pub_date'),
                    'content': news.get('content'),
                    'summary': news.get('short_summary'),

                    # 5W1H
                    'who': news.get('who'),
                    'what': news.get('what'),
                    'when_time': news.get('when_time'),
                    'where_place': news.get('where_place'),
                    'why': news.get('why'),
                    'how': news.get('how'),

                    # åç±
                    'domain': news.get('domain'),
                    'tags': [],
                    'keywords': [],

                    # è¯å
                    'final_score': news.get('final_score'),
                    'score_timeliness': news.get('source_score'),
                    'score_importance': news.get('influence_score'),
                    'score_credibility': news.get('value_score'),
                    'score_impact': news.get('heat_score')
                }

                if db.insert_news(db_news):
                    migrated += 1

            logger.info(f"  è¿ç: {migrated}/{len(news_list)} æ?")
            total_migrated += migrated

        except Exception as e:
            logger.error(f"  éè¯¯: {e}")

    return total_migrated

def migrate_archive_pool(db: NewsDatabase):
    """è¿çå½æ¡£æ± æ°æ?""
    archive_pool_dir = Path(PROJECT_ROOT) / "data" / "archive_pool"

    if not archive_pool_dir.exists():
        logger.info("å½æ¡£æ± ç®å½ä¸å­å¨ïè·³è¿?")
        return 0

    total_migrated = 0

    for archive_file in archive_pool_dir.glob("pool_*.json"):
        logger.info(f"å¤çæä¶: {archive_file.name}")

        try:
            with open(archive_file, 'r', encoding='utf-8') as f:
                news_list = json.load(f)

            if not isinstance(news_list, list):
                logger.warning(f"  è·³è¿: ä¸æ¯åè¡¨æ å")
                continue

            migrated = 0
            for news in news_list:
                # æåºæ°æ®åºè®°å½?                db_news = {
                    'news_id': news.get('news_id'),
                    'title': news.get('title'),
                    'translated_title': news.get('translated_title'),
                    'link': news.get('link'),
                    'source': news.get('source_type'),
                    'source_name': news.get('source_name'),
                    'pub_date': news.get('pub_date'),
                    'content': news.get('content'),
                    'summary': news.get('short_summary'),

                    # 5W1H
                    'who': news.get('who'),
                    'what': news.get('what'),
                    'when_time': news.get('when_time'),
                    'where_place': news.get('where_place'),
                    'why': news.get('why'),
                    'how': news.get('how'),

                    # åç±
                    'domain': news.get('domain'),
                    'tags': [],
                    'keywords': [],

                    # è¯å
                    'final_score': news.get('final_score'),
                    'score_timeliness': news.get('source_score'),
                    'score_importance': news.get('influence_score'),
                    'score_credibility': news.get('value_score'),
                    'score_impact': news.get('heat_score')
                }

                if db.insert_news(db_news):
                    migrated += 1

            logger.info(f"  è¿ç: {migrated}/{len(news_list)} æ?")
            total_migrated += migrated

        except Exception as e:
            logger.error(f"  éè¯¯: {e}")

    return total_migrated

def migrate_history_ids(db: NewsDatabase):
    """è¿çåå²ID"""
    history_file = Path(PROJECT_ROOT) / "data" / "history_ids.json"

    if not history_file.exists():
        logger.info("åå²IDæä¶ä¸å­å¨ïè·³è¿")
        return 0

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_ids = json.load(f)

        if not isinstance(history_ids, list):
            logger.warning("åå²IDä¸æ¯åè¡¨æ åïè·³è¿?")
            return 0

        # æéæ è®°ä¸ºå·²å¤ç
        db.mark_processed_batch(history_ids)

        logger.info(f"è¿çåå²ID: {len(history_ids)} æ?")
        return len(history_ids)

    except Exception as e:
        logger.error(f"è¿çåå²IDéè¯¯: {e}")
        return 0

def main():
    logger.info("=" * 60)
    logger.info("ð¦ æ°æ®è¿çïJSON â?SQLite")
    logger.info("=" * 60)

    # åååæ°æ®åº
    db = NewsDatabase()

    # è¿çå¾åææ± 
    logger.info("")
    logger.info("ð¥ è¿çå¾åææ± ")
    logger.info("-" * 50)
    analysis_count = migrate_analysis_pool(db)

    # è¿çå½æ¡£æ±?    logger.info("")
    logger.info("ð è¿çå½æ¡£æ±?")
    logger.info("-" * 50)
    archive_count = migrate_archive_pool(db)

    # è¿çåå²ID
    logger.info("")
    logger.info("ð è¿çåå²ID")
    logger.info("-" * 50)
    history_count = migrate_history_ids(db)

    # æå°çè®¡
    logger.info("")
    logger.info("=" * 60)
    logger.info("ð è¿çå®æ")
    logger.info("=" * 60)
    logger.info(f"å¾åææ± è¿ç: {analysis_count} æ?")
    logger.info(f"å½æ¡£æ± è¿ç? {archive_count} æ?")
    logger.info(f"åå²IDè¿ç: {history_count} æ?")

    # æ°æ®åºçè®?    stats = db.get_stats()
    logger.info(f"æ°æ®åºæé: {stats['total_news']} æ?")
    logger.info(f"å·²å¤çID: {stats['processed']} æ?")
    logger.info("=" * 60)

    return 0

if __name__ == "__main__":
    sys.exit(main())
