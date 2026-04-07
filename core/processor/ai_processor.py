#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI处理模块 - 多厂商统一处理
配置格式：AI_<用途>_<信息类型> = <值>
用途：ANALYSIS(深度分析) / FILTER(快速筛选) / BACKUP(备用)
"""

import os
import json
import logging
import time
import yaml
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

from core.config.loader import get_env
from core.utils.text_utils import parse_json_str


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器 - 指数退避重试

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避系数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # TokenLimitExceeded 直接穿透，不重试
                    if type(e).__name__ == "TokenLimitExceeded":
                        raise
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"{func.__name__} 失败，{current_delay}秒后重试... ({attempt + 1}/{max_retries})")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"{func.__name__} 重试{max_retries}次后仍失败")

            raise last_exception
        return wrapper
    return decorator


@dataclass
class ValueJudgmentResult:
    """价值判断结果"""
    has_value: bool
    added_value: str
    similarity_score: float
    should_keep: bool


@dataclass
class ReportResult:
    """报告生成结果"""
    title: str
    core_tags: List[str]
    conclusion: str
    markdown_content: str


_PROVIDERS_CONFIG_CACHE: Optional[Dict[str, Any]] = None
_ENV_LOADED = False


def _ensure_env_loaded():
    """确保.env文件已加载"""
    global _ENV_LOADED
    if not _ENV_LOADED:
        from dotenv import load_dotenv
        load_dotenv()
        _ENV_LOADED = True


def load_providers_config() -> Dict[str, Any]:
    """加载厂商配置文件（带缓存）"""
    global _PROVIDERS_CONFIG_CACHE
    
    if _PROVIDERS_CONFIG_CACHE is not None:
        return _PROVIDERS_CONFIG_CACHE
    
    config_path = Path(__file__).parent.parent / "config" / "ai_providers.yaml"
    
    if not config_path.exists():
        _PROVIDERS_CONFIG_CACHE = {"providers": {}}
        return _PROVIDERS_CONFIG_CACHE
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            _PROVIDERS_CONFIG_CACHE = config
            return config
    except Exception as e:
        logging.getLogger("AIProcessor").warning(f"加载ai_providers.yaml失败: {e}")
        _PROVIDERS_CONFIG_CACHE = {"providers": {}}
        return _PROVIDERS_CONFIG_CACHE


def get_ai_config(purpose: str) -> Dict[str, str]:
    """
    获取指定用途的AI配置
    
    Args:
        purpose: "ANALYSIS" / "FILTER" / "BACKUP"
    
    Returns:
        配置字典 {provider, model, api_key, base_url, sdk, extra_headers}
    """
    _ensure_env_loaded()
    
    purpose = purpose.upper()
    
    provider = os.getenv(f"AI_{purpose}_PROVIDER", "").strip()
    model = os.getenv(f"AI_{purpose}_MODEL", "").strip()
    api_key = os.getenv(f"AI_{purpose}_KEY", "").strip()
    base_url = os.getenv(f"AI_{purpose}_BASE_URL", "").strip()
    
    if not provider:
        return {}
    
    providers_config = load_providers_config()
    provider_info = providers_config.get("providers", {}).get(provider, {})
    
    if not base_url:
        base_url = provider_info.get("base_url", "")
    
    sdk = provider_info.get("sdk", "openai")
    extra_headers = provider_info.get("extra_headers", {})
    
    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "sdk": sdk,
        "extra_headers": extra_headers
    }


class BaseProvider:
    """AI提供商基类"""
    
    def __init__(self, config: Dict[str, str]):
        self.provider = config.get("provider", "unknown")
        self.model = config.get("model", "")
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "")
        self.sdk = config.get("sdk", "openai")
        self.extra_headers = config.get("extra_headers", {})
        self._client = None
        self.logger = logging.getLogger(f"AI.{self.provider}")
    
    def _get_client(self):
        """获取客户端"""
        if self._client is None:
            if self.sdk == "volcengine":
                try:
                    from volcenginesdkarkruntime import Ark
                    self._client = Ark(
                        base_url=self.base_url,
                        api_key=self.api_key
                    )
                except ImportError:
                    self.logger.warning("volcenginesdkarkruntime SDK未安装，请运行: pip install volcengine-python-sdk")
                    return None
            else:
                try:
                    from openai import OpenAI
                    client_kwargs = {
                        "api_key": self.api_key,
                        "base_url": self.base_url,
                        "timeout": 120.0,
                        "max_retries": 2
                    }
                    if self.extra_headers:
                        client_kwargs["default_headers"] = self.extra_headers
                    self._client = OpenAI(**client_kwargs)
                except ImportError:
                    self.logger.warning("OpenAI SDK未安装，请运行: pip install openai")
                    return None
        return self._client
    
    def is_available(self) -> bool:
        """检查API是否可用"""
        return bool(self.api_key) and self._get_client() is not None
    
    @retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求（带重试 + token 计数）"""
        client = self._get_client()
        if not client:
            raise RuntimeError(f"{self.provider}客户端未初始化")

        # 前置: 检查 token 阈值
        from core.processor.token_counter import TokenCounter, TokenLimitExceeded
        counter = TokenCounter.get_instance()
        counter.check_and_raise(self.model)

        try:
            response = client.chat.completions.create(
                model=kwargs.get('model', self.model),
                messages=messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 2000)
            )

            # 后置: 记录 token 用量（副作用，不改变返回值）
            if hasattr(response, 'usage') and response.usage:
                counter.record_usage(
                    model=self.model,
                    prompt_tokens=getattr(response.usage, 'prompt_tokens', 0) or 0,
                    completion_tokens=getattr(response.usage, 'completion_tokens', 0) or 0,
                )

            return response.choices[0].message.content
        except TokenLimitExceeded:
            raise
        except Exception as e:
            self.logger.error(f"{self.provider}请求失败: {e}")
            raise


