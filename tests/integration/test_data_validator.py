#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - Step 9 数据完整性校验模块

测试范围：
- 5W1H 字段校验
- 评分字段校验
- 领域分类校验
- AI 补救机制
- 默认值填充
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.processor.data_validator import DataValidator


class TestDataValidator:
    """数据校验器测试"""

    @pytest.fixture
    def validator(self):
        """创建校验器实例"""
        return DataValidator()

    @pytest.fixture
    def valid_news(self):
        """有效新闻数据"""
        return {
            'news_id': 'test123',
            'title': '测试新闻',
            'source_name': '测试源'
        }

    @pytest.fixture
    def valid_result(self):
        """有效结果数据"""
        return {
            'translation': 'Test translation',
            'summary': 'Test summary',
            'analysis': {
                'who': '测试人物',
                'what': '测试内容',
                'when': '2026-03-20',
                'where': '测试地点',
                'why': '测试原因',
                'how': '测试方式'
            },
            'scoring': {
                'source_score': 85,
                'influence_score': 80,
                'value_score': 75,
                'compliance_score': 90
            },
            'domain': '科技'
        }


class TestValidationRules(TestDataValidator):
    """验证规则测试"""

    def test_validate_translation_valid(self, validator):
        """测试翻译验证 - 有效"""
        result = validator._validate_translation("这是一段翻译")
        assert result['status'] == 'valid'

    def test_validate_translation_empty(self, validator):
        """测试翻译验证 - 空值"""
        result = validator._validate_translation("")
        assert result['status'] == 'error'
        assert '空' in result['message']

    def test_validate_summary_valid(self, validator):
        """测试摘要验证 - 有效"""
        result = validator._validate_summary("这是一段摘要")
        assert result['status'] == 'valid'

    def test_validate_summary_empty(self, validator):
        """测试摘要验证 - 空值"""
        result = validator._validate_summary("")
        assert result['status'] == 'error'
        assert '空' in result['message']

    def test_validate_analysis_valid(self, validator):
        """测试分析验证 - 有效"""
        analysis = {
            'who': '人物',
            'what': '内容',
            'when': '2026-03-20',
            'where': '地点',
            'why': '原因',
            'how': '方式'
        }
        result = validator._validate_analysis(analysis)
        assert result['status'] == 'valid'

    def test_validate_analysis_missing_field(self, validator):
        """测试分析验证 - 缺失字段"""
        analysis = {
            'who': '人物',
            'what': '内容'
        }
        result = validator._validate_analysis(analysis)
        assert result['status'] == 'error'
        assert '缺失5W1H字段' in result['message']

    def test_validate_scoring_valid(self, validator):
        """测试评分验证 - 有效"""
        scoring = {
            'source_score': 85,
            'influence_score': 80,
            'value_score': 75,
            'compliance_score': 90
        }
        result = validator._validate_scoring(scoring)
        assert result['status'] == 'valid'

    def test_validate_scoring_missing_field(self, validator):
        """测试评分验证 - 缺失字段"""
        scoring = {
            'source_score': 85,
            'influence_score': 80
        }
        result = validator._validate_scoring(scoring)
        assert result['status'] == 'error'
        assert '缺失评分字段' in result['message']

    def test_validate_scoring_empty(self, validator):
        """测试评分验证 - 空值"""
        result = validator._validate_scoring(None)
        assert result['status'] == 'error'

    def test_validate_domain_valid(self, validator):
        """测试领域验证 - 有效"""
        result = validator._validate_domain('科技')
        assert result['status'] == 'valid'

    def test_validate_domain_invalid(self, validator):
        """测试领域验证 - 无效"""
        result = validator._validate_domain('非法领域')
        assert result['status'] == 'error'
        assert '无效' in result['message']

    def test_validate_domain_empty(self, validator):
        """测试领域验证 - 空值"""
        result = validator._validate_domain('')
        assert result['status'] == 'error'


