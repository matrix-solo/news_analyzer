#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淇璇勫垎涓篘ULL鐨勬柊闂?""""

import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("FixNullScores")


def fix_null_scores():
    """淇璇勫垎涓篘ULL鐨勬柊闂?""
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(''''
            SELECT id, title, score_timeliness, score_importance, score_credibility, score_impact 
            FROM news 
            WHERE score IS NULL OR score = 0
        ''')
        null_news = cursor.fetchall()
        
        if not null_news:
            logger.info("娌℃湁鍙戠幇璇勫垎涓篘ULL鐨勬柊闂?")
            return 0
        
        logger.info(f"鍙戠幇 {len(null_news)} 鏉¤瘎鍒嗕负NULL鐨勬柊闂?")
        
        fixed_count = 0
        for news in null_news:
            news_id = news[0]
            title = news[1]
            score_timeliness = news[2] or 0
            score_importance = news[3] or 0
            score_credibility = news[4] or 0
            score_impact = news[5] or 0
            
            final_score = (
                score_timeliness * 0.25 +
                score_importance * 0.25 +
                score_credibility * 0.25 +
                score_impact * 0.25
            )
            
            cursor.execute(''''
                UPDATE news 
                SET score = ? 
                WHERE id = ?
            ''', (final_score, news_id))
            
            logger.info(f"淇: {title[:30]}... -> 璇勫垎: {final_score:.1f}")
            fixed_count += 1
        
        conn.commit()
        
        logger.info(f"鍏变慨澶?{fixed_count} 鏉℃柊闂荤殑璇勫垎")
        return fixed_count


if __name__ == "__main__":
    sys.exit(fix_null_scores())

