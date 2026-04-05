#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史关联分析引擎（融合版）
融合主题分析和实体分析，提升效率并降低维护成本
"""

import re
import logging
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter

# 尝试导入 jieba，如果失败则使用简单分词
try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

# 导入性能监控
from core.utils.performance import timed

logger = logging.getLogger(__name__)

# 中文停用词
STOPWORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '他', '它', '她', '们', '什么', '这个', '那个', '如何',
    '怎么', '为什么', '哪', '哪个', '哪里', '谁', '多少', '几', '可以', '应该',
    '可能', '需要', '因为', '所以', '但是', '然而', '虽然', '如果', '只有',
    '或者', '以及', '并且', '而且', '然后', '于是', '接着', '之后', '其中',
    '对于', '关于', '通过', '根据', '按照', '依据', '随着', '为了',
    '以', '把', '被', '给', '向', '从', '到', '为', '与', '及', '和', '或',
    '年', '月', '日', '时', '分', '秒', '号', '点', '今日', '昨日', '明日',
    '当天', '目前', '现在', '最近', '近日', '近期', '日前', '此前',
    '之后', '之前', '期间', '当中', '之际', '以来', '起', '来'
])

# 实体权重配置
ENTITY_WEIGHTS = {
    '人名': 2.0,
    '地名': 1.5,
    '机构': 1.3,
    '其他': 1.0
}

# 实体识别规则
PERSON_SUFFIXES = ['先生', '女士', '总统', '总理', '主席', '部长', '省长', '市长', '局长', '司长', '处长', '科长', '主任', '书记', '将军', '教授', '博士', '记者', '发言人']
PLACE_SUFFIXES = ['市', '省', '县', '区', '国', '洲', '岛', '半岛', '山脉', '河流', '海域', '地区', '特区']
ORG_SUFFIXES = ['公司', '集团', '银行', '大学', '学院', '研究所', '研究院', '机构', '组织', '协会', '基金会', '委员会', '议会', '国会', '政府', '部门', '部', '局', '厅', '院', '社', '报', '台']


@dataclass
class RelatedNews:
    """历史关联新闻"""
    news_id: str
    title: str
    pub_date: str
    related_score: float
    unified_score: float
    time_score: float
    time_type: str
    matched_keywords: List[str]
    matched_entities: List[str]


class UnifiedAnalyzer:
    """
    融合分析器 - 统一主题和实体分析
    
    核心思想：
    1. 使用TF-IDF提取关键词
    2. 使用规则识别实体（人名/地名/机构）
    3. 对实体词进行权重加成
    4. 计算余弦相似度
    """
    
    def __init__(self, history_news: List[Dict]):
        self.history_news = history_news
        self.history_vectors = []
        self.history_texts = []
        self._build_index()
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []
        
        if HAS_JIEBA:
            words = jieba.cut(text)
            return [w for w in words if w.strip() and w not in STOPWORDS and len(w) > 1]
        else:
            words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
            return [w for w in words if w.strip() and w not in STOPWORDS and len(w) > 1]
    
    def _detect_entity_type(self, word: str, context: str = "") -> str:
        """
        检测实体类型
        
        Args:
            word: 待检测的词
            context: 上下文（可选）
        
        Returns:
            实体类型：人名/地名/机构/其他
        """
        # 检查人名后缀
        for suffix in PERSON_SUFFIXES:
            if word.endswith(suffix) or suffix in context:
                return '人名'
        
        # 检查地名后缀
        for suffix in PLACE_SUFFIXES:
            if word.endswith(suffix):
                return '地名'
        
        # 检查机构后缀
        for suffix in ORG_SUFFIXES:
            if word.endswith(suffix):
                return '机构'
        
        # 检查是否为常见人名模式（2-4个汉字，首字母大写等）
        if len(word) >= 2 and len(word) <= 4:
            if re.match(r'^[\u4e00-\u9fff]+$', word):
                # 简单判断：如果上下文中有称谓，则可能是人名
                for suffix in ['表示', '称', '说', '认为', '指出', '强调', '宣布']:
                    if suffix in context:
                        return '人名'
        
        return '其他'
    
    def _boost_entity_weight(self, words: List[str], context: str = "") -> List[str]:
        """
        对实体词进行权重加成
        
        通过重复词来提升TF-IDF权重
        
        Args:
            words: 分词列表
            context: 上下文
        
        Returns:
            加权后的词列表
        """
        boosted_words = []
        
        for word in words:
            entity_type = self._detect_entity_type(word, context)
            weight = ENTITY_WEIGHTS.get(entity_type, 1.0)
            
            # 通过重复词来提升权重
            repeat_count = int(weight)
            for _ in range(repeat_count):
                boosted_words.append(word)
        
        return boosted_words
    
    def _preprocess(self, news: Dict) -> Tuple[str, str]:
        """
        预处理新闻
        
        Returns:
            (合并文本, 原始文本用于上下文)
        """
        keywords = news.get('keywords', [])
        if not isinstance(keywords, list):
            keywords = []
        
        tags = news.get('tags', [])
        if not isinstance(tags, list):
            tags = []
        
        texts = [
            news.get('translated_title', ''),
            news.get('translated_content', ''),
            news.get('summary', ''),
            ' '.join(keywords),
            ' '.join(tags)
        ]
        
        merged_text = ' '.join([t for t in texts if t])
        return merged_text, merged_text
    
    def _calculate_tf(self, tokens: List[str]) -> Dict[str, int]:
        """计算词频"""
        return Counter(tokens)
    
    def _calculate_idf(self, all_tokens: List[List[str]]) -> Dict[str, float]:
        """计算逆文档频率"""
        n_docs = len(all_tokens)
        df = Counter()
        for tokens in all_tokens:
            df.update(set(tokens))
        
        idf = {}
        for word, freq in df.items():
            idf[word] = 1.0 + (n_docs / (1.0 + freq))
        return idf
    
    def _calculate_tfidf(self, tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
        """计算TF-IDF"""
        tf = self._calculate_tf(tokens)
        tfidf = {}
        max_tf = max(tf.values()) if tf else 1
        
        for word, freq in tf.items():
            tf_normalized = freq / max_tf
            tfidf[word] = tf_normalized * idf.get(word, 1.0)
        
        return tfidf
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        all_words = set(vec1.keys()) | set(vec2.keys())
        
        v1 = [vec1.get(w, 0.0) for w in all_words]
        v2 = [vec2.get(w, 0.0) for w in all_words]
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _build_index(self):
        """构建索引"""
        if not self.history_news:
            return
        
        all_tokens = []
        for news in self.history_news:
            text, context = self._preprocess(news)
            tokens = self._tokenize(text)
            # 实体权重加成
            boosted_tokens = self._boost_entity_weight(tokens, context)
            all_tokens.append(boosted_tokens)
            self.history_texts.append(text)
        
        # 计算IDF
        idf = self._calculate_idf(all_tokens)
        
        # 计算每条新闻的TF-IDF向量
        for tokens in all_tokens:
            tfidf = self._calculate_tfidf(tokens, idf)
            self.history_vectors.append(tfidf)
        
        logger.info(f"融合索引构建完成: {len(self.history_vectors)} 条")
    
    def calculate_similarity(self, current_news: Dict) -> List[Tuple[int, float]]:
        """
        计算当前新闻与历史新闻的相似度
        
        Returns:
            List[(索引, 相似度)]
        """
        if not self.history_vectors:
            return []
        
        # 当前新闻向量化
        text, context = self._preprocess(current_news)
        tokens = self._tokenize(text)
        boosted_tokens = self._boost_entity_weight(tokens, context)
        
        # 重新计算IDF
        all_tokens = []
        for news in self.history_news:
            t, _ = self._preprocess(news)
            toks = self._tokenize(t)
            boosted = self._boost_entity_weight(toks, "")
            all_tokens.append(boosted)
        all_tokens.append(boosted_tokens)
        
        idf = self._calculate_idf(all_tokens)
        current_vector = self._calculate_tfidf(boosted_tokens, idf)
        
        # 计算与所有历史新闻的相似度
        similarities = []
        for idx, history_vector in enumerate(self.history_vectors):
            score = self._cosine_similarity(current_vector, history_vector)
            similarities.append((idx, score))
        
        return similarities
    
    def get_matched_keywords(self, current_news: Dict, history_idx: int) -> List[str]:
        """获取匹配的关键词"""
        if history_idx >= len(self.history_news):
            return []
        
        current_text, _ = self._preprocess(current_news)
        current_tokens = set(self._tokenize(current_text))
        
        history_news = self.history_news[history_idx]
        history_text, _ = self._preprocess(history_news)
        history_tokens = set(self._tokenize(history_text))
        
        matched = current_tokens & history_tokens
        return list(matched)[:10]
    
    def get_matched_entities(self, current_news: Dict, history_idx: int) -> List[str]:
        """获取匹配的实体"""
        if history_idx >= len(self.history_news):
            return []
        
        current_text, context = self._preprocess(current_news)
        current_tokens = self._tokenize(current_text)
        current_entities = set()
        for token in current_tokens:
            entity_type = self._detect_entity_type(token, context)
            if entity_type != '其他':
                current_entities.add(token)
        
        history_news = self.history_news[history_idx]
        history_text, history_context = self._preprocess(history_news)
        history_tokens = self._tokenize(history_text)
        history_entities = set()
        for token in history_tokens:
            entity_type = self._detect_entity_type(token, history_context)
            if entity_type != '其他':
                history_entities.add(token)
        
        matched = current_entities & history_entities
        return list(matched)


class TimeAnalyzer:
    """时间关联分析器 - 90天时间线"""
    
    def __init__(self):
        self.time_ranges = [
            (0, 7, '本周关联', 1.0),
            (7, 30, '近期关联', 0.7),
            (30, 90, '历史背景', 0.3)
        ]
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期"""
        if not date_str:
            return None
        
        try:
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(date_str.replace('Z', '').split('.')[0], fmt)
                    return dt
                except (ValueError, AttributeError):
                    continue
            return None
        except (ValueError, AttributeError):
            return None
    
    def calculate_time_score(self, current_date: datetime, history_date: datetime) -> float:
        """计算时间关联度"""
        if not current_date or not history_date:
            return 0.0
        
        days_diff = abs((current_date - history_date).days)
        
        for min_days, max_days, _, base_score in self.time_ranges:
            if min_days <= days_diff < max_days:
                progress = (days_diff - min_days) / (max_days - min_days)
                return base_score - progress * (base_score - base_score * 0.5)
        
        return 0.0
    
    def classify_time_relationship(self, current_date: datetime, history_date: datetime) -> str:
        """分类时间关联类型"""
        if not current_date or not history_date:
            return "未知"
        
        days_diff = (current_date - history_date).days
        
        for min_days, max_days, type_name, _ in self.time_ranges:
            if min_days <= days_diff < max_days:
                return type_name
        
        return "超范围" if days_diff >= 90 else "未来"


