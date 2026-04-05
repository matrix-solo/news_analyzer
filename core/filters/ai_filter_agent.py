#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI判断器
使用AI进行5W1H检测和去重判断
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.processor.ai_processor import AIProcessor
from core.utils.text_utils import parse_json_str


@dataclass
class AIFactCheckResult:
    """AI事实判断结果"""
    is_factual: bool
    content_type: str
    w5h1_analysis: Dict[str, str]
    reason: str
    confidence: float = 0.0
    original_language: str = "中文"
    translated_title: str = ""
    translated_content: str = ""
    w5h1_score: int = 0
    short_summary: str = ""
    domain: str = ""
    source_score: float = 0.0
    influence_score: float = 0.0
    heat_score: float = 0.0
    value_score: float = 0.0
    final_score: float = 0.0
    score_reason: str = ""


@dataclass
class AIDedupResult:
    """AI去重判断结果"""
    is_duplicate: bool
    duplicate_groups: List[Dict]
    kept_ids: List[str]
    removed_ids: List[str]
    reason: str
    confidence: float = 0.0


@dataclass
class AIFilterLog:
    """AI判断日志"""
    timestamp: str
    action: str
    input_data: Dict
    result: Dict
    confidence: float

    def to_dict(self) -> Dict:
        return asdict(self)


# ── 单条新闻的完整判断 prompt ──────────────────────────────────────────────────

_FACT_CHECK_SYSTEM = """你是一个专业的新闻内容分析专家。请分析以下新闻内容，判断其是否为"事实新闻"，并完整提取5W1H要素，同时进行多维度评分。

## 语言处理规则（重要）

如果新闻内容是外文（非中文），请先将其翻译成中文，然后再进行分析判断。
- 翻译时要保持原文的事实准确性，不要添加或遗漏关键信息
- 所有输出结果必须使用中文

## 5W1H 提取要求（核心）

请从新闻中**准确、完整**提取以下要素，每个要素填写**具体内容**而非笼统描述：
- **when（何时）**：具体时间点或时间段，如"2026年3月7日"、"本周二"
- **where（何地）**：具体地点、国家、城市或区域
- **who（何人）**：涉及的主要人物、机构、组织名称
- **what（何事）**：事件的核心内容，用一句话概括
- **why（何因）**：事件发生的原因、背景或动机
- **how（如何）**：事件发生的方式、过程或措施

若某要素在文中未明确提及，填"无"；若有隐含信息可推断，可简要写出。

## 判断标准

### 事实新闻（应纳入）的特征：
1. 包含至少3个明确的5W1H要素
2. 内容是客观陈述，无主观评价、无立场输出
3. 可核查、可验证（有具体数据、场景、引用）
4. 不是广告、活动推广、纯数据汇总
5. 无明显错误、虚假信息

### 非事实内容（应剔除）的类型：
1. 纯评论/专栏/社论：仅表达观点，无新事实
2. 猜测/预判/推演：无明确事实依据的预测
3. 纯数据汇总：无事件性，仅罗列数据
4. 广告/推广：商业推广内容
5. 访谈/专访：以对话为主，无独立事实陈述

## 简短摘要要求

生成50-150字的简短摘要，客观中立，凸显事件影响，可从原文抽取关键句组合。

## 新闻领域分类

请判断新闻所属领域：政治、经济、科技、社会、文化、体育、娱乐、健康、环境、其他

## 五大维度评分标准

### 1. 信源得分（0-10分，权重30%）
- 10分：中央级官方媒体（新华社、人民日报、央视等）
- 8-9分：权威通讯社（路透、美联、法新）、权威财经媒体（财新、彭博）
- 6-7分：行业头部媒体、省级官方媒体
- 4-5分：普通媒体、地方媒体
- 1-3分：自媒体、网络媒体

### 2. 影响力得分（0-10分，权重40%）
- 10分：全球性重大事件，影响全人类
- 8-9分：国家级重大政策、重大事件，影响全国
- 6-7分：行业重大事件、区域性重要事件
- 4-5分：普通新闻，影响有限
- 1-3分：小众事件，影响范围很小

### 3. 热度得分（0-10分，权重20%）
- 10分：全网热搜第一，全民关注
- 8-9分：多平台热搜，广泛传播
- 6-7分：行业热点，一定传播
- 4-5分：普通关注度
- 1-3分：关注度很低

### 4. 价值得分（0-10分，权重10%）
- 10分：独家重磅，信息密度极高
- 8-9分：独家报道，信息密度高
- 6-7分：有价值信息，信息密度中等
- 4-5分：普通信息价值
- 1-3分：信息价值很低

### 5. 合规扣分（0-0.05分，直接扣减）
- 0分：完全合规
- 0.01-0.02分：轻微问题（如标题党）
- 0.03-0.05分：明显问题（如谣言嫌疑、低俗内容）"""

