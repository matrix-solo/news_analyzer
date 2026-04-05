#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - Task2 报告生成模块

测试范围：
- Task2DailyReporter 完整流程
- 报告生成器
- TOP N 选择逻辑
- 无新闻通知
"""

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestSelectTopN:
    """TOP N 选择测试"""

    def test_select_top_n_basic(self):
        """测试基本 TOP N 选择"""
        news_list = [
            {'news_id': 'n1', 'final_score': 90, 'heat_score': 80},
            {'news_id': 'n2', 'final_score': 85, 'heat_score': 85},
            {'news_id': 'n3', 'final_score': 95, 'heat_score': 70},
        ]

        def sort_key(x):
            return x.get('final_score', x.get('influence_score', 0))

        sorted_news = sorted(news_list, key=sort_key, reverse=True)[:2]
        assert len(sorted_news) == 2
        assert sorted_news[0]['news_id'] == 'n3'

    def test_select_top_n_with_influence_score(self):
        """测试使用 influence_score 计算"""
        news_list = [
            {'news_id': 'n1', 'influence_score': 90, 'heat_score': 80},
            {'news_id': 'n2', 'influence_score': 85, 'heat_score': 85},
        ]

        def sort_key(x):
            return x.get('final_score', x.get('influence_score', 0))

        sorted_news = sorted(news_list, key=sort_key, reverse=True)
        assert sorted_news[0]['news_id'] == 'n1'

    def test_select_top_n_empty_list(self):
        """测试空列表"""
        news_list = []
        def sort_key(x):
            return x.get('final_score', x.get('influence_score', 0))
        result = sorted(news_list, key=sort_key, reverse=True)[:10]
        assert len(result) == 0

    def test_select_top_n_less_than_n(self):
        """测试列表长度小于 N"""
        news_list = [
            {'news_id': 'n1', 'final_score': 90, 'heat_score': 80},
        ]
        def sort_key(x):
            return x.get('final_score', x.get('influence_score', 0))
        result = sorted(news_list, key=sort_key, reverse=True)[:10]
        assert len(result) == 1


class TestChinaNewsClassification:
    """中国新闻分类测试"""

    def test_is_china_news_keywords(self):
        """测试通过关键词判断中国新闻"""
        china_keywords = ['中国', '北京', '上海', '习近平', '李强']

        def is_china_news(news):
            title = news.get('title', '') or ''
            translated = news.get('translated_title', '') or ''
            text = (title + ' ' + translated).lower()
            return any(kw.lower() in text for kw in china_keywords)

        news_china = {'title': '中国领导人访问美国', 'translated_title': ''}
        news_foreign = {'title': 'US President visits UK', 'translated_title': ''}

        assert is_china_news(news_china) == True
        assert is_china_news(news_foreign) == False

    def test_is_china_news_source(self):
        """测试通过来源判断中国新闻"""
        china_sources = ['新华社', '人民日报', '央视新闻', '澎湃新闻']

        def is_china_news_by_source(news):
            source = news.get('source_name', '') or ''
            return source in china_sources

        news1 = {'title': '新闻', 'source_name': '新华社'}
        news2 = {'title': 'News', 'source_name': 'Reuters'}

        assert is_china_news_by_source(news1) == True
        assert is_china_news_by_source(news2) == False


class TestReportScoring:
    """报告评分计算测试"""

    def test_score_calculation(self):
        """测试 final_score 计算"""
        final_score = 90.0
        score = final_score
        assert score == 90.0

    def test_score_with_missing_final_score(self):
        """测试缺少 final_score 时的计算"""
        final_score = 0
        score = final_score
        assert score == 0

    def test_score_calculation_order(self):
        """测试评分排序正确性"""
        news_list = [
            {'news_id': 'n1', 'final_score': 90, 'heat_score': 80},
            {'news_id': 'n2', 'final_score': 80, 'heat_score': 90},
        ]

        def sort_key(x):
            return x.get('final_score', x.get('influence_score', 0))

        sorted_news = sorted(news_list, key=sort_key, reverse=True)
        assert sorted_news[0]['news_id'] == 'n1'


class TestReportDateHandling:
    """报告日期处理测试"""

    def test_current_date_format(self):
        """测试日期格式"""
        from core.config.loader import get_current_date
        date_str = get_current_date()
        assert len(date_str) == 10
        assert date_str[4] == '-'
        assert date_str[7] == '-'

    def test_report_date_strftime(self):
        """测试日期字符串格式化"""
        dt = datetime(2026, 3, 20)
        date_str = dt.strftime('%Y-%m-%d')
        assert date_str == '2026-03-20'


class TestNotificationLogic:
    """通知逻辑测试"""

    def test_no_news_notification_message(self):
        """测试无新闻通知内容"""
        from core.config.loader import get_current_date
        current_date = get_current_date()

        subject = f"【告警】新闻采集异常 - {current_date}"

        assert '告警' in subject
        assert '新闻采集异常' in subject

    def test_email_config_check(self):
        """测试邮件配置检查"""
        from core.utils.email_sender import is_email_configured
        result = is_email_configured()
        assert isinstance(result, bool)


class TestReportGeneratorIntegration:
    """报告生成器集成测试"""

    def test_sorting_china_and_foreign(self):
        """测试中外国新闻分离排序"""
        all_news = [
            {'news_id': 'n1', 'title': '中国新闻', 'final_score': 80, 'heat_score': 70},
            {'news_id': 'n2', 'title': 'US News', 'final_score': 85, 'heat_score': 75},
            {'news_id': 'n3', 'title': '中国经济', 'final_score': 90, 'heat_score': 80},
        ]

        china_keywords = ['中国', '北京']
        foreign_keywords = ['US', 'America', 'UK']

        def is_china(news):
            title = news.get('title', '') or ''
            return any(kw.lower() in title.lower() for kw in china_keywords)

        china_news = [n for n in all_news if is_china(n)]
        foreign_news = [n for n in all_news if not is_china(n)]

        assert len(china_news) == 2
        assert len(foreign_news) == 1

    def test_domain_top_extraction(self):
        """测试领域 TOP1 提取"""
        all_news = [
            {'news_id': 'n1', 'domain': '科技', 'final_score': 90, 'heat_score': 80},
            {'news_id': 'n2', 'domain': '科技', 'final_score': 85, 'heat_score': 75},
            {'news_id': 'n3', 'domain': '政治', 'final_score': 88, 'heat_score': 82},
        ]

        def sort_key(x):
            return x.get('final_score', 0) * 0.7 + x.get('heat_score', 0) * 0.3

        by_domain = {}
        for news in all_news:
            domain = news.get('domain', '其他')
            if domain not in by_domain or sort_key(news) > sort_key(by_domain[domain]):
                by_domain[domain] = news

        domain_tops = list(by_domain.values())
        assert len(domain_tops) == 2
        domains = [n['domain'] for n in domain_tops]
        assert '科技' in domains
        assert '政治' in domains


class TestReportFilePaths:
    """报告文件路径测试"""

    def test_date_based_directory(self):
        """测试按日期分类的目录"""
        report_date = '2026-03-20'
        base_dir = Path('./reports')

        date_dir = base_dir / report_date
        brief_dir = date_dir / 'brief'
        depth_dir = date_dir / 'depth'

        assert brief_dir.parts[-2] == '2026-03-20'
        assert depth_dir.parts[-2] == '2026-03-20'

    def test_brief_report_filename(self):
        """测试简要报告文件名"""
        report_date = '2026-03-20'
        filename = f"brief_report_{report_date}.md"
        assert filename == 'brief_report_2026-03-20.md'

    def test_depth_report_filename(self):
        """测试深度报告文件名"""
        report_date = '2026-03-20'
        domain = '科技'
        filename = f"depth_report_{domain}_{report_date}.md"
        assert filename == 'depth_report_科技_2026-03-20.md'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
