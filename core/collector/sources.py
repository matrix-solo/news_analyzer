#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS源配置管理 V2.0
从sources.yaml加载信源配置，支持双RSS源（主源+备份源）
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import yaml
from pathlib import Path

project_root = Path(__file__).parent.parent.parent


@dataclass
class RSSSource:
    """RSS源配置"""
    name: str
    url: str
    rss_url: str = ""
    rss_url_backup: str = ""
    type: str = "domestic"
    category: str = "general"
    media_type: str = ""
    region: str = ""
    credibility: str = ""
    bias: str = ""
    strengths: str = ""
    enabled: bool = True
    priority: int = 1
    description: str = ""
    language: str = "zh"
    note: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'url': self.url,
            'rss_url': self.rss_url,
            'rss_url_backup': self.rss_url_backup,
            'type': self.type,
            'category': self.category,
            'media_type': self.media_type,
            'region': self.region,
            'credibility': self.credibility,
            'bias': self.bias,
            'enabled': self.enabled,
            'priority': self.priority,
            'description': self.description,
            'language': self.language,
            'note': self.note
        }
    
    @classmethod
    def from_yaml(cls, data: Dict, source_type: str = "domestic", category: str = "general") -> 'RSSSource':
        return cls(
            name=data.get('name', ''),
            url=data.get('url', ''),
            rss_url=data.get('rss_url', ''),
            rss_url_backup=data.get('rss_url_backup', ''),
            type=source_type,
            category=category,
            media_type=data.get('type', ''),
            region=data.get('region', ''),
            credibility=data.get('credibility', ''),
            bias=data.get('bias', ''),
            strengths=data.get('strengths', ''),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 1),
            description=data.get('note', ''),
            language='zh' if '中国' in data.get('region', '') or '中文' in data.get('name', '') else 'en',
            note=data.get('note', '')
        )