class AIProcessor:
    """AI处理器 - 支持多厂商、多用途配置"""
    
    PURPOSES = ["ANALYSIS", "FILTER", "BACKUP"]
    
    def __init__(self):
        self.logger = logging.getLogger("AIProcessor")
        self._providers: Dict[str, BaseProvider] = {}
        self.storage = None
        self._init_providers()
    
    def _init_providers(self):
        """初始化所有用途的Provider"""
        for purpose in self.PURPOSES:
            config = get_ai_config(purpose)
            if config and config.get("provider"):
                self._providers[purpose] = BaseProvider(config)
                self.logger.info(f"初始化 {purpose} Provider: {config.get('provider')}/{config.get('model')}")
    
    def set_storage(self, storage):
        """设置存储管理器"""
        self.storage = storage
    
    def get_provider(self, purpose: str = "FILTER") -> Optional[BaseProvider]:
        """
        获取指定用途的AI提供商（阈值感知：跳过已超 token 限额的 provider）

        Args:
            purpose: 用途，可选值: "ANALYSIS"(深度分析) / "FILTER"(快速筛选) / "BACKUP"(备用)

        Returns:
            对应的提供商实例，如果不可用则尝试备用
        """
        purpose = purpose.upper()

        try:
            from core.processor.token_counter import TokenCounter
            counter = TokenCounter.get_instance()
        except Exception:
            counter = None

        # 优先: 请求的 provider 可用且未超阈值
        if purpose in self._providers and self._providers[purpose].is_available():
            provider = self._providers[purpose]
            if counter is None or not counter.is_over_threshold(provider.model):
                return provider
            self.logger.warning(
                f"{purpose} provider ({provider.model}) 今日 token 已超阈值，尝试切换"
            )

        # 备选: BACKUP provider 可用且未超阈值
        if purpose != "BACKUP" and "BACKUP" in self._providers:
            backup = self._providers["BACKUP"]
            if backup.is_available() and (counter is None or not counter.is_over_threshold(backup.model)):
                self.logger.warning(f"使用 BACKUP provider ({backup.model}) 替代 {purpose}")
                return backup

        # 兜底: 任何可用且未超阈值的 provider
        for p in self.PURPOSES:
            if p in self._providers:
                provider = self._providers[p]
                if provider.is_available() and (counter is None or not counter.is_over_threshold(provider.model)):
                    self.logger.warning(f"使用 {p} provider ({provider.model}) 作为兜底")
                    return provider

        # 最终兜底: 即使超阈值也返回请求的 provider
        if purpose in self._providers and self._providers[purpose].is_available():
            self.logger.error(f"所有 provider 今日 token 已超阈值，强制使用 {purpose}")
            return self._providers[purpose]

        self.logger.error("没有可用的AI Provider")
        return None
    
    def judge_value(
        self,
        official_content: str,
        third_party_content: str,
        official_source: str = "官媒",
        third_party_source: str = "第三方",
        purpose: str = "FILTER"
    ) -> ValueJudgmentResult:
        """
        判断第三方内容是否有新增价值
        
        Args:
            official_content: 官媒核心内容
            third_party_content: 第三方内容
            official_source: 官媒来源名称
            third_party_source: 第三方来源名称
            purpose: 用途，默认使用快速筛选
        
        Returns:
            ValueJudgmentResult: 价值判断结果
        """
        provider = self.get_provider(purpose)
        if not provider:
            self.logger.warning("AI提供商不可用，默认保留内容")
            return ValueJudgmentResult(
                has_value=True,
                added_value="无法判断，默认保留",
                similarity_score=0.5,
                should_keep=True
            )
        
        prompt = f"""你是一个新闻价值分析专家。请分析以下第三方内容相对于官媒内容是否有新增价值。

【官媒内容】（来源：{official_source}）
{official_content[:2000]}

【第三方内容】（来源：{third_party_source}）
{third_party_content[:2000]}

请判断第三方内容是否提供了官媒没有的新增价值，包括：
1. 新的事实、数据或细节
2. 不同的视角或观点
3. 更深入的背景分析
4. 重要的补充信息

请以JSON格式返回分析结果：
{{
    "has_value": true或false,
    "added_value": "具体描述新增价值，如果没有则填'无'",
    "similarity_score": 0.0到1.0之间的数字,
    "should_keep": true或false
}}

注意：
- 如果第三方内容只是重复官媒信息，无新增价值，should_keep应为false
- 如果有新增价值，should_keep应为true
- similarity_score表示内容相似度，0表示完全不同，1表示完全相同"""

        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            result = self._parse_json_response(response)
            
            return ValueJudgmentResult(
                has_value=result.get('has_value', False),
                added_value=result.get('added_value', ''),
                similarity_score=result.get('similarity_score', 1.0),
                should_keep=result.get('should_keep', False)
            )
        except Exception as e:
            self.logger.error(f"价值判断失败: {e}")
            return ValueJudgmentResult(
                has_value=False,
                added_value=f"判断失败: {str(e)}",
                similarity_score=1.0,
                should_keep=False
            )
    
    def extract_tags(self, content: str, max_tags: int = 5, purpose: str = "FILTER") -> List[str]:
        """
        提取内容标签
        
        Args:
            content: 新闻内容
            max_tags: 最大标签数量
            purpose: 用途
        
        Returns:
            标签列表
        """
        provider = self.get_provider(purpose)
        if not provider:
            return []
        
        prompt = f"""请从以下新闻内容中提取{max_tags}个核心关键词作为标签。

新闻内容：
{content[:1000]}

请直接返回JSON数组格式的标签列表，例如：
["标签1", "标签2", "标签3"]"""

        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            result = self._parse_json_response(response)
            if isinstance(result, list):
                return result[:max_tags]
            return []
        except Exception as e:
            self.logger.error(f"标签提取失败: {e}")
            return []
    
    def generate_summary(self, content: str, purpose: str = "FILTER") -> str:
        """
        生成新闻摘要
        
        Args:
            content: 新闻内容
            purpose: 用途
        
        Returns:
            摘要内容
        """
        provider = self.get_provider(purpose)
        if not provider:
            return content[:300] if content else ""
        
        prompt = f"""请为以下新闻生成摘要，要求：

1. **一句话概要**（必选）：用一句简洁清晰的话概括新闻核心，讲清何人、何事、何时、何地，让读者快速理解事件全貌。
2. **详细摘要**（可选）：若内容复杂，可再补充100-200字，包含原因、过程、影响等。

新闻内容：
{content[:2000]}

请直接返回摘要内容，第一句必须是一句话概要，不需要任何引言或开场白。"""

        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.7)
            return response
        except Exception as e:
            self.logger.error(f"摘要生成失败: {e}")
            return content[:300] if content else ""
    
    def translate_content(self, content: str, target_language: str = "中文", purpose: str = "FILTER") -> str:
        """
        翻译新闻内容
        
        Args:
            content: 新闻内容
            target_language: 目标语言
            purpose: 用途
        
        Returns:
            翻译后的内容
        """
        provider = self.get_provider(purpose)
        if not provider:
            return content
        
        prompt = f"""请将以下新闻内容翻译成{target_language}，保持原文的事实准确性，不要添加或遗漏关键信息。

新闻内容：
{content[:2000]}

请直接返回翻译后的内容，不需要任何引言或开场白。"""

        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            return response
        except Exception as e:
            self.logger.error(f"翻译失败: {e}")
            return content
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应（委托给 utils.text_utils.parse_json_str）"""
        return parse_json_str(response)
    
    def query_related_history(self, news: Dict, history_news: List[Dict], purpose: str = "ANALYSIS") -> List[Dict]:
        """
        历史关联查询：查询近90天内与当前新闻相关的历史新闻
        
        Args:
            news: 当前新闻
            history_news: 历史新闻列表
            purpose: 用途
        
        Returns:
            相关历史新闻列表
        """
        provider = self.get_provider(purpose)
        if not provider or not history_news:
            return []
        
        current_domain = news.get('domain', '其他')
        
        same_domain_news = [n for n in history_news if n.get('domain') == current_domain]
        other_domain_news = [n for n in history_news if n.get('domain') != current_domain]
        
        selected_history = same_domain_news[:15] + other_domain_news[:5]
        if len(selected_history) < 20:
            selected_history = history_news[:20]
        
        current_text = f"标题: {news.get('translated_title', news.get('title', ''))}\n"
        current_text += f"摘要: {news.get('short_summary', news.get('content', '')[:300])}\n"
        current_text += f"领域: {current_domain}\n"
        
        history_text = ""
        for i, h_news in enumerate(selected_history):
            history_text += f"[ID: {h_news.get('news_id', i)}] 标题: {h_news.get('translated_title', h_news.get('title', ''))}\n"
            history_text += f"日期: {h_news.get('publish_date', '未知')}\n"
            history_text += f"摘要: {h_news.get('short_summary', h_news.get('content', '')[:150])}\n\n"
        
        prompt = f"""你是一个专业的新闻关联分析专家。请分析当前新闻与历史新闻的关联关系。

