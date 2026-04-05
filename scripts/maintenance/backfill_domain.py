#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回填领域标签脚本

为未分类的新闻补充领域标签
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import get_db
from core.collector import UnifiedRSSCollector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackfillDomain")


def backfill_domains():
    """回填未分类新闻领域标签"""
    db = get_db()
    collector = UnifiedRSSCollector(incremental_mode=False)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, translated_title, title, content 
            FROM news 
            WHERE domain IS NULL OR domain = '' OR domain = '其他'
        """)
        rows = cursor.fetchall()

    if not rows:
        logger.info("无需处理，所有新闻已分类")
        return

    logger.info(f"发现 {len(rows)} 条需要回填的新闻")

    updates = []
    for row in rows:
        news_id = row[0]
        translated_title = row[1] or ''
        title = row[2] or ''
        content = row[3] or ''

        full_title = translated_title if translated_title else title

        domain = collector._guess_domain(
            category='',
            title=full_title,
            content=content
        )

        if domain and domain != '其他':
            updates.append((domain, news_id))
            logger.info(f"回填成功: {full_title[:40]}... -> {domain}")

    if updates:
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    "UPDATE news SET domain = ? WHERE id = ?",
                    updates
                )
                conn.commit()
                logger.info(f"成功回填 {len(updates)} 条新闻领域标签")
        except Exception as e:
            logger.error(f"回填更新失败: {e}")
    else:
        logger.info("没有可回填的新闻")


if __name__ == "__main__":
    backfill_domains()
