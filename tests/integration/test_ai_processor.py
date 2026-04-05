#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - AI处理器模块

测试范围：
- Provider配置加载
- AI处理器初始化
- 重试机制
- 聊天功能(Mock)
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.processor.ai_processor import (
    BaseProvider, AIProcessor, get_ai_config,
    load_providers_config, retry_on_failure
)


class TestLoadProvidersConfig:
    """加载厂商配置测试"""

    def test_load_config_success(self):
        """测试成功加载配置"""
        config = load_providers_config()
        assert 'providers' in config
        assert isinstance(config['providers'], dict)

    def test_load_config_has_required_fields(self):
        """测试配置包含必需字段"""
        config = load_providers_config()
        providers = config.get('providers', {})
        if 'doubao' in providers:
            doubao = providers['doubao']
            assert 'sdk' in doubao
        if 'deepseek' in providers:
            deepseek = providers['deepseek']
            assert 'sdk' in deepseek


class TestGetAIConfig:
    """获取AI配置测试"""

    def test_get_ai_config_filter(self):
        """测试获取FILTER配置"""
        config = get_ai_config('FILTER')
        assert 'provider' in config
        assert 'model' in config
        assert 'api_key' in config
        assert 'base_url' in config

    def test_get_ai_config_analysis(self):
        """测试获取ANALYSIS配置"""
        config = get_ai_config('ANALYSIS')
        assert 'provider' in config
        assert config['provider'] == 'deepseek'

    def test_get_ai_config_backup(self):
        """测试获取BACKUP配置"""
        config = get_ai_config('BACKUP')
        assert 'provider' in config
        assert isinstance(config['provider'], str)

    def test_get_ai_config_invalid_purpose(self):
        """测试无效用途"""
        config = get_ai_config('INVALID')
        assert config == {}

    def test_get_ai_config_case_insensitive(self):
        """测试大小写不敏感"""
        config1 = get_ai_config('filter')
        config2 = get_ai_config('FILTER')
        config3 = get_ai_config('Filter')
        assert config1['provider'] == config2['provider'] == config3['provider']


class TestBaseProvider:
    """基础Provider测试"""

    def test_provider_initialization(self):
        """测试Provider初始化"""
        config = {
            'provider': 'test',
            'model': 'test-model',
            'api_key': 'test-key',
            'base_url': 'https://test.api.com/v1',
            'sdk': 'openai'
        }
        provider = BaseProvider(config)
        assert provider.provider == 'test'
        assert provider.model == 'test-model'
        assert provider.api_key == 'test-key'

    def test_provider_is_available_with_key(self):
        """测试有API Key时可用"""
        config = {
            'provider': 'test',
            'model': 'test-model',
            'api_key': 'valid-key',
            'base_url': 'https://test.api.com/v1',
            'sdk': 'openai'
        }
        with patch('core.processor.ai_processor.BaseProvider._get_client') as mock_client:
            mock_client.return_value = Mock()
            provider = BaseProvider(config)
            assert provider.is_available() == True

    def test_provider_is_available_without_key(self):
        """测试无API Key时不可用"""
        config = {
            'provider': 'test',
            'model': 'test-model',
            'api_key': '',
            'base_url': 'https://test.api.com/v1',
            'sdk': 'openai'
        }
        provider = BaseProvider(config)
        assert provider.is_available() == False

    def test_provider_extra_headers(self):
        """测试额外headers配置"""
        config = {
            'provider': 'openrouter',
            'model': 'test-model',
            'api_key': 'test-key',
            'base_url': 'https://openrouter.ai/api/v1',
            'sdk': 'openai',
            'extra_headers': {
                'HTTP-Referer': 'https://github.com/test',
                'X-Title': 'Test App'
            }
        }
        provider = BaseProvider(config)
        assert provider.extra_headers == {
            'HTTP-Referer': 'https://github.com/test',
            'X-Title': 'Test App'
        }


class TestRetryOnFailure:
    """重试装饰器测试"""

    def test_retry_success_on_first_try(self):
        """测试第一次成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.1)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """测试失败后成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.1)
        def eventually_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("临时错误")
            return "success"

        result = eventually_success()
        assert result == "success"
        assert call_count == 3

    def test_retry_all_failures(self):
        """测试全部失败"""
        call_count = 0

        @retry_on_failure(max_retries=2, delay=0.1)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("持续错误")

        with pytest.raises(ValueError):
            always_fail()
        assert call_count == 3


class TestAIProcessor:
    """AI处理器测试"""

    @pytest.fixture
    def processor(self):
        return AIProcessor()

    def test_processor_initialization(self, processor):
        """测试处理器初始化"""
        assert processor.logger is not None
        assert isinstance(processor._providers, dict)

    def test_processor_has_filter_provider(self, processor):
        """测试有FILTER Provider"""
        assert 'FILTER' in processor._providers
        assert processor._providers['FILTER'] is not None

    def test_processor_has_analysis_provider(self, processor):
        """测试有ANALYSIS Provider"""
        assert 'ANALYSIS' in processor._providers
        assert processor._providers['ANALYSIS'] is not None

    def test_processor_get_provider(self, processor):
        """测试获取Provider"""
        provider = processor.get_provider('FILTER')
        assert provider is not None

    def test_processor_get_invalid_provider(self, processor):
        """测试获取无效 Provider"""
        provider = processor.get_provider('INVALID')
        assert provider is None or hasattr(provider, 'provider')


class TestProviderChat:
    """Provider聊天测试"""

    @patch('core.processor.ai_processor.BaseProvider._get_client')
    def test_chat_success(self, mock_get_client):
        """测试成功聊天"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="测试回复"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        config = {
            'provider': 'test',
            'model': 'test-model',
            'api_key': 'test-key',
            'base_url': 'https://test.api.com/v1',
            'sdk': 'openai'
        }

        provider = BaseProvider(config)
        result = provider.chat([{"role": "user", "content": "测试"}])
        assert result == "测试回复"

    @patch('core.processor.ai_processor.BaseProvider._get_client')
    def test_chat_with_custom_params(self, mock_get_client):
        """测试自定义参数聊天"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="回复"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        config = {
            'provider': 'test',
            'model': 'test-model',
            'api_key': 'test-key',
            'base_url': 'https://test.api.com/v1',
            'sdk': 'openai'
        }

        provider = BaseProvider(config)
        result = provider.chat(
            [{"role": "user", "content": "测试"}],
            temperature=0.5,
            max_tokens=1000
        )

        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['max_tokens'] == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