## 当前新闻

{current_text}

## 历史新闻列表

{history_text}

## 请判断哪些历史新闻与当前新闻有明显关联

关联类型包括：
1. 政策延续：当前新闻是历史政策的延续或调整
2. 事件后续：当前新闻是历史事件的后续发展
3. 对比数据：当前新闻与历史新闻的数据形成对比
4. 因果关系：历史事件是当前事件的原因或背景
5. 相关主题：同一主题的不同方面

## 请以JSON格式输出关联结果

```json
[
    {{
        "news_id": "历史新闻ID",
        "relation_type": "关联类型",
        "relation_desc": "关联描述（一句话说明如何关联）"
    }},
    ...
]
```

请只输出有明显关联的历史新闻，最多返回5条。如果没有明显关联，返回空数组。"""
        
        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            result = self._parse_json_response(response)
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            self.logger.error(f"历史关联查询失败: {e}")
            return []
    
    def generate_event_insight(self, news: Dict, related_history: List[Dict], purpose: str = "ANALYSIS") -> str:
        """
        生成单事件深度洞察
        
        Args:
            news: 当前新闻
            related_history: 相关历史新闻
            purpose: 用途
        
        Returns:
            深度洞察文本（约900字）
        """
        provider = self.get_provider(purpose)
        if not provider:
            return "AI服务暂不可用，无法生成深度洞察。"
        
        current_text = f"标题: {news.get('translated_title', news.get('title', ''))}\n"
        current_text += f"来源: {news.get('source_name', '未知')}\n"
        current_text += f"领域: {news.get('domain', '其他')}\n"
        current_text += f"摘要: {news.get('short_summary', news.get('content', '')[:500])}\n"
        
        history_text = ""
        if related_history:
            history_text = "\n## 相关历史新闻\n\n"
            for h in related_history:
                history_text += f"- {h.get('publish_date', '')} {h.get('title', '')}（{h.get('relation_type', '')}）\n"
                history_text += f"  关联说明：{h.get('relation_desc', '')}\n"
        
        prompt = f"""你是一个专业的新闻分析师。请根据以下新闻信息，生成一篇深度洞察分析文章。