class HistoryRelationEngine:
    """
    历史关联分析引擎（融合版）
    
    权重分配：
    - 融合分析（TF-IDF + 实体加权）：70%
    - 时间分析：30%
    """
    
    WEIGHTS = {
        'unified': 0.7,
        'time': 0.3
    }
    
    def __init__(self, history_news: List[Dict]):
        self.history_news = history_news
        
        # 初始化融合分析器
        self.unified_analyzer = UnifiedAnalyzer(history_news)
        self.time_analyzer = TimeAnalyzer()
        
        # 解析日期
        self.current_date = datetime.now()
        self.history_dates = []
        for n in history_news:
            dt = self.time_analyzer.parse_date(n.get('pub_date', ''))
            self.history_dates.append(dt)
        
        logger.info(f"历史关联引擎初始化完成（融合版）: {len(history_news)} 条历史新闻")

    def find_related_by_dimensions(
        self,
        current_news: Dict,
        *,
        top_k: int = 5,
        threshold: float = 0.05,
        domains: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[RelatedNews]:
        """
        维度化查询接口（为报告层提供更稳定的入口）。

        第一阶段实现：在现有融合相似度之上增加“领域/标签”软约束：
        - 若提供 domains，则优先在同领域新闻中找关联
        - 若提供 tags，则把 tags 拼接进 current_news 的 tags 字段以提升匹配
        """
        if domains:
            filtered_history = [h for h in self.history_news if h.get("domain") in set(domains)]
            engine = HistoryRelationEngine(filtered_history)
            cur = dict(current_news)
            if tags:
                cur_tags = cur.get("tags") if isinstance(cur.get("tags"), list) else []
                cur["tags"] = list({*cur_tags, *tags})
            return engine.find_related_news(cur, top_k=top_k, threshold=threshold)

        cur = dict(current_news)
        if tags:
            cur_tags = cur.get("tags") if isinstance(cur.get("tags"), list) else []
            cur["tags"] = list({*cur_tags, *tags})
        return self.find_related_news(cur, top_k=top_k, threshold=threshold)
    
    @timed
    def find_related_news(
        self,
        current_news: Dict,
        top_k: int = 5,
        threshold: float = 0.05
    ) -> List[RelatedNews]:
        """查找相关历史新闻（融合版）"""
        
        if not self.history_news:
            return []
        
        # 1. 融合相似度
        unified_scores = self.unified_analyzer.calculate_similarity(current_news)
        
        # 2. 计算综合关联度
        results = []
        
        for idx, unified_score in unified_scores:
            if idx >= len(self.history_news):
                continue
            
            history_news = self.history_news[idx]
            
            # 时间关联度
            history_date = self.history_dates[idx] if idx < len(self.history_dates) else None
            if history_date:
                time_score = self.time_analyzer.calculate_time_score(
                    self.current_date, history_date
                )
                time_type = self.time_analyzer.classify_time_relationship(
                    self.current_date, history_date
                )
            else:
                time_score = 0.0
                time_type = "未知"
            
            # 综合评分
            final_score = (
                unified_score * self.WEIGHTS['unified'] +
                time_score * self.WEIGHTS['time']
            )
            
            if final_score >= threshold:
                # 获取匹配的关键词和实体
                matched_keywords = self.unified_analyzer.get_matched_keywords(current_news, idx)
                matched_entities = self.unified_analyzer.get_matched_entities(current_news, idx)
                
                results.append(RelatedNews(
                    news_id=history_news.get('news_id', ''),
                    title=history_news.get('translated_title', history_news.get('title', '')),
                    pub_date=history_news.get('pub_date', '')[:10],
                    related_score=final_score,
                    unified_score=unified_score,
                    time_score=time_score,
                    time_type=time_type,
                    matched_keywords=matched_keywords[:5],
                    matched_entities=matched_entities[:5]
                ))
        
        # 3. 排序并返回Top K
        results.sort(key=lambda x: x.related_score, reverse=True)
        
        logger.info(f"找到 {len(results)} 条相关历史新闻")
        return results[:top_k]


def format_related_section(related_news: List[RelatedNews], current_title: str = "") -> str:
    """格式化历史关联分析 section"""
    
    if not related_news:
        return "## 历史关联分析\n\n无历史关联信息。"
    
    sections = ["## 历史关联分析", ""]
    
    # 按时间类型分组
    background = [n for n in related_news if n.time_type in ["历史背景", "近期关联"]]
    development = [n for n in related_news if n.time_type == "本周关联"]
    
    # 1. 事件前因和背景
    if background:
        b = background[0]
        days_diff = (datetime.now() - datetime.strptime(b.pub_date, '%Y-%m-%d')).days if b.pub_date else 0
        time_desc = f"{days_diff}天前" if days_diff > 0 else ""
        
        sections.append("事件前因和背景：")
        sections.append(f"可参考【{b.pub_date}】{b.title}（关联度：{b.related_score:.2f}，{time_desc}）")
        sections.append("")
    
    # 2. 后续发展
    if development:
        d = development[0]
        sections.append("后续发展：")
        sections.append(f"可见【{d.pub_date}】{d.title}（关联度：{d.related_score:.2f}）")
        sections.append("")
    
    # 3. 其他关联报道
    other_news = [n for n in related_news if n not in background and n not in development]
    if other_news:
        sections.append("其他关联报道：")
        for o in other_news[:3]:
            sections.append(f"可参考【{o.pub_date}】{o.title}（关联度：{o.related_score:.2f}）")
        sections.append("")
    
    # 4. 综合说明
    if len(related_news) >= 2:
        sections.append("综合说明：")
        
        main_related = related_news[0]
        
        summary_parts = [f"本事件与【{main_related.pub_date}】{main_related.title}存在关联"]
        
        if len(related_news) >= 2:
            second = related_news[1]
            summary_parts.append(f"与【{second.pub_date}】{second.title}形成{'时间' if second.time_type == '本周关联' else '内容'}上的关联")
        
        sections.append('，'.join(summary_parts) + '。')
    
    return '\n'.join(sections)


def format_related_table(related_news: List[RelatedNews]) -> str:
    """以表格形式格式化历史关联结果"""
    if not related_news:
        return ""

    lines: List[str] = []
    lines.append("### 历史关联明细")
    lines.append("")
    lines.append("| 日期 | 标题 | 关联度 | 时间类型 | 匹配关键词 | 匹配实体 |")
    lines.append("|------|------|--------|----------|------------|----------|")

    for item in related_news:
        keywords = ", ".join(item.matched_keywords) if item.matched_keywords else "-"
        entities = ", ".join(item.matched_entities) if item.matched_entities else "-"
        lines.append(
            f"| {item.pub_date or '-'} | {item.title} | {item.related_score:.2f} | "
            f"{item.time_type} | {keywords} | {entities} |"
        )

    lines.append("")
    return "\n".join(lines)


def get_engine(history_news: List[Dict]) -> HistoryRelationEngine:
    """获取历史关联引擎实例"""
    return HistoryRelationEngine(history_news)