class TestCombinedValidation(TestDataValidator):
    """组合验证测试"""

    def test_validate_combined_result_all_valid(self, validator, valid_news, valid_result):
        """测试组合验证 - 全部有效"""
        result = validator.validate_combined_result(valid_news, valid_result)
        assert result['status'] == 'valid'
        assert 'results' in result

    def test_validate_combined_result_missing_field(self, validator, valid_news, valid_result):
        """测试组合验证 - 缺失字段"""
        del valid_result['translation']
        result = validator.validate_combined_result(valid_news, valid_result)
        assert result['status'] in ['default_filled', 'remediated']
        assert 'results' in result

    def test_validate_combined_result_multiple_errors(self, validator, valid_news, valid_result):
        """测试组合验证 - 多处错误"""
        valid_result['translation'] = ''
        valid_result['summary'] = ''
        result = validator.validate_combined_result(valid_news, valid_result)
        assert result['status'] in ['default_filled', 'remediated']


class TestAIRemediation(TestDataValidator):
    """AI补救测试"""

    def test_ai_remediation_no_provider(self, validator):
        """测试无AI provider时不补救"""
        validation_results = {
            'translation': {'status': 'error', 'message': '翻译为空'}
        }
        result = validator._attempt_ai_remediation({}, {}, validation_results)
        assert result is None

    def test_ai_remediation_no_failed_fields(self, validator):
        """测试没有失败字段时不补救"""
        validator.ai_provider = Mock()
        validation_results = {
            'translation': {'status': 'valid'}
        }
        result = validator._attempt_ai_remediation({}, {}, validation_results)
        assert result is None

    def test_ai_remediation_success(self, validator):
        """测试AI补救成功"""
        validator.ai_provider = Mock(return_value='{"fixed_field": "value"}')

        validation_results = {
            'translation': {'status': 'error', 'message': '翻译为空'}
        }

        news = {'title': '测试新闻', 'source_name': '测试源'}
        result = validator._attempt_ai_remediation(news, {}, validation_results)
        assert result is not None

    def test_ai_remediation_failure(self, validator):
        """测试AI补救失败"""
        validator.ai_provider = Mock(side_effect=Exception("API错误"))

        validation_results = {
            'translation': {'status': 'error', 'message': '翻译为空'}
        }

        result = validator._attempt_ai_remediation({}, {}, validation_results)
        assert result is None


class TestDefaultValues(TestDataValidator):
    """默认值填充测试"""

    def test_fill_default_values(self, validator):
        """测试默认值填充"""
        result = {
            'translation': '',
            'summary': '有效摘要',
            'analysis': {},
            'scoring': {
                'source_score': 60,
                'influence_score': 60,
                'value_score': 60,
                'compliance_score': 60
            },
            'domain': '科技'
        }

        validation_results = {
            'translation': {'status': 'error'},
            'summary': {'status': 'valid'},
            'analysis': {'status': 'error'},
            'scoring': {'status': 'valid'},
            'domain': {'status': 'valid'}
        }

        defaults = validator._fill_default_values(result, validation_results)
        assert 'translation' in defaults
        assert defaults['translation'] == '暂无翻译'
        assert 'analysis.what' in defaults
        assert defaults['analysis.what'] == '暂无信息'
        assert 'analysis.who' in defaults
        assert defaults['analysis.who'] == '暂无信息'


class TestValidDomains(TestDataValidator):
    """有效领域测试"""

    def test_valid_domains_list(self, validator):
        """测试有效领域列表"""
        expected_domains = ['政治', '经济', '科技', '军事', '社会', '文化', '体育', '娱乐']
        assert validator.VALID_DOMAINS == expected_domains

    def test_all_domains_recognized(self, validator):
        """测试所有领域都被识别"""
        for domain in validator.VALID_DOMAINS:
            result = validator._validate_domain(domain)
            assert result['status'] == 'valid'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
