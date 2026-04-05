#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资顾问模块
生成投资建议、趋势预测、市场影响分析
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from core.utils.text_utils import format_tags, get_news_title, get_news_content, parse_json_str

logger = logging.getLogger(__name__)


@dataclass
class InvestmentAdvice:
    """投资建议"""
    sentiment: str  # positive/negative/neutral
    sentiment_score: float  # -1.0 to 1.0
    affected_sectors: List[Dict]  # 受影响板块
    affected_stocks: List[Dict]  # 受影响个股
    recommendation: str  # buy/hold/sell/watch
    confidence: float  # 0.0 to 1.0
    time_horizon: str  # short/medium/long
    risk_level: str  # low/medium/high
    key_metrics: Dict
    reasoning: str
    risk_factors: List[str]
    opportunities: List[str]


@dataclass
class MarketImpact:
    """市场影响分析"""
    impact_level: str  # high/medium/low
    impact_score: float  # 0.0 to 10.0
    affected_markets: List[str]  # A股/港股/美股/大宗商品
    expected_volatility: str  # increase/decrease/stable
    historical_similarity: float  # 与历史事件相似度
    historical_outcome: str  # 历史类似事件结果


class InvestmentAdvisor:
    """投资顾问 - 基于新闻生成投资建议"""
    
    def __init__(self, ai_processor):
        self.ai = ai_processor
    
    def analyze(self, news: Dict, history_news: List[Dict] = None) -> InvestmentAdvice:
        """
        分析单条新闻，生成投资建议
        
        Args:
            news: 新闻数据
            history_news: 相关历史新闻
        
        Returns:
            InvestmentAdvice
        """
        # 构建分析提示词
        prompt = self._build_analysis_prompt(news, history_news)
        
        try:
            response = self.ai.chat([
                {"role": "system", "content": "你是资深投资分析师，擅长从新闻中提取投资机会和风险。"},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=1500)
            
            # 解析JSON响应
            analysis = parse_json_str(response)
            return self._parse_advice(analysis)
            
        except Exception as e:
            logger.error(f"Investment analysis failed: {e}")
            return self._default_advice()
    
    def _build_analysis_prompt(self, news: Dict, history_news: List[Dict] = None) -> str:
        """构建分析提示词"""
        history_context = ""
        if history_news:
            history_context = "\n\n相关历史新闻：\n"
            for i, h in enumerate(history_news[:3], 1):
                history_context += f"{i}. {h.get('translated_title', h.get('title', ''))}\n"
        
        return f"""请分析以下新闻的投资价值，以JSON格式返回分析结果。

【新闻标题】
{get_news_title(news)}

【新闻内容】
{get_news_content(news, max_chars=1000)}

【新闻标签】
{format_tags(news.get('tags', []))}

【领域】
{news.get('domain', '未分类')}
{history_context}

请返回以下JSON格式：
{{
    "sentiment": "positive/negative/neutral",
    "sentiment_score": 0.7,
    "affected_sectors": [
        {{"name": "半导体", "impact": "positive", "strength": 4}}
    ],
    "affected_stocks": [
        {{"symbol": "NVDA", "name": "英伟达", "impact": "positive", "confidence": 0.8}}
    ],
    "recommendation": "buy/hold/sell/watch",
    "confidence": 0.75,
    "time_horizon": "short/medium/long",
    "risk_level": "low/medium/high",
    "key_metrics": {{
        "expected_return": "+5%~+10%",
        "probability": 0.7,
        "time_window": "2周内"
    }},
    "reasoning": "详细分析理由...",
    "risk_factors": ["风险1", "风险2"],
    "opportunities": ["机会1", "机会2"]
}}

要求：
1. 只返回JSON，不要其他文字
2. 基于事实分析，不臆测
3. 量化指标要合理
"""
    
    def _parse_advice(self, analysis: Dict) -> InvestmentAdvice:
        """解析分析结果"""
        return InvestmentAdvice(
            sentiment=analysis.get('sentiment', 'neutral'),
            sentiment_score=analysis.get('sentiment_score', 0.0),
            affected_sectors=analysis.get('affected_sectors', []),
            affected_stocks=analysis.get('affected_stocks', []),
            recommendation=analysis.get('recommendation', 'watch'),
            confidence=analysis.get('confidence', 0.5),
            time_horizon=analysis.get('time_horizon', 'medium'),
            risk_level=analysis.get('risk_level', 'medium'),
            key_metrics=analysis.get('key_metrics', {}),
            reasoning=analysis.get('reasoning', ''),
            risk_factors=analysis.get('risk_factors', []),
            opportunities=analysis.get('opportunities', [])
        )
    
    def _default_advice(self) -> InvestmentAdvice:
        """默认建议"""
        return InvestmentAdvice(
            sentiment='neutral',
            sentiment_score=0.0,
            affected_sectors=[],
            affected_stocks=[],
            recommendation='watch',
            confidence=0.0,
            time_horizon='medium',
            risk_level='medium',
            key_metrics={},
            reasoning='分析失败',
            risk_factors=[],
            opportunities=[]
        )
    
    def analyze_market_impact(self, news_list: List[Dict]) -> MarketImpact:
        """
        分析市场整体影响
        
        Args:
            news_list: 当日重要新闻列表
        
        Returns:
            MarketImpact
        """
        # 聚合多条新闻的影响
        combined_impact = self._aggregate_impact(news_list)
        
        return MarketImpact(
            impact_level=combined_impact.get('level', 'medium'),
            impact_score=combined_impact.get('score', 5.0),
            affected_markets=combined_impact.get('markets', []),
            expected_volatility=combined_impact.get('volatility', 'stable'),
            historical_similarity=0.0,
            historical_outcome=''
        )
    
    def _aggregate_impact(self, news_list: List[Dict]) -> Dict:
        """聚合多条新闻的影响"""
        # 简化实现：基于新闻评分和领域计算
        total_score = sum(n.get('final_score', 50) for n in news_list)
        avg_score = total_score / len(news_list) if news_list else 50
        
        # 根据平均分判断影响级别
        if avg_score >= 75:
            level = 'high'
            score = 8.0
        elif avg_score >= 60:
            level = 'medium'
            score = 6.0
        else:
            level = 'low'
            score = 4.0
        
        # 判断受影响市场
        markets = set()
        for news in news_list:
            domain = news.get('domain', '')
            if domain == '经济':
                markets.update(['A股', '港股', '美股'])
            elif domain == '政治':
                markets.update(['A股', '大宗商品'])
            elif domain == '科技':
                markets.update(['美股', 'A股'])
        
        return {
            'level': level,
            'score': score,
            'markets': list(markets),
            'volatility': 'increase' if level == 'high' else 'stable'
        }
    
    def format_advice_section(self, advice: InvestmentAdvice) -> str:
        """格式化投资建议为Markdown"""
        if not advice or advice.confidence == 0:
            return "## 投资分析\n\n暂无投资建议。"
        
        lines = [
            "## 投资分析",
            "",
            f"### 市场情绪",
            f"- 整体情绪：{self._sentiment_emoji(advice.sentiment)} {self._sentiment_text(advice.sentiment)}",
            f"- 信心指数：{advice.sentiment_score * 100:.0f}/100",
            ""
        ]
        
        # 影响板块
        if advice.affected_sectors:
            lines.extend([
                "### 影响板块",
                "| 板块 | 影响方向 | 影响程度 |",
                "|------|----------|----------|"
            ])
            for sector in advice.affected_sectors[:5]:
                impact = "📈 正面" if sector.get('impact') == 'positive' else "📉 负面" if sector.get('impact') == 'negative' else "➡️ 中性"
                strength = "⭐" * sector.get('strength', 3)
                lines.append(f"| {sector.get('name', '未知')} | {impact} | {strength} |")
            lines.append("")
        
        # 相关标的
        if advice.affected_stocks:
            lines.extend([
                "### 相关标的",
                "| 代码 | 名称 | 影响 | 置信度 |",
                "|------|------|------|--------|"
            ])
            for stock in advice.affected_stocks[:5]:
                impact = "📈" if stock.get('impact') == 'positive' else "📉" if stock.get('impact') == 'negative' else "➡️"
                conf = f"{stock.get('confidence', 0) * 100:.0f}%"
                lines.append(f"| {stock.get('symbol', '-')} | {stock.get('name', '-')} | {impact} | {conf} |")
            lines.append("")
        
        # 投资建议
        lines.extend([
            "### 投资建议",
            f"- **建议操作**：{self._recommendation_text(advice.recommendation)}",
            f"- **时间窗口**：{advice.key_metrics.get('time_window', '未明确')}",
            f"- **预期收益**：{advice.key_metrics.get('expected_return', '未评估')}",
            f"- **成功概率**：{advice.key_metrics.get('probability', 0) * 100:.0f}%",
            f"- **风险等级**：{self._risk_text(advice.risk_level)}",
            ""
        ])
        
        # 分析理由
        if advice.reasoning:
            lines.extend([
                "### 分析理由",
                advice.reasoning,
                ""
            ])
        
        # 风险提示
        if advice.risk_factors:
            lines.extend([
                "### ⚠️ 风险提示",
            ])
            for risk in advice.risk_factors:
                lines.append(f"- {risk}")
            lines.append("")
        
        # 投资机会
        if advice.opportunities:
            lines.extend([
                "### 💡 投资机会",
            ])
            for opp in advice.opportunities:
                lines.append(f"- {opp}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _sentiment_emoji(self, sentiment: str) -> str:
        """情绪表情"""
        return {
            'positive': '😊',
            'negative': '😟',
            'neutral': '😐'
        }.get(sentiment, '😐')
    
    def _sentiment_text(self, sentiment: str) -> str:
        """情绪文字"""
        return {
            'positive': '乐观',
            'negative': '谨慎',
            'neutral': '中性'
        }.get(sentiment, '中性')
    
    def _recommendation_text(self, rec: str) -> str:
        """建议文字"""
        return {
            'buy': '买入',
            'hold': '持有',
            'sell': '卖出',
            'watch': '观望'
        }.get(rec, '观望')
    
    def _risk_text(self, risk: str) -> str:
        """风险文字"""
        return {
            'low': '低 🟢',
            'medium': '中 🟡',
            'high': '高 🔴'
        }.get(risk, '中 🟡')