_FACT_CHECK_OUTPUT_FORMAT = """
## 请以JSON格式输出分析结果

```json
{
    "is_factual": true或false,
    "content_type": "事实新闻/评论/预测/广告/访谈/数据汇总",
    "original_language": "原文语言（中文/英文/法文/德文等）",
    "translated_title": "如果是外文，填写中文翻译后的标题；如果是中文则填原标题",
    "translated_content": "如果是外文，填写中文翻译后的内容摘要（300字以内）；如果是中文则填原内容摘要",
    "short_summary": "50-150字的简短摘要，客观中立，凸显事件影响",
    "domain": "新闻所属领域（政治/经济/科技/社会/文化/体育/娱乐/健康/环境/其他）",
    "w5h1_analysis": {
        "when": "具体时间（如无则填'无'）",
        "where": "具体地点（如无则填'无'）",
        "who": "具体人物/机构（如无则填'无'）",
        "what": "事件核心内容（如无则填'无'）",
        "why": "原因/背景（如无则填'无'）",
        "how": "方式/过程（如无则填'无'）"
    },
    "source_score": 0到10的信源得分,
    "influence_score": 0到10的影响力得分,
    "heat_score": 0到10的热度得分,
    "value_score": 0到10的价值得分,
    "score_reason": "一句话说明重要性（例如：该事件可能导致全球供应链调整）",
    "reason": "判断理由（中文），简短说明为什么纳入或剔除",
    "confidence": 0.0到1.0之间的置信度
}
```

请只输出JSON，不要输出其他内容。"""