## 当前新闻

{current_text}

{history_text}

## 请生成深度洞察分析文章（约900字）

要求：
1. 以连贯的叙述方式撰写，不要使用分点形式（如"一、二、三"或"1. 2. 3."）
2. 文章应有明确的开头、主体和结尾，形成完整的文章结构
3. 内容应涵盖以下方面（但不要显式标注）：
   - 事件核心要点拆解
   - 当前直接影响
   - 发展趋势预判
   - 潜在风险与机遇
4. 语言专业、客观、有洞察力，避免空泛的描述
5. 结合历史关联信息，增强分析的深度和连贯性"""
        
        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=2000)
            return response
        except Exception as e:
            self.logger.error(f"深度洞察生成失败: {e}")
            return "深度洞察生成失败。"
    
    def generate_domain_overview(self, domain: str, events: List[Dict], purpose: str = "ANALYSIS") -> str:
        """
        生成领域整体分析
        
        Args:
            domain: 领域名称
            events: 事件列表
            purpose: 用途
        
        Returns:
            领域整体分析文本（约1000字）
        """
        provider = self.get_provider(purpose)
        if not provider:
            return "AI服务暂不可用，无法生成领域整体分析。"
        
        events_text = ""
        for i, event in enumerate(events, 1):
            news = event.get('representative_news', {})
            events_text += f"### 事件{i}: {news.get('translated_title', news.get('title', '未知'))}\n"
            events_text += f"评分: {news.get('final_score', 0)}分\n"
            events_text += f"摘要: {news.get('short_summary', '无摘要')}\n\n"
        
        prompt = f"""你是一个专业的{domain}领域分析师。请根据以下当日重要事件，生成一篇领域整体分析文章。

