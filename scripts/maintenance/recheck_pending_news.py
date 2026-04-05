#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æééæ°å¤æ­æ°æ®åºä¸­æªå®æåæçæ°é
ç¨éïå¤ç domainãscore ä¸ºç©ºçæ°éïè¡¥å 5W1H åæ
"""

import sys
import os
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# å è½½ç¯ååé
project_root = Path(__file__).parent
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase
from core.processor.ai_processor import AIProcessor
from core.utils.text_utils import parse_json_str

# éç½®æ¥å¿
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            project_root / 'logs' / f'recheck_news_{datetime.now().strftime("%Y-%m-%d")}.log',
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger("RecheckNews")

class NewsRechecker:
    """æ°ééæ°å¤æ­å¤çå?""

    def __init__(self):
        self.db = NewsDatabase()
        self.ai_processor = AIProcessor()
        self.stats = {
            'total': 0,
            'processed': 0,
            'passed': 0,
            'rejected': 0,
            'failed': 0
        }

    def run(self, batch_size: int = 10, delay: float = 1.0):
        """
        æè¡éæ°å¤æ­

        Args:
            batch_size: æ¯æå¤çæ°é
            delay: æ¯æ¡æ°éå¤çåçå¶è¿ïçï?        """"
        logger.info("=" * 70)
        logger.info("ð æééæ°å¤æ­æªå®æåæçæ°é")
        logger.info("=" * 70)

        # 1. è·åéè¦éæ°å¤æ­çæ°é
        pending_news = self._get_pending_news()
        self.stats['total'] = len(pending_news)

        if not pending_news:
            logger.info("â?æ²¡æéè¦éæ°å¤æ­çæ°é")
            return

        logger.info(f"åç° {len(pending_news)} æ¡éè¦éæ°å¤æ­çæ°é")

        # 2. è·å ANALYSIS æ¨¡åïé«çºæ¨¡åï
        analysis_provider = self.ai_processor.get_provider("ANALYSIS")
        if not analysis_provider:
            logger.warning("ANALYSIS æ¨¡åä¸å¯ç¨ïä½¿ç¨ FILTER æ¨¡å")
            analysis_provider = self.ai_processor.get_provider("FILTER")

        if not analysis_provider:
            logger.error("â?æ²¡æå¯ç¨ç?AI æ¨¡å")
            return

        logger.info(f"ä½¿ç¨æ¨¡å: {analysis_provider.model} ({analysis_provider.provider})")
        logger.info("-" * 70)

        # 3. éæ¡å¤ç
        for i, news in enumerate(pending_news, 1):
            logger.info(f"\n[{i}/{len(pending_news)}] å¤ç: {news['title'][:50]}...")

            try:
                # æåºæç¤ºè¯?                prompt = self._build_prompt(news)
                messages = [{"role": "user", "content": prompt}]

                # è°ç¨ AI
                response = analysis_provider.chat(messages)

                # è£æçæ
                result = self._parse_response(response)

                # æ'æ°æ°æ®åº?                if result['is_factual'] and result['w5h1_score'] >= 3:
                    self._update_news(news['id'], result)
                    self.stats['passed'] += 1
                    logger.info(f"  â?[PASS] 5W1H: {result['w5h1_score']}, Domain: {result['domain']}")
                else:
                    self._mark_rejected(news['id'], result)
                    self.stats['rejected'] += 1
                    logger.info(f"  â?[REJECT] {result.get('content_type', 'æªç¥')}")

                self.stats['processed'] += 1

                # å¶è¿ïé¿å?API éæµ
                if delay > 0:
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"  â ï¸ [ERROR] {e}")
                self.stats['failed'] += 1
                self.stats['processed'] += 1

        # 4. æå°çè®¡
        self._print_summary()

    def _get_pending_news(self) -> List[Dict]:
    """è·åéè¦éæ°å¤æ­çæ°é"""
        import sqlite3

        news_list = []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # æ¥è¯ domain ä¸ºç©ºæ?score ä¸ºç©ºçæ°é?            cursor.execute("""
                SELECT id, title, content, source_name, link
                FROM news 
                WHERE domain IS NULL 
                   OR domain = '' 
                   OR domain = 'None'
                   OR score IS NULL
                   OR score = 0
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()

            for row in rows:
                news_list.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2] or '',
                    'source_name': row[3],
                    'link': row[4]
                })

        return news_list

    def _build_prompt(self, news: Dict) -> str:
        """æåºå¤æ­æç¤ºè¯?""
        return f"""è¯·åæä¥ä¸æ°éïå¤æ­å¶æ¯å¦ä¸ºäºå®ææ°éïå¶è¿è¡?W1Håæã?"
## å¾åææ°é?
æ éï{news['title']}
æ¥æºï{news.get('source_name', 'æªç¥')}
åå®ï{news.get('content', '')[:1000]}

## è¾åºè¦æ±

è¯·ä¥JSONæ åè¾åºïä¸è¦åå«ää½å¶äæå­ï
{{
    "is_factual": trueæfalse,
    "content_type": "æ°é/è¯è®º/å¿å/å¶ä",
    "w5h1_analysis": {{
        "who": "äºä¶ä¸ä½",
        "what": "äºä¶åå®",
        "when": "äºä¶æ¶é'",'
        "where": "äºä¶å°ç",
        "why": "äºä¶åå ",
        "how": "äºä¶æå"
    }},
    "w5h1_score": 0å?çæ'æ?'
    "domain": "æ¿æ²/çæµ/çæ/ä½è²/å¨±ä/ç¤¾ä/å¥åº·/æå/åäº/å¶ä",
    "confidence": 0.0å?.0,
    "short_summary": "ä¸å¥è¯æè¦"
}}

