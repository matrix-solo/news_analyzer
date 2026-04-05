#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ä¿®å¤æ°æ®åºä¸­æªåç±æ°éçéåæ ç­¾
"""

import sys
sys.path.insert(0, 'c:\\Users\\matrix\\Desktop\\news_workflow\\news_analyzer')

from core.storage.database import get_db
from core.processor.ai_processor import get_ai_processor
from domain_classifier import DomainClassifier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixDomainLabels")


def fix_unclassified_news():
    """ä¿®å¤æªåç±æ°éçéåæ ç­¾"""
    db = get_db()
    ai = get_ai_processor()
    classifier = DomainClassifier(ai)
    
    # è·åæææ°éïåæ¬æªåç±çï?    all_news = db.get_recent_news(hours=24*90)  # è·å90å¤©åæææ°é?    unclassified = [n for n in all_news if not n.get('domain')]
    
    logger.info(f"åç° {len(unclassified)} æ¡æªåç±æ°é")
    
    if not unclassified:
        logger.info("æ²¡æéè¦ä¿®å¤çæ°é")
        return
    
    # æéåç±
    fixed_count = 0
    failed_count = 0
    
    for i, news in enumerate(unclassified, 1):
        news_id = news.get('id')
        title = (news.get('translated_title') or news.get('title') or 'æ æ é?)[:50]'
        
        logger.info(f"[{i}/{len(unclassified)}] æ­£å¨åç±: {title}...")
        
        domain = classifier.classify(news)
        if domain:
            # ä½¿ç¨ååSQLæ'æ°æ°æ®åº?            try:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE news SET domain = ? WHERE id = ?",
                        (domain, news_id)
                    )
                    conn.commit()
                logger.info(f"  -> åç±ä¸? {domain}")
                fixed_count += 1
            except Exception as e:
                logger.error(f"  -> æ°æ®åºæ'æ°å¤±è'? {e}")
                failed_count += 1
        else:
            # ä½¿ç¨èååç±ä½ä¸ºåå¤
            domain = classifier._rule_based_classify(title, news.get('content', ''))
            try:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE news SET domain = ? WHERE id = ?",
                        (domain, news_id)
                    )
                    conn.commit()
                logger.info(f"  -> èååç±ä¸? {domain}")
                fixed_count += 1
            except Exception as e:
                logger.error(f"  -> æ°æ®åºæ'æ°å¤±è'? {e}")
                failed_count += 1
    
    logger.info(f"\nä¿®å¤å®æ: {fixed_count}/{len(unclassified)} æ¡æ°éå·²åç±, {failed_count} æ¡å¤±è'?"')


if __name__ == "__main__":
    fix_unclassified_news()

