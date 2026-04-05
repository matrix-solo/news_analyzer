# -*- coding: utf-8 -*-
"""
轻量级新闻分类器

基于规则的快速分类，不调用 LLM 或模型：
1. RSS category 映射
2. 信源名称映射
3. 标题/内容关键词匹配
"""

from typing import List, Dict, Any, Tuple


class LightweightClassifier:

    DOMAIN_LABELS = ['政治', '经济', '科技', '军事', '社会', '文化', '体育', '娱乐']

    CATEGORY_MAPPING = {
        'technology': '科技',
        'tech': '科技',
        'finance': '经济',
        'financial': '经济',
        'market': '经济',
        'politics': '政治',
        'political': '政治',
        'world': '政治',
        'international': '政治',
        'military': '军事',
        'war': '军事',
        'sports': '体育',
        'sport': '体育',
        'entertainment': '娱乐',
        'culture': '文化',
        'education': '教育',
        'health': '社会',
        'healthcare': '社会',
        'environment': '社会',
        'society': '社会',
        'social': '社会',
    }

    SOURCE_DOMAIN_MAPPING = {
        'BBC News': '政治',
        'Reuters': '经济',
        'AFP': '政治',
        'AP': '政治',
        '路透社': '经济',
        '美联社': '政治',
        '法新社': '政治',
        '新华社': '政治',
        '共同社': '政治',
        '韩联社': '政治',
        '安莎社': '政治',
        'TechCrunch': '科技',
        'Wired': '科技',
        'The Verge': '科技',
        'Ars Technica': '科技',
    }

    KEYWORD_MAPPING = {
        '政治': [
            '政治', '外交', '政府', '总统', '首相', '总理', '国会', '议会',
            '选举', '政党', '制裁', '谈判', '峰会', '联合国', '北约', '欧盟',
            '伊朗', '俄罗斯', '乌克兰', '美国', '中国', '欧盟', '以色列', '加沙',
            '战争', '冲突', '军事', '部队', '军队', '武器', '导弹', '核',
            'politics', 'government', 'president', 'prime minister', 'election',
            'sanction', 'war', 'military', 'conflict', 'nato', 'eu', 'un'
        ],
        '经济': [
            '经济', '财经', '金融', '股市', '股票', '投资', '贸易', '关税',
            'GDP', '通胀', '央行', '利率', '汇率', '石油', '黄金', '银行',
            '保险', '期货', '债券', '基金', '房产', '房价', '消费', '零售',
            'economy', 'economic', 'finance', 'financial', 'stock', 'market',
            'trade', 'investment', 'gdp', 'inflation', 'interest rate'
        ],
        '军事': [
            '军事', '武器', '导弹', '核', '军队', '部队', '国防', '军工',
            '战机', '军舰', '坦克', '士兵', '将军', '演习', '基地', '雷达',
            'military', 'weapon', 'missile', 'nuclear', 'army', 'defense',
            'aircraft', 'warship', 'drone', 'combat', 'troops'
        ],
        '科技': [
            '科技', '技术', '人工智能', 'AI', '芯片', '半导体', '互联网',
            '软件', '硬件', '手机', '电脑', '苹果', '谷歌', '微软', 'OpenAI',
            'ChatGPT', '机器人', '5G', '6G', '区块链', '元宇宙', '自动驾驶',
            '电动车', '特斯拉', 'SpaceX', '航天', '卫星',
            'technology', 'tech', 'artificial intelligence', 'ai', 'chip',
            'semiconductor', 'software', 'hardware', 'robot', 'space', 'tesla'
        ],
        '文化': [
            '文化', '娱乐', '电影', '音乐', '艺术', '文学', '博物馆', '展览',
            '明星', '演员', '导演', '歌手', '综艺', '电视剧', '票房',
            'culture', 'entertainment', 'movie', 'film', 'music', 'art',
            'celebrity', 'actor', 'director', 'museum', 'exhibition'
        ],
        '教育': [
            '教育', '学校', '大学', '学院', '学生', '教师', '教授', '考试',
            '招生', '留学', '奖学金', '课程', '教材', '培训',
            'education', 'school', 'university', 'college', 'student', 'teacher',
            'exam', 'course', 'training'
        ],
        '体育': [
            '体育', '足球', '篮球', '网球', '奥运', '世界杯', '冠军', '联赛',
            '比赛', '运动员', '球队', '俱乐部', '转会', '金牌', '奖牌',
            'sports', 'football', 'soccer', 'basketball', 'tennis', 'olympics',
            'championship', 'league', 'athlete', 'team', 'world cup'
        ],
        '社会': [
            '社会', '健康', '医疗', '医院', '医生', '疾病', '疫情', '疫苗',
            '药物', '环境', '气候', '灾害', '事故', '犯罪', '法律', '案件',
            '警方', '调查', '逮捕', '火灾', '洪水', '地震', '空难',
            'society', 'social', 'health', 'healthcare', 'medical', 'hospital',
            'disease', 'vaccine', 'environment', 'climate', 'crime', 'law',
            'accident', 'disaster', 'investigation'
        ],
    }

    def __init__(self):
        self.domain_labels = self.DOMAIN_LABELS
        self.confidence_threshold = 0.5

    def classify_batch(self, news_list: List[Dict]) -> List[Dict[str, Any]]:
        """
        批量分类新闻

        Args:
            news_list: 新闻列表，每条包含 title, content, category, source_name 等字段

        Returns:
            分类结果列表，每项包含 domain 和 confidence
        """
        results = []
        for news in news_list:
            domain, confidence = self.classify_single(news)
            results.append({
                'domain': domain,
                'confidence': confidence
            })
        return results

    def classify_single(self, news: Dict) -> Tuple[str, float]:
        """
        单条新闻分类

        Args:
            news: 新闻字典，包含 title, content, category, source_name 等

        Returns:
            (domain, confidence) 元组
        """
        category = news.get('category', '') or ''
        source_name = news.get('source_name', '') or ''
        title = news.get('title', '') or ''
        content = (news.get('content', '') or '')[:500]

        text = (title + ' ' + content).lower()

        domain, confidence, match_type = self._classify(
            category, source_name, title, text
        )

        return domain, confidence

    def _classify(
        self,
        category: str,
        source_name: str,
        title: str,
        text: str
    ) -> Tuple[str, float, str]:
        """
        内部分类逻辑

        Returns:
            (domain, confidence, match_type)
        """
        category_lower = category.lower()
        source_lower = source_name.lower()

        if category_lower and category_lower != 'comprehensive':
            mapped = self.CATEGORY_MAPPING.get(category_lower)
            if mapped:
                return mapped, 0.9, 'category'

        if source_lower:
            for source_key, domain in self.SOURCE_DOMAIN_MAPPING.items():
                if source_key.lower() in source_lower:
                    return domain, 0.85, 'source'

        domain_counts = {}
        for domain, keywords in self.KEYWORD_MAPPING.items():
            count = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    count += 1
            if count > 0:
                domain_counts[domain] = count

        if domain_counts:
            best_domain = max(domain_counts, key=domain_counts.get)
            max_count = domain_counts[best_domain]
            confidence = min(0.5 + max_count * 0.1, 0.85)
            return best_domain, confidence, 'keyword'

        return '社会', 0.5, 'default'