class AIFilterAgent:
    """AI判断器 - 用于5W1H检测和去重判断"""

    # 保留供外部（如测试）直接引用
    FACT_CHECK_PROMPT = (
        _FACT_CHECK_SYSTEM
        + "\n\n## 待分析新闻\n\n标题：{title}\n来源：{source}\n内容：{content}\n"
        + _FACT_CHECK_OUTPUT_FORMAT
    )

    DEDUP_PROMPT = """你是一个专业的新闻去重专家。请分析以下新闻列表，判断哪些新闻是重复的，应该只保留哪几条。

## 去重规则

1. 同一事件的报道视为重复，只保留信息最完整或来源最权威的版本
2. 不同事件但标题相似的，不视为重复
3. 同一事件的不同视角报道（有新增事实），不视为重复

## 权威优先级
中央媒体（新华社、央视、人民日报）> 通讯社（路透、美联、法新）> 权威第三方（财新、澎湃等）

## 待分析新闻列表

{news_list}

## 请以JSON格式输出分析结果

```json
{{
    "duplicate_groups": [
        {{
            "event": "事件描述",
            "duplicate_ids": ["重复的新闻id列表"],
            "kept_id": "应保留的新闻id",
            "reason": "保留理由"
        }}
    ],
    "unique_ids": ["不重复的新闻id列表"],
    "total_kept": 保留数量,
    "total_removed": 剔除数量,
    "confidence": 0.0到1.0之间的置信度
}}
```

请只输出JSON，不要输出其他内容。"""

    def __init__(self, log_dir: str = None):
        self.logger = logging.getLogger("AIFilterAgent")
        self.ai_processor = AIProcessor()
        self.log_dir = Path(log_dir) if log_dir else project_root / "data" / "filter_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logs: List[AIFilterLog] = []
        self.stats = {
            'fact_checks': 0,
            'dedup_checks': 0,
            'ai_calls': 0
        }

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def check_fact(self, title: str, content: str, source: str) -> AIFactCheckResult:
        """AI判断是否为事实新闻（单条）"""
        prompt = self.FACT_CHECK_PROMPT.format(
            title=title,
            source=source,
            content=content[:1500]
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            provider = self.ai_processor.get_provider("FILTER")
            response = provider.chat(messages)
            result = self._parse_fact_check_response(response)
            self.stats['fact_checks'] += 1
            self.stats['ai_calls'] += 1
            self._log_action(
                action="fact_check",
                input_data={"title": title, "source": source, "content": content[:200]},
                result=result.__dict__,
                confidence=result.confidence
            )
            return result

        except Exception as e:
            self.logger.error(f"AI事实判断失败: {e}")
            # 尝试 BACKUP provider
            try:
                backup = self.ai_processor.get_provider("BACKUP")
                if backup:
                    self.logger.info("尝试使用 BACKUP provider...")
                    response = backup.chat(messages)
                    result = self._parse_fact_check_response(response)
                    self.stats['fact_checks'] += 1
                    self.stats['ai_calls'] += 1
                    return result
            except Exception as e2:
                self.logger.error(f"BACKUP provider 也失败: {e2}")

            return self._make_failed_result(f"AI判断异常: {str(e)}")

    def check_fact_batch(self, news_list: List[Dict]) -> List[AIFactCheckResult]:
        """批量AI判断是否为事实新闻"""
        if not news_list:
            return []

        batch_prompt = self._build_batch_prompt(news_list)
        messages = [{"role": "user", "content": batch_prompt}]

        try:
            provider = self.ai_processor.get_provider("FILTER")
            response = provider.chat(messages)
            results = self._parse_fact_check_batch_response(response, len(news_list))
            self.stats['fact_checks'] += len(results)
            self.stats['ai_calls'] += 1
            for news, result in zip(news_list, results):
                self._log_action(
                    action="fact_check_batch",
                    input_data={"title": news.get('title', ''), "source": news.get('source', ''),
                                "content": news.get('content', '')[:200]},
                    result=result.__dict__,
                    confidence=result.confidence
                )
            return results

        except Exception as e:
            self.logger.error(f"AI批量事实判断失败: {e}")
            # 尝试 BACKUP provider
            try:
                backup = self.ai_processor.get_provider("BACKUP")
                if backup:
                    self.logger.info("尝试使用 BACKUP provider...")
                    response = backup.chat(messages)
                    results = self._parse_fact_check_batch_response(response, len(news_list))
                    self.stats['fact_checks'] += len(results)
                    self.stats['ai_calls'] += 1
                    return results
            except Exception as e2:
                self.logger.error(f"BACKUP provider 也失败: {e2}")

            return [self._make_failed_result(f"AI判断异常: {str(e)}") for _ in news_list]

    def check_duplicates(self, news_list: List[Dict]) -> AIDedupResult:
        """AI判断重复新闻"""
        if not news_list:
            return AIDedupResult(
                is_duplicate=False,
                duplicate_groups=[],
                kept_ids=[],
                removed_ids=[],
                reason="空列表",
                confidence=1.0
            )

        news_text = self._format_news_list(news_list)
        prompt = self.DEDUP_PROMPT.format(news_list=news_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            provider = self.ai_processor.get_provider("FILTER")
            response = provider.chat(messages)
            result = self._parse_dedup_response(response, news_list)
            self.stats['dedup_checks'] += 1
            self.stats['ai_calls'] += 1
            self._log_action(
                action="dedup_check",
                input_data={"count": len(news_list), "ids": [n.get('id') for n in news_list]},
                result={
                    "duplicate_groups": result.duplicate_groups,
                    "kept_ids": result.kept_ids,
                    "removed_ids": result.removed_ids
                },
                confidence=result.confidence
            )
            return result

        except Exception as e:
            self.logger.error(f"AI去重判断失败: {e}")
            # 尝试 BACKUP provider
            try:
                backup = self.ai_processor.get_provider("BACKUP")
                if backup:
                    self.logger.info("尝试使用 BACKUP provider...")
                    response = backup.chat(messages)
                    result = self._parse_dedup_response(response, news_list)
                    self.stats['dedup_checks'] += 1
                    self.stats['ai_calls'] += 1
                    return result
            except Exception as e2:
                self.logger.error(f"BACKUP provider 也失败: {e2}")

            return AIDedupResult(
                is_duplicate=False,
                duplicate_groups=[],
                kept_ids=[n.get('id') for n in news_list],
                removed_ids=[],
                reason=f"AI判断异常: {str(e)}",
                confidence=0.0
            )

    # ── 内部：prompt 构建 ─────────────────────────────────────────────────────

    def _build_batch_prompt(self, news_list: List[Dict]) -> str:
        """构建批量 prompt：复用系统规则 + 评分标准，仅替换新闻列表节"""
        news_section = "## 待分析新闻列表\n\n"
        for i, news in enumerate(news_list, 1):
            news_section += f"### 新闻 {i}\n"
            news_section += f"标题：{news.get('title', '')}\n"
            news_section += f"来源：{news.get('source', '')}\n"
            news_section += f"内容：{news.get('content', '')[:500]}\n\n"

        output_format = """## 请以JSON数组格式输出分析结果

```json
[
    {
        "is_factual": true或false,
        "content_type": "事实新闻/评论/预测/广告/访谈/数据汇总",
        "original_language": "原文语言（中文/英文/法文/德文等）",
        "translated_title": "如果是外文，填写中文翻译后的标题；如果是中文则填原标题",
        "translated_content": "如果是外文，填写中文翻译后的内容摘要（300字以内）；如果是中文则填原内容摘要",
        "short_summary": "50-150字的简短摘要，客观中立，凸显事件影响",
        "domain": "新闻所属领域（政治/经济/科技/社会/文化/体育/娱乐/健康/环境/其他）",
        "w5h1_analysis": {
            "when": "时间要素描述（中文），如无则填'无'",
            "where": "地点要素描述（中文），如无则填'无'",
            "who": "人物要素描述（中文），如无则填'无'",
            "what": "事件要素描述（中文），如无则填'无'",
            "why": "原因要素描述（中文），如无则填'无'",
            "how": "方式要素描述（中文），如无则填'无'"
        },
        "source_score": 0到10的信源得分,
        "influence_score": 0到10的影响力得分,
        "heat_score": 0到10的热度得分,
        "value_score": 0到10的价值得分,
        "score_reason": "一句话说明重要性（例如：该事件可能导致全球供应链调整）",
        "reason": "判断理由（中文），简短说明为什么纳入或剔除",
        "confidence": 0.0到1.0之间的置信度
    },
    ...
]
```

请只输出JSON数组，不要输出其他内容。每个新闻对应一个分析结果，顺序与输入列表一致。"""

        return f"{_FACT_CHECK_SYSTEM}\n\n{news_section}\n{output_format}"

    # ── 内部：响应解析 ────────────────────────────────────────────────────────

    @staticmethod
    def _calc_final_score(source_score: float, influence_score: float,
                          heat_score: float, value_score: float) -> float:
        """计算最终得分（公式统一管理，权重：各25%）"""
        raw = (source_score / 10 * 0.25
               + influence_score / 10 * 0.25
               + heat_score / 10 * 0.25
               + value_score / 10 * 0.25) * 100
        return round(raw, 1)

    def _parse_fact_check_data(self, data: Dict) -> AIFactCheckResult:
        """从已解析的 JSON dict 构建 AIFactCheckResult（内部通用）"""
        w5h1_analysis = data.get('w5h1_analysis', {})
        w5h1_score = sum(1 for v in w5h1_analysis.values() if v and v != '无')

        source_score = float(data.get('source_score', 5.0))
        influence_score = float(data.get('influence_score', 5.0))
        heat_score = float(data.get('heat_score', 5.0))
        value_score = float(data.get('value_score', 5.0))

        return AIFactCheckResult(
            is_factual=bool(data.get('is_factual', False)),
            content_type=data.get('content_type', '未知'),
            w5h1_analysis=w5h1_analysis,
            reason=data.get('reason', ''),
            confidence=float(data.get('confidence', 0.0)),
            original_language=data.get('original_language', '中文'),
            translated_title=data.get('translated_title', ''),
            translated_content=data.get('translated_content', ''),
            w5h1_score=w5h1_score,
            short_summary=data.get('short_summary', ''),
            domain=data.get('domain', '其他'),
            source_score=source_score,
            influence_score=influence_score,
            heat_score=heat_score,
            value_score=value_score,
            final_score=self._calc_final_score(
                source_score, influence_score, heat_score, value_score
            ),
            score_reason=data.get('score_reason', '')
        )

    def _parse_fact_check_response(self, response: str) -> AIFactCheckResult:
        """解析单条事实判断响应"""
        try:
            data = parse_json_str(response)
            if not isinstance(data, dict):
                raise ValueError("响应不是 JSON 对象")
            return self._parse_fact_check_data(data)
        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            return self._make_failed_result(f"响应解析异常: {str(e)}")

    def _parse_fact_check_batch_response(self, response: str, expected_count: int) -> List[AIFactCheckResult]:
        """解析批量事实判断响应"""
        try:
            data_list = parse_json_str(response)
            if not isinstance(data_list, list):
                raise ValueError("响应不是 JSON 数组")

            results = [self._parse_fact_check_data(d) for d in data_list]

            # 补足 / 截断至预期数量
            while len(results) < expected_count:
                results.append(self._make_failed_result("响应结果数量不足"))
            return results[:expected_count]

        except Exception as e:
            self.logger.error(f"解析AI批量响应失败: {e}")
            return [self._make_failed_result(f"响应解析异常: {str(e)}") for _ in range(expected_count)]

    def _parse_dedup_response(self, response: str, news_list: List[Dict]) -> AIDedupResult:
        """解析去重判断响应"""
        try:
            data = parse_json_str(response)
            if not isinstance(data, dict):
                raise ValueError("响应不是 JSON 对象")

            duplicate_groups = data.get('duplicate_groups', [])
            unique_ids = data.get('unique_ids', [])

            kept_ids = list(unique_ids) if unique_ids else []
            removed_ids = []
            for group in duplicate_groups:
                dup_ids = group.get('duplicate_ids', [])
                kept_id = group.get('kept_id')
                removed_ids.extend([id for id in dup_ids if id != kept_id])
                if kept_id and kept_id not in kept_ids:
                    kept_ids.append(kept_id)

            if not kept_ids:
                all_ids = [n.get('id') for n in news_list]
                self.logger.warning(f"AI去重返回空kept_ids，保留所有新闻")
                kept_ids = all_ids

            return AIDedupResult(
                is_duplicate=len(removed_ids) > 0,
                duplicate_groups=duplicate_groups,
                kept_ids=kept_ids,
                removed_ids=removed_ids,
                reason=f"共{len(duplicate_groups)}组重复，剔除{len(removed_ids)}条",
                confidence=float(data.get('confidence', 0.0))
            )
        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            all_ids = [n.get('id') for n in news_list]
            return AIDedupResult(
                is_duplicate=False,
                duplicate_groups=[],
                kept_ids=all_ids,
                removed_ids=[],
                reason=f"响应解析异常: {str(e)}",
                confidence=0.0
            )

    # ── 内部：工具方法 ────────────────────────────────────────────────────────

    @staticmethod
    def _make_failed_result(reason: str) -> AIFactCheckResult:
        """构造一个表示失败的 AIFactCheckResult"""
        return AIFactCheckResult(
            is_factual=False,
            content_type="判断失败",
            w5h1_analysis={},
            reason=reason,
            confidence=0.0,
            original_language="未知",
            translated_title="",
            translated_content="",
            w5h1_score=0,
            short_summary="",
            domain="其他",
            source_score=0.0,
            influence_score=0.0,
            heat_score=0.0,
            value_score=0.0,
            final_score=0.0,
            score_reason=""
        )

    def _format_news_list(self, news_list: List[Dict]) -> str:
        """格式化新闻列表（用于去重 prompt）"""
        lines = []
        for i, news in enumerate(news_list, 1):
            news_id = news.get('id', f'news_{i}')
            lines.append(f"[ID: {news_id}]")
            lines.append(f"标题: {news.get('title', '')}")
            lines.append(f"来源: {news.get('source', '')}")
            content = news.get('content', '')[:300]
            lines.append(f"摘要: {content}...")
            lines.append("")
        return "\n".join(lines)

    def _log_action(self, action: str, input_data: Dict, result: Dict, confidence: float):
        """记录判断日志"""
        log = AIFilterLog(
            timestamp=datetime.now().isoformat(),
            action=action,
            input_data=input_data,
            result=result,
            confidence=confidence
        )
        self.logs.append(log)

        try:
            log_file = self.log_dir / f"ai_filter_{datetime.now().strftime('%Y%m%d')}.jsonl"
            if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024:
                backup_file = self.log_dir / f"ai_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                log_file.rename(backup_file)
                self.logger.info(f"日志文件轮转: {backup_file.name}")

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log.to_dict(), ensure_ascii=False) + "\n")
        except (IOError, OSError) as e:
            self.logger.error(f"保存日志失败: {e}")

    def save_summary_log(self):
        """保存汇总日志"""
        if not self.logs:
            return

        log_file = self.log_dir / f"ai_filter_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_logs': len(self.logs),
                'fact_checks': len([l for l in self.logs if l.action == 'fact_check']),
                'dedup_checks': len([l for l in self.logs if l.action == 'dedup_check']),
                'logs': [log.to_dict() for log in self.logs]
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"AI判断汇总日志已保存: {log_file}")
        return log_file

    def get_stats(self) -> Dict:
        """获取统计信息"""
        fact_checks = [log for log in self.logs if log.action == "fact_check"]
        dedup_checks = [log for log in self.logs if log.action == "dedup_check"]

        factual_count = sum(1 for log in fact_checks if log.result.get('is_factual', False))
        total_removed = sum(
            len(log.result.get('removed_ids', []))
            for log in dedup_checks
        )

        return {
            'total_logs': len(self.logs),
            'fact_checks': len(fact_checks),
            'factual_news': factual_count,
            'non_factual_news': len(fact_checks) - factual_count,
            'dedup_checks': len(dedup_checks),
            'total_removed': total_removed,
            'avg_confidence': sum(log.confidence for log in self.logs) / max(len(self.logs), 1)
        }