æ³¨æï?1. w5h1_score æ?5W1H åæçå®æ'åº¦å¾åï?-6åï'
2. domain å¿é¡æ¯ä¸è¿°éé¡ää¸
3. å¦æä¸æ¯äºå®ææ°éïis_factual è®¾ä¸º false""""

    def _parse_response(self, response: str) -> Dict:
    """è£æ AI ååº"""
        try:
            result = parse_json_str(response)
            if not isinstance(result, dict):
                raise ValueError("ååºä¸æ¯ææçJSONå¯è±¡")

            # éªè¯å¿è¦å­æ®µ
            return {
                'is_factual': result.get('is_factual', False),
                'content_type': result.get('content_type', 'å¶ä'),
                'w5h1_analysis': result.get('w5h1_analysis', {}),
                'w5h1_score': result.get('w5h1_score', 0),
                'domain': result.get('domain', 'å¶ä'),
                'confidence': result.get('confidence', 0.0),
                'short_summary': result.get('short_summary', '')
            }
        except Exception as e:
            logger.debug(f"è£æååºå¤±è'¥: {e}, ååº: {response[:200]}"')
            return {
                'is_factual': False,
                'content_type': 'è£æå¤±è'¥','
                'w5h1_analysis': {},
                'w5h1_score': 0,
                'domain': 'å¶ä',
                'confidence': 0.0,
                'short_summary': ''
            }

    def _update_news(self, news_id: str, result: Dict):
    """æ'æ°æ°éè®°å½"""
        w5h1 = result.get('w5h1_analysis', {})

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(""""
                UPDATE news SET
                    domain = ?,
                    score = 75.0,
                    who = ?,
                    what = ?,
                    when_time = ?,
                    where_place = ?,
                    why = ?,
                    how = ?,
                    summary = ?
                WHERE id = ?
            """, (
                result.get('domain', 'å¶ä'),
                w5h1.get('who', ''),
                w5h1.get('what', ''),
                w5h1.get('when', ''),
                w5h1.get('where', ''),
                w5h1.get('why', ''),
                w5h1.get('how', ''),
                result.get('short_summary', ''),
                news_id
            ))

    def _mark_rejected(self, news_id: str, result: Dict):
    """æ è®°ä¸ºå·²æç"""
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(""""
                UPDATE news SET
                    domain = 'å·²æç?,'
                    score = 0
                WHERE id = ?
            """, (news_id,))

    def _print_summary(self):
    """æå°çè®¡æè¦"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("ð éæ°å¤æ­å®æ")
        logger.info("=" * 70)
        logger.info(f"æå¤çæ°: {self.stats['total']} æ?")
        logger.info(f"å·²å¤ç? {self.stats['processed']} æ?")
        logger.info(f"  â?éè¿: {self.stats['passed']} æ?")
        logger.info(f"  â?æç: {self.stats['rejected']} æ?")
        logger.info(f"  â ï¸ å¤±è'¥: {self.stats['failed']} æ?"')
        logger.info("=" * 70)

def main():
    """ä¸å½æ?""
    import argparse

    parser = argparse.ArgumentParser(description='æééæ°å¤æ­æªå®æåæçæ°é')
    parser.add_argument('--batch-size', type=int, default=10, help='æ¯æå¤çæ°é')
    parser.add_argument('--delay', type=float, default=1.0, help='æ¯æ¡æ°éå¤çåçå¶è¿ïçï?')
    parser.add_argument('--dry-run', action='store_true', help='äæ£æ¥ïä¸å®éå¤ç?')

    args = parser.parse_args()

    rechecker = NewsRechecker()

    if args.dry_run:
        # äæ£æ¥æ¨¡å?        pending = rechecker._get_pending_news()
        print(f"\nåç° {len(pending)} æ¡éè¦éæ°å¤æ­çæ°é")
        print("\nå?0æ?")
        for i, news in enumerate(pending[:10], 1):
            print(f"{i}. {news['title'][:50]}... (æ¥æº: {news['source_name']})")
        return

    rechecker.run(batch_size=args.batch_size, delay=args.delay)

if __name__ == "__main__":
    main()

"""
    import argparse

    parser = argparse.ArgumentParser(description='æééæ°å¤æ­æªå®æåæçæ°é')
    parser.add_argument('--batch-size', type=int, default=10, help='æ¯æå¤çæ°é')
    parser.add_argument('--delay', type=float, default=1.0, help='æ¯æ¡æ°éå¤çåçå¶è¿ïçï?')
    parser.add_argument('--dry-run', action='store_true', help='äæ£æ¥ïä¸å®éå¤ç?')

    args = parser.parse_args()

    rechecker = NewsRechecker()

    if args.dry_run:
        # äæ£æ¥æ¨¡å?        pending = rechecker._get_pending_news()
        print(f"\nåç° {len(pending)} æ¡éè¦éæ°å¤æ­çæ°é")
        print("\nå?0æ?")
        for i, news in enumerate(pending[:10], 1):
            print(f"{i}. {news['title'][:50]}... (æ¥æº: {news['source_name']})")
        return

    rechecker.run(batch_size=args.batch_size, delay=args.delay)

if __name__ == "__main__":
    main()
