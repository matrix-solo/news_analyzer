#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""信源评分 - 基于 sources.yaml 的 Tier 层级"""
import os
import yaml
import logging

logger = logging.getLogger(__name__)

# Tier 层级到分数的映射（基于 collection_strategy 中的 weight）
# 统一为 0-10 范围
# tier1: weight 9-10 → 9.5
# tier2: weight 7-8 → 7.5
# tier3: weight 5-6 → 5.5
# null/disabled: 默认 5.0
TIER_SCORES = {
    1: 9.5,    # 核心骨架 - 最高权重
    2: 7.5,    # 区域支柱 - 中等权重
    3: 5.5,    # 专业补充 - 基础权重
}

# 默认分数（未知信源）
DEFAULT_SCORE = 5.0

# 缓存已加载的配置
_source_cache = {}


def _load_sources_config():
    """加载 sources.yaml 配置"""
    if _source_cache:
        return _source_cache

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'sources.yaml'
    )

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            _source_cache['config'] = config
            _source_cache['name_to_tier'] = _build_name_to_tier_map(config)
            logger.info(f"已加载 sources.yaml 配置，共 {_len(_source_cache['name_to_tier'])} 个信源")
    except Exception as e:
        logger.warning(f"加载 sources.yaml 失败: {e}")
        _source_cache['config'] = None
        _source_cache['name_to_tier'] = {}

    return _source_cache


def _build_name_to_tier_map(config):
    """从配置构建信源名称到 Tier 的映射"""
    name_to_tier = {}

    if not config:
        return name_to_tier

    # 国际信源
    international = config.get('international', {})
    for category_name, sources in international.items():
        if isinstance(sources, list):
            for source in sources:
                name = source.get('name')
                tier = source.get('tier')
                if name and tier is not None:
                    name_to_tier[name] = tier

    # 国内信源
    domestic = config.get('domestic', {})
    for category_name, sources in domestic.items():
        if isinstance(sources, list):
            for source in sources:
                name = source.get('name')
                tier = source.get('tier')
                if name and tier is not None:
                    name_to_tier[name] = tier

    return name_to_tier


def _len(d):
    """安全获取字典长度"""
    return len(d) if d else 0


def get_source_score(source_name: str) -> float:
    """
    根据信源名称获取权威性评分

    评分逻辑：
    1. 从 sources.yaml 查找信源的 Tier 层级
    2. 根据 Tier 层级返回对应分数
    3. 未找到的信源返回默认分数

    Tier 分数映射（0-10范围）：
    - Tier 1 (核心骨架): 9.5 - 路透社、美联社、法新社等
    - Tier 2 (区域支柱): 7.5 - BBC、纽约时报、金融时报等
    - Tier 3 (专业补充): 5.5 - TechCrunch、36氪等
    - 默认: 5.0
    """
    if not source_name:
        return DEFAULT_SCORE

    cache = _load_sources_config()
    name_to_tier = cache.get('name_to_tier', {})

    # 精确匹配
    tier = name_to_tier.get(source_name)

    # 如果没找到，尝试模糊匹配（检查是否包含信源名称）
    if tier is None:
        for name, t in name_to_tier.items():
            if name in source_name or source_name in name:
                tier = t
                logger.debug(f"模糊匹配: {source_name} -> {name} (tier={tier})")
                break

    # 根据 Tier 返回分数
    if tier is not None:
        return TIER_SCORES.get(tier, DEFAULT_SCORE)

    return DEFAULT_SCORE


def get_source_tier(source_name: str) -> int | None:
    """
    获取信源的 Tier 层级

    Returns:
        1, 2, 3 或 None（未知信源）
    """
    if not source_name:
        return None

    cache = _load_sources_config()
    name_to_tier = cache.get('name_to_tier', {})

    tier = name_to_tier.get(source_name)

    if tier is None:
        for name, t in name_to_tier.items():
            if name in source_name or source_name in name:
                return t

    return tier


def reload_config():
    """重新加载配置（用于测试或配置更新）"""
    global _source_cache
    _source_cache = {}
    return _load_sources_config()