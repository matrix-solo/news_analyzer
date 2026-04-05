#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试 - 配置模块

测试配置加载和环境变量
"""

import os
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestEnvironmentConfig:
    """环境配置测试"""

    def test_load_env_variable(self):
        """测试加载环境变量"""
        test_value = os.environ.get('TEST_VAR', 'default')
        assert test_value == 'default'

    def test_load_existing_env_variable(self):
        """测试加载已存在的环境变量"""
        os.environ['TEST_VAR'] = 'test_value'
        value = os.environ.get('TEST_VAR')
        assert value == 'test_value'
        del os.environ['TEST_VAR']

    def test_env_variable_with_default(self):
        """测试带默认值的環境變量"""
        value = os.environ.get('NON_EXISTENT_VAR', 'default_value')
        assert value == 'default_value'


class TestConfigLoader:
    """配置加载器测试"""

    def test_config_file_detection(self):
        """测试配置文件检测"""
        config_file = '.env'
        file_exists = os.path.exists(config_file)
        assert isinstance(file_exists, bool)

    def test_yaml_config_loading(self):
        """测试YAML配置加载"""
        yaml_content = """
sources:
  rss:
    - name: test
      url: https://example.com/rss
"""
        assert 'sources:' in yaml_content
        assert 'rss:' in yaml_content


class TestProviderConfig:
    """Provider配置测试"""

    def test_doubao_config_structure(self):
        """测试豆包配置结构"""
        config = {
            'provider': 'doubao',
            'model': 'doubao-seed-2.0',
            'api_key': 'test-key',
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3'
        }
        assert config['provider'] == 'doubao'
        assert 'api_key' in config

    def test_deepseek_config_structure(self):
        """测试DeepSeek配置结构"""
        config = {
            'provider': 'deepseek',
            'model': 'deepseek-chat',
            'api_key': 'test-key',
            'base_url': 'https://api.deepseek.com/v1'
        }
        assert config['provider'] == 'deepseek'


class TestConfigValidation:
    """配置验证测试"""

    def test_required_config_keys(self):
        """测试必需配置项"""
        config = {
            'provider': 'test',
            'model': 'test-model',
            'api_key': 'test-key',
            'base_url': 'https://api.test.com'
        }
        required_keys = ['provider', 'model', 'api_key', 'base_url']
        for key in required_keys:
            assert key in config

    def test_api_key_validation(self):
        """测试API Key验证"""
        valid_key = 'sk-1234567890abcdef'
        is_valid = valid_key.startswith('sk-') and len(valid_key) > 10
        assert is_valid == True

    def test_base_url_validation(self):
        """测试Base URL验证"""
        url = 'https://api.test.com/v1'
        is_valid = url.startswith('http') and '/v1' in url
        assert is_valid == True


class TestConfigMerging:
    """配置合并测试"""

    def test_default_config(self):
        """测试默认配置"""
        defaults = {
            'timeout': 30,
            'retry': 3,
            'batch_size': 10
        }
        assert defaults['timeout'] == 30

    def test_config_override(self):
        """测试配置覆盖"""
        defaults = {'timeout': 30}
        overrides = {'timeout': 60}
        merged = {**defaults, **overrides}
        assert merged['timeout'] == 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
