#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并处理器 - 单次 LLM 调用完成翻译 + 摘要 + 5W1H + 评分 + 事实判断

设计原则：低成本（一次调用 = 五步输出），替代原有分散的多次 AI 调用。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

_COMBINED_SYSTEM = """你是一个专业的新闻分析专家。请对以下新闻进行一次性综合分析，输出 JSON 格式结果。

JSON 结构要求（严格遵守）：
{
  "is_factual": true或false,
  "translation": "如果原文是外语，输出中文翻译；若已是中文，输出原标题",
  "translated_content": "全文中文翻译（若已是中文则原文）",
  "summary": "50-150字以内核心摘要",
  "original_summary": "来源网站的原始摘要（若无则为空字符串）",
  "analysis": {
    "who": "涉及的主体（人/机构/国家），不清楚则填'暂无信息'",
    "what": "发生了什么事，不清楚则填'暂无信息'",
    "when": "时间信息，不清楚则填'暂无信息'",
    "where": "地点信息，不清楚则填'暂无信息'",
    "why": "原因/背景，不清楚则填'暂无信息'",
    "how": "方式/过程/结果，不清楚则填'暂无信息'"
  },
  "domain": "领域（政治/经济/科技/军事/社会/文化/体育/娱乐之一）",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "scoring": {
    "influence_score": 7,
    "value_score": 6
  },
  "reason": "判断理由，简短说明为什么纳入或剔除"
}

## 事实新闻判断标准（重要）

### 事实新闻（is_factual=true）的特征：
1. 包含至少3个明确的5W1H要素
2. 内容是客观陈述，无主观评价、无立场输出
3. 可核查、可验证（有具体数据、场景、引用）
4. 不是广告、活动推广、纯数据汇总
5. 无明显错误、虚假信息

### 非事实内容（is_factual=false）的类型：
1. 纯评论/专栏/社论：仅表达观点，无新事实
2. 猜测/预判/推演：无明确事实依据的预测
3. 纯数据汇总：无事件性，仅罗列数据
4. 广告/推广：商业推广内容
5. 访谈/专访：以对话为主，无独立事实陈述

## 评分标准（0-10，数值越大表示该维度评分越高）

- influence_score： 事件影响范围。全球影响=9-10，全国影响=6-8，地区影响=3-5，无实质影响=1以下
- value_score: 决策参考价值。重大投资/政策/科技决策相关=8-10，行业参考=5-7，娱乐/生活=1-3

请只输出 JSON，不要有任何其他内容。"""