## 当日{domain}领域重要事件

{events_text}

## 请生成领域整体分析文章（约1000字）

要求：
1. 以连贯的叙述方式撰写，不要使用分点形式（如"一、二、三"或"1. 2. 3."）
2. 文章应有明确的开头、主体和结尾，形成完整的文章结构
3. 内容应涵盖以下方面（但不要显式标注）：
   - 当日事件内在关联
   - 领域整体趋势
   - 未来预判
4. 语言专业、客观、有前瞻性
5. 结合各事件之间的内在联系，形成有深度的整体分析"""
        
        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=2500)
            return response
        except Exception as e:
            self.logger.error(f"领域整体分析生成失败: {e}")
            return "领域整体分析生成失败。"
    
    def cluster_events(self, news_list: List[Dict], purpose: str = "ANALYSIS") -> List[Dict]:
        """
        对新闻列表进行事件聚类（基于向量相似度）

        Args:
            news_list: 新闻列表
            purpose: 用途

        Returns:
            聚类结果列表，每个聚类包含 event_name, news_ids, representative_id, reason
        """
        if not news_list:
            return []

        news_with_embedding = [n for n in news_list if n.get('embedding')]
        news_without_embedding = [n for n in news_list if not n.get('embedding')]

        if not news_with_embedding:
            self.logger.info("没有新闻包含embedding，使用简单聚类")
            return self._simple_cluster(news_list)

        clusters = self._vector_clustering(news_with_embedding)

        for n in news_without_embedding:
            clusters.append(self._simple_cluster([n])[0])

        provider = self.get_provider(purpose)
        if provider:
            clusters = self._ai_naming(clusters, provider)

        clusters.sort(key=lambda x: x.get('avg_score', 0), reverse=True)

        self.logger.info(f"事件聚类完成: {len(clusters)}个聚类")
        return clusters[:10]

    def _vector_clustering(self, news_list: List[Dict], similarity_threshold: float = 0.85) -> List[Dict]:
        """基于向量相似度的聚类"""
        vectors = []
        valid_news = []
        for news in news_list:
            emb = news.get('embedding', '')
            if isinstance(emb, bytes):
                try:
                    vec = np.frombuffer(emb, dtype=np.float32)
                except:
                    continue
            elif isinstance(emb, str):
                try:
                    vec = np.array(json.loads(emb), dtype=np.float32)
                except:
                    continue
            elif isinstance(emb, list):
                vec = np.array(emb, dtype=np.float32)
            else:
                continue
            vectors.append(vec)
            valid_news.append(news)

        if not vectors:
            return [self._simple_cluster(news_list)[0]]

        vectors = np.array(vectors)
        n = len(vectors)
        similarities = np.dot(vectors, vectors.T)

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        normalized = vectors / norms
        similarities = np.dot(normalized, normalized.T)

        clusters: List[List[int]] = []
        assigned = [False] * n

        for i in range(n):
            if assigned[i]:
                continue
            cluster = [i]
            assigned[i] = True
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                if similarities[i, j] >= similarity_threshold:
                    cluster.append(j)
                    assigned[j] = True
            clusters.append(cluster)

        results = []
        for cluster_indices in clusters:
            cluster_news = [valid_news[i] for i in cluster_indices]
            rep = max(cluster_news, key=lambda x: x.get('final_score', 0) or 0)
            avg_score = np.mean([n.get('final_score', 0) or 0 for n in cluster_news])

            results.append({
                'event_name': '',  # AI命名填充
                'news_ids': [n.get('news_id') for n in cluster_news],
                'representative_id': rep.get('news_id'),
                'news_list': cluster_news,
                'reason': f'向量相似度聚类，{len(cluster_news)}条新闻',
                'avg_score': avg_score
            })

        return results

    def _ai_naming(self, clusters: List[Dict], provider: BaseProvider) -> List[Dict]:
        """使用AI为所有聚类批量命名"""
        clusters_need_naming = [c for c in clusters if not c.get('event_name') and c.get('news_list')]
        if not clusters_need_naming:
            return clusters

        clusters_text = ""
        for i, cluster in enumerate(clusters_need_naming, 1):
            news_list = cluster.get('news_list', [])[:5]
            titles = [n.get('translated_title', '') or n.get('title', '') for n in news_list]
            cluster_text = "\n".join([f"  {j+1}. {t}" for j, t in enumerate(titles)])
            clusters_text += f"聚类{i}: (共{len(cluster.get('news_ids', []))}条新闻)\n{cluster_text}\n"

        prompt = f"""请为以下所有新闻聚类生成简洁的事件名称。

