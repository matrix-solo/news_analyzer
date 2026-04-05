#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析增强模块
生成更详细的分析报告，包含数据支撑、历史对比、趋势预测
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from core.utils.text_utils import format_tags, get_news_title, get_news_content

logger = logging.getLogger(__name__)


@dataclass
class DepthAnalysis:
    """深度分析结果"""
    when: str = ""           # 何时
    where: str = ""          # 何地
    who: str = ""            # 何人
    what: str = ""           # 何事
    why: str = ""            # 为何
    how: str = ""            # 如何
    summary: str = ""        # 高质量摘要（200字）
    key_facts: List[str] = field(default_factory=list)  # 关键事实
    history_context: str = ""  # 前因后果（基于历史关联）
    comparison: str = ""       # 与历史事件的异同点
    impact: str = ""          # 对相关领域的直接影响
    reasonable_inference: str = ""  # 基于事实的合理推演
    data_table: str = ""     # 从新闻提取的结构化数据表
    core_points: str = ""     # 连贯分析文章主体（保留兼容）
    total_length: int = 0


class DepthAnalyzer:
    """深度分析器 - 生成基于完整上下文的结构化深度分析"""

    def __init__(self, ai_processor):
        self.ai = ai_processor

    def analyze(
        self,
        news: Dict,
        related_history: List[Dict] = None,
        market_anchor: str = ""
    ) -> DepthAnalysis:
        """
        生成深度分析

        流程：
        1. 如果有 original_article，使用全文深度分析
        2. 否则降级到基于摘要的分析

        Args:
            news: 当前新闻（含 original_article 优先）
            related_history: 相关历史新闻（含 original_article 优先）
            market_anchor: 市场锚点文本

        Returns:
            DepthAnalysis
        """
        has_full_text = bool(news.get('original_article'))

        if has_full_text:
            prompt = self._build_full_text_prompt(news, related_history, market_anchor)
        else:
            prompt = self._build_legacy_prompt(news, related_history, market_anchor)

        try:
            response = self.ai.chat([
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=3000)

            return self._parse_analysis(response)

        except Exception as e:
            logger.error(f"深度分析失败: {e}")
            return self._fallback_analysis(news)

    def _build_full_text_prompt(
        self,
        news: Dict,
        related_history: List[Dict] = None,
        market_anchor: str = ""
    ) -> str:
        """基于全文的深度分析Prompt"""
        today_article = news.get('original_article', '')
        title = news.get('translated_title') or news.get('title', '')
        domain = news.get('domain', '未分类')

        history_block = ""
        if related_history:
            history_lines = []
            for i, h in enumerate(related_history[:10], 1):
                h_title = h.get('translated_title') or h.get('title', '')
                h_date = h.get('pub_date', '')[:10]
                h_article = h.get('original_article') or h.get('summary', '')[:500]
                h_score = getattr(h, 'unified_score', 0)
                history_lines.append(
                    f"【历史{i}】({h_date}, 关联度: {h_score:.2f})\n"
                    f"标题：{h_title}\n"
                    f"内容：{h_article[:500]}..."
                )
            history_block = "\n\n".join(history_lines)

        market_block = f"\n\n【市场锚点】\n{market_anchor}" if market_anchor else ""

        return f"""请基于以下完整上下文撰写深度分析，严格按JSON格式输出：

【今日事件全文】
{today_article[:8000]}

【新闻标题】{title}
【新闻领域】{domain}

【历史关联新闻】（按关联度排序，已获取全文）
{history_block if history_block else '（无历史关联）'}
{market_block}

请输出如下JSON（所有字段均为字符串或字符串列表）：

{{
  "when": "具体时间或时间段",
  "where": "具体地点",
  "who": "关键人物/机构",
  "what": "核心事件",
  "why": "原因/背景",
  "how": "方式/过程",
  "summary": "200字客观摘要",
  "key_facts": ["关键事实1", "关键事实2", "关键事实3"],
  "history_context": "前因后果（基于历史关联链）",
  "comparison": "与历史类似事件的异同点",
  "impact": "对相关领域的直接影响",
  "reasonable_inference": "基于事实的合理推演（1-3个月）"
}}"""

    def _build_legacy_prompt(
        self,
        news: Dict,
        related_history: List[Dict] = None,
        market_anchor: str = ""
    ) -> str:
        """降级版Prompt（无全文时使用）"""
        history_block = ""
        if related_history:
            history_block = "\n\n【相关历史记录（近30天）】\n"
            for i, h in enumerate(related_history[:5], 1):
                title = h.get('translated_title') or h.get('title', '')
                pub_date = h.get('pub_date', '')
                summary = (h.get('summary') or h.get('content') or '')[:120]
                history_block += f"{i}. [{pub_date}] {title}\n   摘要：{summary}\n"

        market_block = f"\n\n{market_anchor}" if market_anchor else ""

        return f"""请对以下新闻进行结构化深度分析，严格按JSON格式输出。

【新闻标题】{get_news_title(news)}
【新闻内容】{get_news_content(news, max_chars=1500)}
【新闻领域】{news.get('domain', '未分类')}
【新闻标签】{format_tags(news.get('tags', []))}
{history_block}{market_block}

{{
  "when": "时间（推断自内容）",
  "where": "地点（推断自内容）",
  "who": "人物/机构",
  "what": "核心事件",
  "why": "原因（如有）",
  "how": "方式（如有）",
  "summary": "150字摘要",
  "key_facts": ["事实1", "事实2"],
  "history_context": "基于已知历史的背景",
  "comparison": "与历史事件对比",
  "impact": "潜在影响",
  "reasonable_inference": "合理推演"
}}"""

    def _build_enhanced_prompt(self, news: Dict, related_history: List[Dict] = None,
                               market_anchor: str = "") -> str:
        """兼容旧接口"""
        return self._build_legacy_prompt(news, related_history, market_anchor)

    def _parse_analysis(self, response: str) -> DepthAnalysis:
        """解析 JSON 格式的分析结果"""
        import json, re
        m = re.search(r'\{[\s\S]*\}', response)
        if m:
            try:
                data = json.loads(m.group(0))
                return DepthAnalysis(
                    when=data.get("when", ""),
                    where=data.get("where", ""),
                    who=data.get("who", ""),
                    what=data.get("what", ""),
                    why=data.get("why", ""),
                    how=data.get("how", ""),
                    summary=data.get("summary", ""),
                    key_facts=data.get("key_facts", []),
                    history_context=data.get("history_context", ""),
                    comparison=data.get("comparison", ""),
                    impact=data.get("impact", ""),
                    reasonable_inference=data.get("reasonable_inference", ""),
                    data_table=data.get("data_table", ""),
                    core_points=data.get("core_analysis") or data.get("summary", ""),
                    total_length=len(data.get("summary", ""))
                )
            except json.JSONDecodeError:
                pass
        return self._fallback_analysis_from_response(response)

    def _fallback_analysis(self, news: Dict) -> DepthAnalysis:
        content = get_news_content(news, max_chars=200)
        return DepthAnalysis(
            when="",
            where="",
            who="",
            what="",
            why="",
            how="",
            summary=content[:200] if content else "",
            key_facts=[],
            history_context="",
            comparison="",
            impact="",
            reasonable_inference="",
            core_points=f"新闻核心：{content}..." if content else "",
            total_length=0
        )

    def _fallback_analysis_from_response(self, response: str) -> DepthAnalysis:
        """从原始响应降级"""
        return DepthAnalysis(
            when="",
            where="",
            who="",
            what="",
            why="",
            how="",
            summary=response[:200] if response else "",
            key_facts=[],
            history_context="",
            comparison="",
            impact="",
            reasonable_inference="",
            core_points=response,
            total_length=len(response)
        )

    def format_for_report(self, analysis: DepthAnalysis) -> list[str]:
        """格式化为报告 Markdown 行列表"""
        lines = []

        lines.append("### 5W1H要素")
        lines.append("")
        lines.append("| 要素 | 内容 |")
        lines.append("|------|------|")
        lines.append(f"| 何时 | {analysis.when or '无'} |")
        lines.append(f"| 何地 | {analysis.where or '无'} |")
        lines.append(f"| 何人 | {analysis.who or '无'} |")
        lines.append(f"| 何事 | {analysis.what or '无'} |")
        lines.append(f"| 为何 | {analysis.why or '无'} |")
        lines.append(f"| 如何 | {analysis.how or '无'} |")
        lines.append("")

        if analysis.summary:
            lines.append("### 高质量摘要")
            lines.append("")
            lines.append(analysis.summary)
            lines.append("")

        if analysis.key_facts:
            lines.append("#### 关键事实")
            lines.append("")
            for fact in analysis.key_facts:
                lines.append(f"- {fact}")
            lines.append("")

        if analysis.history_context:
            lines.append("#### 前因后果")
            lines.append("")
            lines.append(analysis.history_context)
            lines.append("")

        if analysis.comparison:
            lines.append("#### 与历史对比")
            lines.append("")
            lines.append(analysis.comparison)
            lines.append("")

        if analysis.impact:
            lines.append("#### 潜在影响")
            lines.append("")
            lines.append(analysis.impact)
            lines.append("")

        if analysis.reasonable_inference:
            lines.append("#### 合理推演")
            lines.append("")
            lines.append(analysis.reasonable_inference)
            lines.append("")

        if analysis.data_table and "无可提取" not in analysis.data_table:
            lines.append("### 新闻数据提取")
            lines.append("")
            lines.append(analysis.data_table)
            lines.append("")

        return lines


_SYSTEM_PROMPT = (
    "你是一个专业的新闻深度分析师。"
    "你的任务是基于完整的事实（原文+历史关联）进行深度分析，提炼决策者需要的信息。"
    "你必须输出有具体事实依据的分析，不做空洞的猜测。"
    "严格按照要求的JSON格式输出，不输出任何JSON以外的内容。"
)
