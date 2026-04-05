#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
领域分类器 - 使用AI自动补全新闻领域标签
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger("DomainClassifier")

DOMAINS = ['政治', '经济', '科技', '军事', '社会', '文化', '体育', '娱乐']

class DomainClassifier:
    """领域分类器"""

    def __init__(self, ai_processor):
        self.ai = ai_processor

    def classify(self, news: Dict) -> Optional[str]:
        """
        对新闻进行领域分类
        
        Args:
            news: 新闻字典，包含 title, content 等字段
        
        Returns:
            领域名称，如果分类失败返回 None
        """
        title = news.get('translated_title') or news.get('title') or '无标题'
        content = news.get('translated_content') or news.get('content') or ''
        content = content[:500]

        provider = self.ai.get_provider("ANALYSIS")
        if not provider:
            logger.warning("AI provider不可用，使用规则分类")
            return self._rule_based_classify(title, content)

        prompt = f"""请判断以下新闻属于哪个领域？

【新闻标题】{title}

【新闻内容】{content}

【可选领域】{', '.join(DOMAINS)}

【要求】
1. 只返回领域名称，不要返回其他内容
2. 如果无法确定，返回"社会"
3. 必须从上述可选领域中选择

【输出格式】直接输出领域名称，例如：政治"""

        try:
            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.1, max_tokens=50)

            domain = response.strip() if response else ''

            if not domain:
                logger.warning(f"AI返回空值，使用规则分类: {title[:30]}...")
                return self._rule_based_classify(title, content)

            if domain in DOMAINS:
                logger.info(f"领域分类成功: {title[:30]}... -> {domain}")
                return domain
            else:
                for d in DOMAINS:
                    if d in domain:
                        logger.info(f"领域分类成功(模糊匹配): {title[:30]}... -> {d}")
                        return d

                logger.warning(f"领域分类返回无效值: '{domain}'，使用规则分类")
                return self._rule_based_classify(title, content)

        except Exception as e:
            logger.error(f"领域分类失败: {e}")
            return self._rule_based_classify(title, content)

    def _rule_based_classify(self, title: str, content: str) -> str:
        """基于规则的领域分类（AI不可用时使用）"""
        text = (title + ' ' + content).lower()

        keywords = {
            '政治': ['政治', '政府', '政策', '选举', '外交', '国会', '议会', '总统', '总理', '部长'],
            '经济': ['经济', '财经', '金融', '股市', '股票', '投资', '贸易', 'gdp', '通胀', '央行', '利率'],
            '科技': ['科技', 'tech', '人工智能', 'ai', '芯片', '半导体', '互联网', '手机', '电脑', '软件', 'openai'],
            '军事': ['军事', '军队', '武器', '国防', '演习', '战争', '冲突', '士兵', '坦克', '导弹', '航母'],
            '社会': ['社会', '教育', '就业', '犯罪', '法律', '民生', '房价', '灾害', '事故'],
            '文化': ['文化', '电影', '音乐', '艺术', '文学', '博物馆', '展览', '历史', '传统'],
            '体育': ['体育', '足球', '篮球', '网球', '奥运', '世界杯', '冠军', '联赛', '运动员', '比赛'],
            '娱乐': ['娱乐', '明星', '演员', '歌手', '综艺', '电影', '电视剧', '八卦', '网红']
        }

        for domain, words in keywords.items():
            for word in words:
                if word in text:
                    return domain

        return '社会'

    def classify_batch(self, news_list: list) -> Dict[str, str]:
        """
        批量分类新闻

        Args:
            news_list: 新闻列表

        Returns:
            字典 {news_id: domain}
        """
        results = {}
        for news in news_list:
            news_id = news.get('news_id')
            if not news_id:
                continue

            if news.get('domain'):
                results[news_id] = news['domain']
                continue

            domain = self.classify(news)
            if domain:
                results[news_id] = domain
            else:
                results[news_id] = '社会'

        return results


def classify_news_domain(news: Dict, ai_processor) -> str:
    """
    对单条新闻进行领域分类
    
    Args:
        news: 新闻字典
        ai_processor: AI处理器
    
    Returns:
        领域名称
    """
    classifier = DomainClassifier(ai_processor)
    domain = classifier.classify(news)
    return domain or '社会'