class CombinedProcessor:
    """合并 LLM 处理器：翻译 + 摘要 + 5W1H + 评分 + 事实判断 一次完成"""

    # 熔断器阈值：连续致命错误达到此数后跳过剩余批次
    CIRCUIT_BREAKER_THRESHOLD = 3

    def __init__(self):
        self._provider = None
        self._backup_provider = None  # BACKUP 提供者，FILTER 失败时兜底（合并自 ai_filter_agent.py）
        self._initialized = False
        self._log_dir = Path(__file__).parent.parent / "data" / "processor_logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._logs: List[Dict] = []
        self._stats = {
            'total_processed': 0,
            'factual_count': 0,
            'non_factual_count': 0,
            'ai_calls': 0,
            'parse_failures': 0
        }
        # 熔断器状态
        self._consecutive_fatal_failures = 0
        self._circuit_open = False

    def _init(self):
        """延迟初始化，避免循环导入"""
        if self._initialized:
            return
        try:
            from core.processor.ai_processor import AIProcessor
            ai = AIProcessor()
            self._provider = ai.get_provider("FILTER")
            self._backup_provider = ai.get_provider("BACKUP")
        except Exception as e:
            logger.warning(f"CombinedProcessor AI provider 初始化失败: {e}")
        self._initialized = True

    def _log_action(self, news: Dict[str, Any], result: Dict[str, Any], accuracy: float):
        """记录处理日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "title": news.get("title", "")[:100],
            "source": news.get("source_name", ""),
            "is_factual": result.get("is_factual"),
            "domain": result.get("domain"),
            "accuracy": accuracy,
            "influence_score": result.get("scoring", {}).get("influence_score"),
            "value_score": result.get("scoring", {}).get("value_score"),
            "reason": result.get("reason", "")[:200]
        }
        self._logs.append(log_entry)
        
        self._stats['total_processed'] += 1
        if result.get("is_factual"):
            self._stats['factual_count'] += 1
        else:
            self._stats['non_factual_count'] += 1

    def save_summary_log(self):
        """保存汇总日志"""
        if not self._logs:
            return
        
        log_file = self._log_dir / f"combined_processor_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024:
                backup_file = self._log_dir / f"combined_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                log_file.rename(backup_file)
                logger.info(f"日志文件轮转: {backup_file.name}")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                for entry in self._logs:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
            logger.info(f"CombinedProcessor 日志已保存: {log_file} ({len(self._logs)} 条)")
        except (IOError, OSError) as e:
            logger.error(f"保存日志失败: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self._stats.copy()

    def is_circuit_open(self) -> bool:
        """检查熔断器是否已断开（LLM 服务不可用）"""
        return self._circuit_open

    @staticmethod
    def _is_fatal_error(error: Exception) -> bool:
        """判断是否为致命错误（认证/账户类，重试无意义）"""
        msg = str(error).lower()
        fatal_keywords = [
            'account_overdue', 'accountoverdue', 'overdue',
            '401', '403', 'authentication', 'unauthorized',
            'invalid api key', 'invalid_api_key',
            'account deactivated', 'insufficient_quota',
            'billing', 'payment_required',
        ]
        return any(kw in msg for kw in fatal_keywords)

    def _on_llm_failure(self, error: Exception):
        """LLM 调用失败后的熔断器逻辑"""
        if self._is_fatal_error(error):
            self._consecutive_fatal_failures += 1
            logger.error(
                f"LLM 致命错误 ({self._consecutive_fatal_failures}/{self.CIRCUIT_BREAKER_THRESHOLD}): {error}"
            )
            if self._consecutive_fatal_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                self._circuit_open = True
                logger.critical(
                    f"熔断器已断开: 连续 {self._consecutive_fatal_failures} 次致命错误，跳过后续批次"
                )
        else:
            # 非致命错误（网络超时/限流等）不触发熔断，仅重置计数
            logger.warning(f"LLM 非致命错误（不触发熔断）: {error}")

    def _on_llm_success(self):
        """LLM 调用成功后重置熔断器"""
        if self._consecutive_fatal_failures > 0:
            logger.info(f"熔断器重置: 之前连续 {self._consecutive_fatal_failures} 次失败，现已恢复")
        self._consecutive_fatal_failures = 0
        self._circuit_open = False

    def process_news(self, news: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """
        处理单条新闻

        Returns:
            (result_dict, accuracy_score)
        """
        self._init()

        prompt = self._build_combined_prompt(news)

        if self._provider:
            try:
                raw = self._provider.chat(
                    [
                        {"role": "system", "content": _COMBINED_SYSTEM},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1500
                )
                result = self._parse_response(raw, news)
                self._on_llm_success()
            except Exception as e:
                # TokenLimitExceeded 时跳过熔断器计数，直接走 BACKUP
                if type(e).__name__ == "TokenLimitExceeded":
                    logger.warning(f"主 provider token 限额触发: {e}")
                else:
                    logger.error(f"CombinedProcessor LLM 调用失败: {e}")
                    self._on_llm_failure(e)
                result = self._try_backup(prompt, news)
        else:
            logger.warning("CombinedProcessor: 无可用 AI provider，使用默认值")
            result = self._default_result(news)

        accuracy = self._evaluate_accuracy(result)
        return result, accuracy

    def _build_combined_prompt(self, news: Dict[str, Any]) -> str:
        title = news.get("title", "")
        content = (news.get("content") or news.get("description") or "")[:1000]
        source = news.get("source_name", "")
        original_summary = (news.get("description") or "")[:300]

        return (
            f"信源：{source}\n"
            f"标题：{title}\n"
            f"原始摘要：{original_summary}\n"
            f"正文（节选）：{content}\n"
        )

    def _parse_response(self, raw: str, news: Dict[str, Any] = None) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON"""
        from core.utils.text_utils import parse_json_str
        result = parse_json_str(raw)
        if not result:
            logger.warning("CombinedProcessor: JSON 解析失败，使用默认结果")
            if news:
                return self._default_result(news)
            return {}
        return result

    def _try_backup(self, prompt: str, news: Dict[str, Any]) -> Dict[str, Any]:
        """尝试使用 BACKUP 提供者（合并自 ai_filter_agent.py 的重试模式）"""
        if not self._backup_provider:
            return self._default_result(news)
        try:
            logger.info("尝试 BACKUP 提供者...")
            raw = self._backup_provider.chat(
                [
                    {"role": "system", "content": _COMBINED_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            result = self._parse_response(raw, news)
            self._on_llm_success()
            logger.info("BACKUP 提供者调用成功")
            return result
        except Exception as e:
            logger.error(f"BACKUP 提供者也失败: {e}")
            return self._default_result(news)

    def _default_result(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """当 AI 不可用时的默认填充"""
        from core.utils.defaults import DefaultValues
        title = news.get("title", "")
        return {
            "translation": title,
            "translated_content": news.get("content", ""),
            "summary": news.get("description", title)[:100],
            "original_summary": news.get("description", ""),
            "analysis": {
                "who": "暂无信息",
                "what": "暂无信息",
                "when": news.get("pub_date", "暂无信息"),
                "where": "暂无信息",
                "why": "暂无信息",
                "how": "暂无信息"
            },
            "domain": "其他",
            "keywords": [],
            "scoring": {
                "influence_score": DefaultValues.SCORE_DEFAULT,
                "value_score": DefaultValues.SCORE_DEFAULT
            }
        }

    def _evaluate_accuracy(self, result: Dict[str, Any]) -> float:
        """评估结果完整性，返回 0-1 精度分"""
        required_fields = ["translation", "summary", "analysis", "scoring"]
        completeness = sum(
            1 for f in required_fields if result.get(f)
        ) / len(required_fields)

        consistency = 0.8 if result.get("translation") else 1.0

        if result.get("analysis"):
            w5h1_fields = ["who", "what", "when", "where", "why", "how"]
            w5h1 = sum(
                1 for f in w5h1_fields
                if result["analysis"].get(f) and result["analysis"][f] != "暂无信息"
            ) / len(w5h1_fields)
        else:
            w5h1 = 0.0

        return completeness * 0.4 + consistency * 0.3 + w5h1 * 0.3

    def process_batch(self, news_list: list) -> list:
        """
        批量处理新闻（单次 LLM 调用处理多条新闻）

        Args:
            news_list: 新闻列表

        Returns:
            [(news, result, accuracy), ...] 列表
        """
        if not news_list:
            return []

        self._init()

        # 熔断器检查：如果 LLM 服务不可用，直接跳过
        if self._circuit_open:
            logger.warning(f"熔断器已断开，跳过 {len(news_list)} 条新闻")
            return [(news, None, 0.0) for news in news_list]

        if not self._provider:
            logger.warning("CombinedProcessor: 无可用 AI provider，使用默认值")
            return [(news, self._default_result(news), 0.0) for news in news_list]

        batch_prompt = self._build_batch_prompt(news_list)

        try:
            raw = self._provider.chat(
                [
                    {"role": "system", "content": _COMBINED_SYSTEM + "\n\n注意：你需要处理多条新闻，请返回 JSON 数组，每条新闻对应一个结果对象。"},
                    {"role": "user", "content": batch_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            results = self._parse_batch_response(raw, len(news_list))
            self._on_llm_success()
        except Exception as e:
            # TokenLimitExceeded 时跳过熔断器计数
            if type(e).__name__ == "TokenLimitExceeded":
                logger.warning(f"批量处理主 provider token 限额触发: {e}")
            else:
                logger.error(f"CombinedProcessor 批量 LLM 调用失败: {e}")
                self._on_llm_failure(e)
            # 尝试 BACKUP 提供者
            if self._backup_provider:
                try:
                    logger.info("批量处理尝试 BACKUP 提供者...")
                    raw = self._backup_provider.chat(
                        [
                            {"role": "system", "content": _COMBINED_SYSTEM + "\n\n注意：你需要处理多条新闻，请返回 JSON 数组，每条新闻对应一个结果对象。"},
                            {"role": "user", "content": batch_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=4000
                    )
                    results = self._parse_batch_response(raw, len(news_list))
                    self._on_llm_success()
                    logger.info("BACKUP 批量处理成功")
                except Exception as e2:
                    logger.error(f"BACKUP 批量处理也失败: {e2}")
                    results = [None] * len(news_list)
            else:
                results = [None] * len(news_list)

        output = []
        for i, news in enumerate(news_list):
            result = results[i] if i < len(results) and results[i] else None
            if not result:
                output.append((news, None, 0.0))
            else:
                accuracy = self._evaluate_accuracy(result)
                output.append((news, result, accuracy))

        return output
    
    def _build_batch_prompt(self, news_list: list) -> str:
        """构建批量处理 prompt"""
        parts = []
        for i, news in enumerate(news_list, 1):
            title = news.get("title", "")
            content = (news.get("content") or news.get("description") or "")[:500]
            source = news.get("source_name", "")
            parts.append(f"【新闻 {i}】\n信源：{source}\n标题：{title}\n正文：{content}\n")
        
        return (
            f"请分析以下 {len(news_list)} 条新闻，返回 JSON 数组：\n\n"
            + "\n---\n".join(parts)
            + "\n\n请返回 JSON 数组格式，每条新闻一个对象。"
        )
    
    def _parse_batch_response(self, raw: str, expected_count: int) -> list:
        """解析批量响应"""
        from core.utils.text_utils import parse_json_str
        result = parse_json_str(raw)
        
        if isinstance(result, list):
            return result
        
        if isinstance(result, dict):
            return [result]
        
        logger.warning(f"CombinedProcessor: 批量响应解析失败，期望 {expected_count} 条")
        return [None] * expected_count
