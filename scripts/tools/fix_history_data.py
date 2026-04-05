#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史数据修复脚本
将所有 combined_processing_status 为 NULL 的数据设置为 'force_stored'
并填充默认值，确保数据完整性
"""
import sys
sys.path.insert(0, '.')

from core.storage.database import NewsDatabase
from core.processor.data_validator import DataValidator
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_history_data():
    """修复所有历史数据的 combined_processing_status"""
    db = NewsDatabase()
    validator = DataValidator()

    null_status_news = db.get_news_by_status(None)

    logger.info(f"发现 {len(null_status_news)} 条历史数据需要修复")

    success_count = 0
    fail_count = 0

    for news in null_status_news:
        try:
            news_id = news['id']

            validation_result = validator.validate_combined_result(
                news,
                news.get('combined_result', {})
            )

            updates = {}

            if validation_result['status'] in ['valid', 'remediated', 'default_filled']:
                updates['combined_processing_status'] = 'passed'
                updates['validation_status'] = validation_result['status']
            else:
                updates['combined_processing_status'] = 'force_stored'
                updates['validation_status'] = 'default_filled'
                _fill_default_values(news)
                for key, value in news.items():
                    if key in ['score_timeliness', 'score_importance', 'score_credibility',
                               'score_impact', 'heat_score', 'final_score', 'who', 'what',
                               'when_time', 'where_place', 'why', 'how']:
                        updates[key] = value

            db.update_news(news_id, updates)
            success_count += 1
            logger.debug(f"修复: {news['id'][:20]}... -> {updates['combined_processing_status']}")

        except Exception as e:
            logger.error(f"修复失败: {news['id'][:20]}..., error: {e}")
            fail_count += 1

    logger.info(f"历史数据修复完成: 成功 {success_count}, 失败 {fail_count}")


def _fill_default_values(news: dict):
    """填充默认值"""
    if not news.get('final_score') or news.get('final_score') == 0:
        st = news.get('score_timeliness', 50.0) or 50.0
        si = news.get('score_importance', 50.0) or 50.0
        sc = news.get('score_credibility', 50.0) or 50.0
        sip = news.get('score_impact', 50.0) or 50.0
        news['final_score'] = st * 0.25 + si * 0.25 + sc * 0.25 + sip * 0.25

    if not news.get('score_timeliness'):
        news['score_timeliness'] = 50.0
    if not news.get('score_importance'):
        news['score_importance'] = 50.0
    if not news.get('score_credibility'):
        news['score_credibility'] = 50.0
    if not news.get('score_impact'):
        news['score_impact'] = 50.0
    if not news.get('heat_score'):
        news['heat_score'] = 50.0

    if not news.get('who'):
        news['who'] = '暂未明确'
    if not news.get('what'):
        news['what'] = '暂未明确'
    if not news.get('when_time'):
        news['when_time'] = news.get('pub_date', '暂未明确')
    if not news.get('where_place'):
        news['where_place'] = '暂未明确'
    if not news.get('why'):
        news['why'] = '暂未明确'
    if not news.get('how'):
        news['how'] = '暂未明确'


if __name__ == '__main__':
    logger.info("开始修复历史数据...")
    fix_history_data()
    logger.info("修复完成")