【聚类列表】
{clusters_text}

【要求】
1. 为每个聚类生成一个不超过15字的事件名称
2. 事件名称应概括该组新闻的核心主题
3. 按顺序返回，格式为"序号. 事件名称"，每行一个

请直接返回结果："""

        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=500)

            lines = response.strip().split('\n')
            name_map = {}
            for line in lines:
                line = line.strip()
                if '.' in line:
                    parts = line.split('.', 1)
                    try:
                        idx = int(parts[0])
                        name = parts[1].strip()[:15]
                        name_map[idx] = name
                    except:
                        continue

            for i, cluster in enumerate(clusters_need_naming, 1):
                if i in name_map:
                    cluster['event_name'] = name_map[i]
                else:
                    news_list = cluster.get('news_list', [])
                    rep_news = news_list[0] if news_list else {}
                    cluster['event_name'] = (rep_news.get('translated_title', '') or rep_news.get('title', ''))[:15]

        except Exception as e:
            self.logger.warning(f"AI批量命名失败: {e}")
            for cluster in clusters_need_naming:
                news_list = cluster.get('news_list', [])
                rep_news = news_list[0] if news_list else {}
                cluster['event_name'] = (rep_news.get('translated_title', '') or rep_news.get('title', ''))[:15]

        return clusters

    def _simple_cluster(self, news_list: List[Dict]) -> List[Dict]:
        """简单聚类：每条新闻作为独立事件"""
        return [
            {
                'event_name': n.get('translated_title', n.get('title', ''))[:30],
                'news_ids': [n.get('news_id')],
                'representative_id': n.get('news_id'),
                'reason': '独立事件（无embedding）',
                'avg_score': n.get('final_score', 0) or 0
            }
            for n in news_list[:10]
        ]


_ai_processor_instance = None

def get_ai_processor() -> AIProcessor:
    """获取AI处理器单例"""
    global _ai_processor_instance
    if _ai_processor_instance is None:
        _ai_processor_instance = AIProcessor()
    return _ai_processor_instance
