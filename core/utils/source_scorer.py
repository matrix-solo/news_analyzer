#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信源评分与综合评分计算

配置来源：core_config.yaml → scoring 段
所有评分参数均通过配置驱动，修改配置即可调整评分策略。
"""
import os
import yaml
import logging

logger = logging.getLogger(__name__)

# ── 从配置文件加载评分参数 ─────────────────────────────────────

def _load_scoring_config() -> dict:
    """从 core_config.yaml 加载评分配置，失败时返回内置默认值"""
    try:
        from core.config.manager import get_config_manager
        mgr = get_config_manager()
        cfg = mgr.get('scoring')
        if cfg and isinstance(cfg, dict):
            return cfg
    except Exception:
        pass

    # 内置默认值（与 core_config.yaml 保持一致）
    return {
        'weights': {'source': 0.25, 'influence': 0.25, 'value': 0.25, 'heat': 0.25},
        'tier_scores': {1: 9.5, 2: 7.5, 3: 5.5},
        'default_source_score': 5.0,
        'defaults': {'score': 5.0},
    }


def get_scoring_config() -> dict:
    """获取评分配置（带缓存）"""
    return _load_scoring_config()


# ── 信源 Tier 评分 ────────────────────────────────────────────

# 默认分数（未知信源）— 配置未加载时的后备值
DEFAULT_SCORE = 5.0

# 缓存已加载的配置
_source_cache = {}

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
    2. 从 core_config.yaml 读取 Tier → 分数映射
    3. 未找到的信源返回 default_source_score

    Tier 分数映射（默认值，可通过 core_config.yaml 调整）：
    - Tier 1 (核心骨架): 9.5 - 路透社、美联社、法新社等顶级通讯社
    - Tier 2 (区域支柱): 7.5 - BBC、纽约时报、金融时报等主流媒体
    - Tier 3 (专业补充): 5.5 - TechCrunch、36氪等垂直领域媒体
    - 默认: 5.0 - 未在 sources.yaml 中定义的信源
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

    # 从配置读取 Tier → 分数映射
    if tier is not None:
        scoring_cfg = get_scoring_config()
        tier_scores = scoring_cfg.get('tier_scores', {})
        return tier_scores.get(tier, scoring_cfg.get('default_source_score', DEFAULT_SCORE))

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


# ── 统一综合评分计算 ─────────────────────────────────────────

def calc_final_score(
    source_score: float,
    influence_score: float,
    value_score: float,
    heat_score: float,
) -> float:
    """
    计算综合评分（final_score）

    公式: (source×w1 + influence×w2 + value×w3 + heat×w4) / 10 × 100
    输入: 各项 0-10 范围
    输出: 0-100 范围，保留一位小数

    权重从 core_config.yaml → scoring.weights 读取
    默认: source=0.25, influence=0.25, value=0.25, heat=0.25
    """
    scoring_cfg = get_scoring_config()
    weights = scoring_cfg.get('weights', {})

    w_source = weights.get('source', 0.25)
    w_influence = weights.get('influence', 0.25)
    w_value = weights.get('value', 0.25)
    w_heat = weights.get('heat', 0.25)

    raw = (
        source_score / 10 * w_source
        + influence_score / 10 * w_influence
        + value_score / 10 * w_value
        + heat_score / 10 * w_heat
    ) * 100

    return round(raw, 1)