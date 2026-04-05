#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVPå®æ'è¿è¡èæ¬'
åä¸çæ°éééãå¤çãæ¨éå¨æµç¨
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from compliance import (
    CommercialSourceFilter,
    SensitiveContentFilter,
    FieldMapper,
    AISensitiveChecker
)
from subscription import SubscriberManager
from services import CommercialEmailService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MVPFullPipeline")

class MVPFullPipeline:
    """MVPå®æ'å¤çç®¡é"""

    def __init__(self, use_ai_check: bool = False):
        self.source_filter = CommercialSourceFilter(
            config_path=str(base_path / "config" / "sources_commercial.yaml")
        )
        self.content_filter = SensitiveContentFilter(
            keywords_path=str(base_path / "compliance" / "keywords.yaml")
        )
        self.field_mapper = FieldMapper(
            config_path=str(base_path / "compliance" / "keywords.yaml")
        )
        self.subscriber_manager = SubscriberManager()
        self.email_service = CommercialEmailService()

        self.use_ai_check = use_ai_check
        self.ai_checker = None
        if use_ai_check:
            try:
                self.ai_checker = AISensitiveChecker()
                logger.info("AIææè¯æ£æµå·²å¯ç¨")
            except Exception as e:
                logger.warning(f"AIæ£æµåååå¤±è'¥: {e}"')
                self.use_ai_check = False

        logger.info("MVPå®æ'ç®¡éåååå®æ?"')

    def process_news(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        å¤çæ°éåè¡¨

        Args:
            news_items: æ°éåè¡¨

        Returns:
            å¤ççæ
        """
        results = {
            'total': len(news_items),
            'passed': [],
            'rejected': [],
            'needs_review': []
        }

        for item in news_items:
            processed = self._process_single_news(item)
            if processed['passed']:
                if processed.get('needs_review'):
                    results['needs_review'].append(processed)
                else:
                    results['passed'].append(processed)
            else:
                results['rejected'].append(processed)

        logger.info(f"å¤çå®æ: éè¿{len(results['passed'])}, éå®¡æ ¸{len(results['needs_review'])}, æç{len(results['rejected'])}")
        return results

    def _process_single_news(self, news: Dict[str, Any]) -> Dict[str, Any]:
    """å¤çåæ¡æ°é"""
        result = {
            'passed': True,
            'news': news,
            'needs_review': False,
            'reason': ''
        }

        source_result = self.source_filter.filter_source(news.get('source', ''))
        if not source_result.passed:
            result['passed'] = False
            result['reason'] = f"ä¿¡æºè¿æ¤: {source_result.reason}"
            return result

        content = f"{news.get('title', '')} {news.get('content', '')}"
        content_result = self.content_filter.filter_content(content)
        if not content_result.passed:
            result['passed'] = False
            result['reason'] = f"åå®è¿æ¤: {content_result.reason}"
            return result

        if self.use_ai_check and self.ai_checker:
            try:
                ai_result = self.ai_checker.check_compliance(
                    news.get('title', ''),
                    news.get('content', '')
                )
                if ai_result.suggested_action == 'reject':
                    result['passed'] = False
                    result['reason'] = f"AIæ£æµ? {ai_result.risk_description}"
                    return result
                if ai_result.suggested_action == 'review' or ai_result.confidence < 0.7:
                    result['needs_review'] = True
            except Exception as e:
                logger.warning(f"AIæ£æµå¤±è'? {e}"')

        domain = news.get('domain', '')
        if domain:
            news['domain'] = self.field_mapper.map_field(domain)

        return result

    def send_daily_report(
        self,
        subject: str,
        content: str,
        attachments: List[Path] = None
    ) -> Dict[str, int]:
        """
        åéæ¯æ¥æ¥å?        
        Args:
            subject: é®ä¶ä¸é
            content: é®ä¶åå®
            attachments: éä¶åè¡¨

        Returns:
            åéçè®?        """"
        return self.email_service.send_daily_report(
            subject=subject,
            content=content,
            attachments=attachments,
            include_payment_link=True
        )

    def add_subscriber(self, email: str) -> bool:
        """æ·å è®éè?""
        return self.subscriber_manager.add_subscriber(email)

    def get_subscriber_stats(self) -> Dict[str, int]:
        """è·åè®éèçè®?""
        return self.subscriber_manager.get_subscriber_count()

    def get_allowed_sources(self) -> List[str]:
        """è·ååè®¸çä¿¡æºåè¡?""
        return self.source_filter.get_allowed_sources()

def demo():
    """æç¤ºå®æ'åè½"""
    print("=" * 60)
    print("MVP å®æ'ç®¡éæç¤º"')
    print("=" * 60)

    pipeline = MVPFullPipeline()

    print("\nãä¿¡æºéç½®ã?")
    print(f"åè®¸ä¿¡æº: {len(pipeline.get_allowed_sources())}ä¸?")
    for source in pipeline.get_allowed_sources():
        print(f"  - {source}")

    print("\nãè®éèç®¡çã?")
    stats = pipeline.get_subscriber_stats()
    print(f"è®éèçè®? {stats}")

    print("\nãæµè¯è®éã?")
    test_email = "test@example.com"
    if pipeline.add_subscriber(test_email):
        print(f"  æ·å è®éèæå? {test_email}")

    stats = pipeline.get_subscriber_stats()
    print(f"  æ'æ°åçè®? {stats}"')

    print("\nãæ°éå¤çæµè¯ã?")
    test_news = [
        {'source': 'æ°åç¤?, 'title': 'å½å¡éåå¸æ°æ¿ç­', 'content': 'å½å¡éäæ¥åå¸æ°æ¿ç­...', 'domain': 'æ¿ç­'},'
        {'source': 'è·¯éç¤¾', 'title': 'å½éæ°é', 'content': 'å½éæ°éåå®...', 'domain': 'å½é'},
        {'source': 'è'æ°ä åª', 'title': 'è'çæ¥é', 'content': 'è'çæ°éæ¥é...', 'domain': 'çæµ'},'
    ]

    results = pipeline.process_news(test_news)
    print(f"  éè¿: {len(results['passed'])}æ?")
    print(f"  æç: {len(results['rejected'])}æ?")
    print(f"  éå®¡æ ¸: {len(results['needs_review'])}æ?")

    for item in results['rejected']:
        print(f"    æçåå : {item['reason']}")

    print("\næç¤ºå®æï?")

if __name__ == "__main__":
    demo()
