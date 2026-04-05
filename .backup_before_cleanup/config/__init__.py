# -*- coding: utf-8 -*-

# config package

"""

统一配置管理接口

提供一致的配置访问方式

"""

from core.config.manager import get_config_manager, load_config, load_sources, get_project_root, get_current_date

from typing import Any, Dict, Optional

# 全局配置管理器实例

_config_manager = None

def get_config(key: str, default: Any = None) -> Any:

    """获取配置值

    支持点号分隔的路径,例如:

    - "sources.domestic.central"

    - "env.deepseek_api_key"

    Args:

        key: 配置键路径

        default: 默认值

    Returns:

        配置值或默认值

    """

    global _config_manager

    if _config_manager is None:

        _config_manager = get_config_manager()

    return _config_manager.get(key, default)

def get_sources() -> Dict[str, Any]:

    """获取源配置

    Returns:

        源配置字典

    """

    global _config_manager

    if _config_manager is None:

        _config_manager = get_config_manager()

    return _config_manager.get_sources()

def get_ai_providers() -> Dict[str, Any]:

    """获取AI提供者配置

    Returns:

        AI提供者配置字典

    """

    global _config_manager

    if _config_manager is None:

        _config_manager = get_config_manager()

    return _config_manager.get_ai_providers()

def get_parsing_rules() -> Dict[str, Any]:

    """获取解析规则配置

    Returns:

        解析规则配置字典

    """

    global _config_manager

    if _config_manager is None:

        _config_manager = get_config_manager()

    return _config_manager.get_parsing_rules()

def get_env(key: str, default: Any = None) -> Any:

    """获取环境变量

    Args:

        key: 环境变量键

        default: 默认值

    Returns:

        环境变量值或默认值

    """

    global _config_manager

    if _config_manager is None:

        _config_manager = get_config_manager()

    return _config_manager.get_env(key, default)

def reload_config() -> None:

    """重新加载配置

    """

    global _config_manager

    _config_manager = get_config_manager()

    _config_manager.load_all()

# 导出常用函数

__all__ = [

    'get_config',

    'get_sources',

    'get_ai_providers',

    'get_parsing_rules',

    'get_env',

    'reload_config',

    'get_project_root',

    'get_current_date',

    'load_config',

    'load_sources'

]
