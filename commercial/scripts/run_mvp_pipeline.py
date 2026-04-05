#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVP Pipeline è¿è¡èæ¬
åä¸çæ°éééä¸å¤çæµç¨
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from compliance import (
    CommercialSourceFilter,
    SensitiveContentFilter,
    FieldMapper,
    AISensitiveChecker
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MVPPipeline")

class MVPPipeline:
    """MVPåä¸çå¤çç®¡é?""

    def __init__(
        self,
        sources_config: str = None,
        keywords_config: str = None,
        use_ai_check: bool = False
    ):
        base_path = Path(__file__).parent.parent

        self.source_filter = CommercialSourceFilter(
            config_path=sources_config or str(base_path / "config" / "sources_commercial.yaml")
        )
        self.content_filter = SensitiveContentFilter(
            keywords_path=keywords_config or str(base_path / "compliance" / "keywords.yaml")
        )
        self.field_mapper = FieldMapper(
            config_path=keywords_config or str(base_path / "compliance" / "keywords.yaml")
        )

        self.use_ai_check = use_ai_check
        self.ai_checker = None
        if use_ai_check:
            try:
                self.ai_checker = AISensitiveChecker()
                logger.info("AIææè¯æ£æµå·²å¯ç¨")
            except Exception as e:
                logger.warning(f"AIæ£æµåååå¤±è'¥: {e}ïå°ä½¿ç¨èåæ£æµ?"')
                self.use_ai_check = False

        logger.info("MVP Pipeline åååå®æ?")
        logger.info(f"åè®¸ä¿¡æº: {len(self.source_filter.get_allowed_sources())}ä¸?")
        logger.info(f"ææè¯çè®? {self.content_filter.get_stats()}")

    def process_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        å¤çåæ¡æ°é

        Args:
            news_item: æ°éæ¡ç®ïåå?source, title, content, domain ç­å­æ®?

        Returns:
            Dict: å¤ççæïåå?passed, reason, processed_item ç­å­æ®?
        """
        result = {
            'passed': True,
            'reason': '',
            'processed_item': None,
            'filter_details': {}
        }

        source_name = news_item.get('source', '')
        source_result = self.source_filter.filter_source(source_name)
        if not source_result.passed:
            result['passed'] = False
            result['reason'] = f"ä¿¡æºè¿æ¤å¤±è'¥: {source_result.reason}"'
            result['filter_details']['source_filter'] = source_result.reason
            return result

        result['filter_details']['source_filter'] = 'passed'

        title = news_item.get('title', '')
        content = news_item.get('content', '')
        full_content = f"{title} {content}"

        content_result = self.content_filter.filter_content(full_content)

        if not content_result.passed:
            result['passed'] = False
            result['reason'] = f"åå®è¿æ¤å¤±è'¥: {content_result.reason}"'
            result['filter_details']['content_filter'] = content_result.reason
            return result

        result['filter_details']['content_filter'] = 'passed'

        if self.use_ai_check and self.ai_checker:
            try:
                ai_result = self.ai_checker.check_compliance(title, content)
                result['filter_details']['ai_check'] = {
                    'risk_level': ai_result.risk_level,
                    'is_compliant': ai_result.is_compliant,
                    'categories': ai_result.risk_categories,
                    'confidence': ai_result.confidence
                }

                if ai_result.suggested_action == 'reject':
                    result['passed'] = False
                    result['reason'] = f"AIæ£æµæç? {ai_result.risk_description}"
                    return result

                if ai_result.suggested_action == 'review' or ai_result.confidence < 0.7:
                    result['filter_details']['ai_check']['needs_review'] = True

            except Exception as e:
                logger.warning(f"AIæ£æµæè¡å¤±è'? {e}"')
                result['filter_details']['ai_check'] = f"æ£æµå¤±è'? {str(e)}"'

        domain = news_item.get('domain', '')
        if domain:
            mapped_domain = self.field_mapper.map_field(domain)
            news_item['domain'] = mapped_domain
            if mapped_domain != domain:
                result['filter_details']['field_mapping'] = f"{domain} -> {mapped_domain}"

        result['processed_item'] = news_item
        result['reason'] = 'å¤çæå'

        return result

    def process_batch(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        æéå¤çæ°é

        Args:
            news_items: æ°éåè¡¨

        Returns:
            Dict: å¤ççæçè®¡
        """
        results = {
            'total': len(news_items),
            'passed': 0,
            'rejected': 0,
            'review': 0,
            'details': []
        }

        for item in news_items:
            process_result = self.process_news_item(item)

            if process_result['passed']:
                needs_review = process_result['filter_details'].get('ai_check', {}).get('needs_review', False)
                if needs_review:
                    results['review'] += 1
                else:
                    results['passed'] += 1
            else:
                results['rejected'] += 1

            results['details'].append(process_result)

        logger.info(f"æéå¤çå®æ: æè®¡{results['total']}æ? éè¿{results['passed']}æ? éå®¡æ ¸{results['review']}æ? æç{results['rejected']}æ?")

        return results

    def get_allowed_sources(self) -> List[str]:
        """è·ååè®¸çä¿¡æºåè¡?""
        return self.source_filter.get_allowed_sources()

    def get_stats(self) -> Dict[str, Any]:
    """è·åçè®¡ä¿¡æ¯"""
        return {
            'allowed_sources': len(self.source_filter.get_allowed_sources()),
            'sensitive_keywords': self.content_filter.get_stats(),
            'field_mappings': len(self.field_mapper.get_all_mappings()),
            'ai_check_enabled': self.use_ai_check
        }

def demo():
    """æç¤ºMVP Pipelineåè½"""
    print("=" * 60)
    print("MVP Pipeline æç¤º")
    print("=" * 60)

    pipeline = MVPPipeline()

    print("\nåè®¸çä¿¡æº?")
    for source in pipeline.get_allowed_sources():
        print(f"  - {source}")

    print("\nçè®¡ä¿¡æ¯:")
    stats = pipeline.get_stats()
    print(f"  åè®¸ä¿¡æº: {stats['allowed_sources']}ä¸?")
    print(f"  ææè¯ç±å? {stats['sensitive_keywords']['total_categories']}ä¸?")
    print(f"  ææè¯ææ°: {stats['sensitive_keywords']['total_keywords']}ä¸?")
    print(f"  éåæ å°: {stats['field_mappings']}æ?")
    print(f"  AIæ£æµ? {'å·²å¯ç? if stats['ai_check_enabled'] else 'æªå¯ç?}")

    test_news = [
        {
            'source': 'æ°åç¤?,'
            'title': 'å½å¡éåå¸æ°æ¿ç­',
            'content': 'å½å¡éäæ¥åå¸å³äºçæµåå±çæ°æ¿ç­?..',
            'domain': 'æ¿ç­'
        },
        {
            'source': 'è·¯éç¤¾',
            'title': 'å½éæ°é',
            'content': 'è¿æ¯ä¸æ¡å½éæ°é?..',
            'domain': 'å½é'
        },
        {
            'source': '36æ°?,'
            'title': 'çæå¬å¸è·å¾èèµ',
            'content': 'æçæå¬å¸å®ææ°ä¸è½®èèµ?..',
            'domain': 'çæ'
        }
    ]

    print("\næµè¯æ°éå¤ç:")
    results = pipeline.process_batch(test_news)

    for i, detail in enumerate(results['details']):
        print(f"\næ°é {i+1}:")
        print(f"  æ¥æº: {test_news[i]['source']}")
        print(f"  æ é: {test_news[i]['title']}")
        print(f"  çæ: {'éè¿' if detail['passed'] else 'æç'}")
        print(f"  åå : {detail['reason']}")
        if detail['processed_item']:
            print(f"  æ å°åéå? {detail['processed_item'].get('domain', 'N/A')}")

if __name__ == "__main__":
    demo()
