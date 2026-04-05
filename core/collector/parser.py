#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS解析器
解析RSS/Atom格式的XML内容
"""

import xml.etree.ElementTree as ET
import logging
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape


@dataclass
class RSSItem:
    """RSS条目"""
    title: str
    link: str
    description: str = ""
    pub_date: Optional[datetime] = None
    author: str = ""
    category: str = ""
    guid: str = ""
    source: str = ""
    content: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'pub_date': self.pub_date.isoformat() if self.pub_date else None,
            'author': self.author,
            'category': self.category,
            'guid': self.guid,
            'source': self.source,
            'content': self.content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSItem':
        pub_date = None
        if data.get('pub_date'):
            try:
                pub_date = datetime.fromisoformat(data['pub_date'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            title=data.get('title', ''),
            link=data.get('link', ''),
            description=data.get('description', ''),
            pub_date=pub_date,
            author=data.get('author', ''),
            category=data.get('category', ''),
            guid=data.get('guid', ''),
            source=data.get('source', ''),
            content=data.get('content', '')
        )


@dataclass
class RSSFeed:
    """RSS订阅源"""
    title: str
    link: str
    description: str = ""
    language: str = ""
    items: List[RSSItem] = field(default_factory=list)
    source_name: str = ""
    source_type: str = "domestic"
    used_backup: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'language': self.language,
            'items': [item.to_dict() for item in self.items],
            'source_name': self.source_name,
            'source_type': self.source_type,
            'used_backup': self.used_backup
        }


class RSSParser:
    """RSS解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger("RSSParser")
    
    def parse(self, xml_content: str, source_name: str = "", source_type: str = "domestic") -> Optional[RSSFeed]:
        """
        解析RSS XML内容
        
        Args:
            xml_content: RSS XML内容
            source_name: 来源名称
            source_type: 来源类型 (domestic/international)
        
        Returns:
            RSSFeed对象
        """
        try:
            xml_content = self._clean_xml(xml_content)
            
            root = ET.fromstring(xml_content)
            
            if root.tag == 'rss':
                return self._parse_rss(root, source_name, source_type)
            elif root.tag == '{http://www.w3.org/2005/Atom}feed':
                return self._parse_atom(root, source_name, source_type)
            elif root.tag == 'feed':
                return self._parse_atom(root, source_name, source_type)
            else:
                self.logger.warning(f"未知的RSS格式: {root.tag}")
                return None
                
        except ET.ParseError as e:
            self.logger.error(f"XML解析错误: {e}")
            return None
        except Exception as e:
            self.logger.error(f"RSS解析异常: {e}")
            return None
    
    def _clean_xml(self, xml_content: str) -> str:
        """清理XML内容"""
        xml_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml_content)
        xml_content = xml_content.strip()
        return xml_content
    
    def _parse_rss(self, root: ET.Element, source_name: str, source_type: str) -> RSSFeed:
        """解析RSS 2.0格式"""
        channel = root.find('channel')
        if channel is None:
            return RSSFeed(title="", link="", source_name=source_name, source_type=source_type)
        
        title = self._get_text(channel, 'title')
        link = self._get_text(channel, 'link')
        description = self._get_text(channel, 'description')
        language = self._get_text(channel, 'language')
        
        items = []
        for item_elem in channel.findall('item'):
            item = self._parse_rss_item(item_elem, source_name)
            if item and item.title and item.link:
                items.append(item)
        
        return RSSFeed(
            title=title,
            link=link,
            description=description,
            language=language,
            items=items,
            source_name=source_name,
            source_type=source_type
        )
    
    def _parse_rss_item(self, item_elem: ET.Element, source_name: str) -> Optional[RSSItem]:
        """解析RSS条目"""
        title = self._get_text(item_elem, 'title')
        link = self._get_text(item_elem, 'link')
        description = self._get_text(item_elem, 'description')
        author = self._get_text(item_elem, 'author') or self._get_text(item_elem, '{http://purl.org/dc/elements/1.1/}creator')
        category = self._get_text(item_elem, 'category')
        guid = self._get_text(item_elem, 'guid')
        
        pub_date_str = self._get_text(item_elem, 'pubDate')
        pub_date = self._parse_date(pub_date_str) if pub_date_str else None
        
        content = self._get_text(item_elem, '{http://purl.org/rss/1.0/modules/content/}encoded')
        if not content:
            content = self._get_text(item_elem, 'content:encoded')
        
        title = self._clean_text(title)
        description = self._clean_text(description)
        content = self._clean_text(content)
        
        return RSSItem(
            title=title,
            link=link,
            description=description,
            pub_date=pub_date,
            author=author,
            category=category,
            guid=guid or link,
            source=source_name,
            content=content
        )
    
    def _parse_atom(self, root: ET.Element, source_name: str, source_type: str) -> RSSFeed:
        """解析Atom格式"""
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        title = self._get_text(root, 'atom:title', ns) or self._get_text(root, 'title')
        link = ""
        for link_elem in root.findall('atom:link', ns) + root.findall('link'):
            href = link_elem.get('href')
            if href:
                link = href
                break
            elif link_elem.text:
                link = link_elem.text
                break
        
        description = self._get_text(root, 'atom:subtitle', ns) or self._get_text(root, 'subtitle')
        language = root.get('{http://www.w3.org/XML/1998/namespace}lang', '')
        
        items = []
        for entry in root.findall('atom:entry', ns) + root.findall('entry'):
            item = self._parse_atom_entry(entry, source_name, ns)
            if item and item.title and item.link:
                items.append(item)
        
        return RSSFeed(
            title=title,
            link=link,
            description=description or "",
            language=language,
            items=items,
            source_name=source_name,
            source_type=source_type
        )
    
    def _parse_atom_entry(self, entry: ET.Element, source_name: str, ns: dict) -> Optional[RSSItem]:
        """解析Atom条目"""
        title = self._get_text(entry, 'atom:title', ns) or self._get_text(entry, 'title')
        
        link = ""
        for link_elem in entry.findall('atom:link', ns) + entry.findall('link'):
            href = link_elem.get('href')
            if href:
                link = href
                break
        
        description = ""
        for tag in ['atom:summary', 'summary', 'atom:content', 'content']:
            desc = self._get_text(entry, tag, ns if tag.startswith('atom:') else None)
            if desc:
                description = desc
                break
        
        author = ""
        author_elem = entry.find('atom:author', ns) or entry.find('author')
        if author_elem is not None:
            author = self._get_text(author_elem, 'atom:name', ns) or self._get_text(author_elem, 'name')
        
        category = ""
        for cat_elem in entry.findall('atom:category', ns) + entry.findall('category'):
            term = cat_elem.get('term', '')
            if term:
                category = term
                break
        
        pub_date_str = self._get_text(entry, 'atom:published', ns) or self._get_text(entry, 'published')
        pub_date_str = pub_date_str or self._get_text(entry, 'atom:updated', ns) or self._get_text(entry, 'updated')
        pub_date = self._parse_date(pub_date_str) if pub_date_str else None
        
        guid = self._get_text(entry, 'atom:id', ns) or self._get_text(entry, 'id') or link
        
        title = self._clean_text(title)
        description = self._clean_text(description)
        
        return RSSItem(
            title=title,
            link=link,
            description=description,
            pub_date=pub_date,
            author=author,
            category=category,
            guid=guid,
            source=source_name,
            content=description
        )
    
    def _get_text(self, element: ET.Element, tag: str, ns: dict = None) -> str:
        """获取元素文本"""
        try:
            if ns and ':' in tag:
                prefix, local = tag.split(':', 1)
                full_tag = f"{{{ns.get(prefix, '')}}}{local}"
                child = element.find(full_tag)
            else:
                child = element.find(tag)
            
            if child is not None and child.text:
                return child.text.strip()
        except (AttributeError, TypeError):
            pass
        return ""
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        text = unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期"""
        if not date_str:
            return None
        
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        date_str = date_str.strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