class RSSSourceManager:
    """RSS源管理器 V2.0 - 从sources.yaml加载，支持双RSS源"""
    
    DEFAULT_CONFIG_PATH = project_root / "sources.yaml"
    
    CATEGORY_MAPPING = {
        'news_agency': 'agency',
        'comprehensive': 'comprehensive',
        'analytical': 'analytical',
        'regional': 'regional',
        'central': 'official',
        'market_professional': 'market',
        'technology': 'technology'
    }
    
    AUTHORITY_PRIORITY = {
        'official': 1,
        'agency': 2,
        'comprehensive': 3,
        'regional': 4,
        'market': 5,
        'analytical': 6
    }
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger("RSSSourceManager")
        self.sources: Dict[str, RSSSource] = {}
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        
        self._load_config()
    
    def _load_config(self):
        """从sources.yaml加载配置"""
        if not self.config_path.exists():
            self.logger.error(f"配置文件不存在: {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._parse_config(config)
            
            enabled_count = sum(1 for s in self.sources.values() if s.enabled and s.rss_url)
            self.logger.info(f"加载RSS源: {len(self.sources)}个 (有效: {enabled_count}个)")
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
    
    def _parse_config(self, config: Dict):
        """解析YAML配置"""
        international = config.get('international', {})
        domestic = config.get('domestic', {})
        
        for category_key, sources_list in international.items():
            category = self.CATEGORY_MAPPING.get(category_key, category_key)
            for source_data in sources_list:
                source = RSSSource.from_yaml(source_data, 'international', category)
                self.sources[source.name] = source
        
        for category_key, sources_list in domestic.items():
            category = self.CATEGORY_MAPPING.get(category_key, category_key)
            for source_data in sources_list:
                source = RSSSource.from_yaml(source_data, 'domestic', category)
                self.sources[source.name] = source
    
    def reload_config(self):
        """重新加载配置"""
        self.sources.clear()
        self._load_config()
    
    def get_source(self, name: str) -> Optional[RSSSource]:
        """获取指定源"""
        return self.sources.get(name)
    
    def get_sources_by_type(self, source_type: str) -> List[RSSSource]:
        """按类型获取源"""
        return [s for s in self.sources.values() if s.type == source_type and s.enabled and s.rss_url]
    
    def get_sources_by_category(self, category: str) -> List[RSSSource]:
        """按分类获取源"""
        return [s for s in self.sources.values() if s.category == category and s.enabled and s.rss_url]
    
    def get_enabled_sources(self) -> List[RSSSource]:
        """获取所有启用的源（必须有主RSS源）"""
        return [s for s in self.sources.values() if s.enabled and s.rss_url]
    
    def get_domestic_sources(self) -> List[RSSSource]:
        """获取国内源"""
        return self.get_sources_by_type('domestic')
    
    def get_international_sources(self) -> List[RSSSource]:
        """获取国际源"""
        return self.get_sources_by_type('international')
    
    def get_official_sources(self) -> List[RSSSource]:
        """获取官媒源"""
        return self.get_sources_by_category('official')
    
    def get_sources_by_credibility(self, credibility: str) -> List[RSSSource]:
        """按可信度获取源"""
        return [s for s in self.sources.values() if s.credibility == credibility and s.enabled and s.rss_url]
    
    def get_high_credibility_sources(self) -> List[RSSSource]:
        """获取高可信度源"""
        return [s for s in self.sources.values() if s.credibility in ['高', '中高'] and s.enabled and s.rss_url]
    
    def get_authority_priority(self, source_name: str) -> int:
        """获取信源权威优先级（数字越小越优先）"""
        source = self.sources.get(source_name)
        if not source:
            return 999
        return self.AUTHORITY_PRIORITY.get(source.category, 999)
    
    def is_official_source(self, source_name: str) -> bool:
        """判断是否为官媒"""
        source = self.sources.get(source_name)
        return source.category == 'official' if source else False
    
    def is_agency_source(self, source_name: str) -> bool:
        """判断是否为通讯社"""
        source = self.sources.get(source_name)
        return source.category == 'agency' if source else False
    
    def get_fact_source_type(self, source_name: str) -> str:
        """获取事实源类型"""
        source = self.sources.get(source_name)
        if not source:
            return "unknown"
        
        if source.category == 'official':
            return "中央媒体"
        elif source.category == 'agency':
            return "通讯社"
        else:
            return "权威第三方"
    
    def get_region_tag(self, source_name: str) -> str:
        """获取地域标签"""
        source = self.sources.get(source_name)
        if not source:
            return "unknown"
        
        if source.type == 'domestic':
            return "国内"
        else:
            region = source.region
            if '欧洲' in region:
                return "国际-欧洲"
            elif '中东' in region:
                return "国际-中东"
            elif '东亚' in region or '日本' in region:
                return "国际-东亚"
            elif '美国' in region or '英国' in region:
                return "国际-西方"
            else:
                return "国际"
    
    def list_sources(self) -> List[Dict]:
        """列出所有源"""
        return [s.to_dict() for s in self.sources.values()]
    
    def get_sources_summary(self) -> Dict:
        """获取源统计摘要"""
        total = len(self.sources)
        enabled = sum(1 for s in self.sources.values() if s.enabled and s.rss_url)
        domestic = sum(1 for s in self.sources.values() if s.type == 'domestic' and s.enabled and s.rss_url)
        international = sum(1 for s in self.sources.values() if s.type == 'international' and s.enabled and s.rss_url)
        official = sum(1 for s in self.sources.values() if s.category == 'official' and s.enabled and s.rss_url)
        high_cred = sum(1 for s in self.sources.values() if s.credibility in ['高', '中高'] and s.enabled and s.rss_url)
        with_backup = sum(1 for s in self.sources.values() if s.enabled and s.rss_url and s.rss_url_backup)
        
        return {
            'total': total,
            'enabled': enabled,
            'disabled': total - enabled,
            'domestic': domestic,
            'international': international,
            'official': official,
            'high_credibility': high_cred,
            'with_backup': with_backup
        }
