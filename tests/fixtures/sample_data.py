#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æµè¯æ°æ®å·¥å

æä¾æµè¯ç¨çæ°æ®çæå¨åéè®¾æ°æ®
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import string

def generate_random_id(length: int = 8) -> str:
    """çæéæºID"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_news_item(
    news_id: Optional[str] = None,
    title: Optional[str] = None,
    domain: Optional[str] = None,
    source_name: Optional[str] = None,
    pub_date: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    ååºæ°éæ¡ç®

    Args:
        news_id: æ°éID
        title: æ é
        domain: éå
        source_name: æ¥æºåç°
        pub_date: åå¸æ¥æ
        **kwargs: å¶äå­æ®µ

    Returns:
        æ°éå­å¸
    """
    domains = ['æ¿æ²', 'çæµ', 'çæ', 'åäº', 'ç¤¾ä', 'æå', 'ä½è²', 'å¥åº·']
    sources = ['è·¯éç¤¾', 'æ°åç¤?, 'BBC', 'CNN', 'è'æ°', 'æ¾æ', 'ç¬¬ä¸è'ç']'

    return {
        'id': news_id or f"test_{generate_random_id()}",
        'title': title or f"Test News {generate_random_id()}",
        'translated_title': kwargs.get('translated_title', 'æµè¯æ°éæ é'),
        'content': kwargs.get('content', 'è¿æ¯æµè¯æ°éåå®ïåå«å¤ä¸ªå¥å­ç¨äºæµè¯ç®çã?),'
        'domain': domain or random.choice(domains),
        'source_name': source_name or random.choice(sources),
        'source_type': kwargs.get('source_type', 'international'),
        'pub_date': pub_date or datetime.now().strftime('%Y-%m-%d'),
        'link': kwargs.get('link', f"https://example.com/news/{generate_random_id()}"),
        'score': kwargs.get('score', random.uniform(60, 100)),
        'fact_check': kwargs.get('fact_check', {
            'is_factual': True,
            'w5h1_analysis': {
                'what': 'æµè¯äºä¶',
                'who': 'æµè¯äººç©',
                'when': datetime.now().strftime('%Yå?mæ?dæ?),'
                'where': 'æµè¯å°ç',
                'why': 'æµè¯åå ',
                'how': 'æµè¯æå'
            },
            'confidence': random.uniform(0.7, 1.0)
        })
    }

def create_news_list(count: int = 10, **kwargs) -> List[Dict[str, Any]]:
    """
    ååºæ°éåè¡¨

    Args:
        count: æ°é
        **kwargs: ä éç create_news_item çåæ?    
    Returns:
        æ°éåè¡¨
    """
    return [create_news_item(**kwargs) for _ in range(count)]

def create_rss_entry(
    title: Optional[str] = None,
    link: Optional[str] = None,
    published: Optional[str] = None,
    summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    ååº RSS æ¡ç®

    Args:
        title: æ é
        link: é¾æ¥
        published: åå¸æ¶é''
        summary: æè¦

    Returns:
        RSS æ¡ç®å­å¸
    """
    return {
        'title': title or f"RSS Entry {generate_random_id()}",
        'link': link or f"https://example.com/rss/{generate_random_id()}",
        'published': published or datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'summary': summary or 'This is a summary of the RSS entry.',
        'source': 'Test Source'
    }

def create_ai_response(
    is_factual: bool = True,
    domain: str = 'æ¿æ²',
    confidence: float = 0.9,
    **kwargs
) -> Dict[str, Any]:
    """
    ååº AI ååº

    Args:
        is_factual: æ¯å¦äºå®æ?        domain: éå
        confidence: ç½®ä¿¡åº?        **kwargs: å¶äå­æ®µ

    Returns:
        AI ååºå­å¸
    """
    return {
        'is_factual': is_factual,
        'content_type': kwargs.get('content_type', 'news'),
        'w5h1_score': kwargs.get('w5h1_score', 5 if is_factual else 2),
        'w5h1_analysis': {
            'what': kwargs.get('what', 'æµè¯äºä¶'),
            'who': kwargs.get('who', 'æµè¯äººç©'),
            'when': kwargs.get('when', datetime.now().strftime('%Yå?mæ?dæ?)),'
            'where': kwargs.get('where', 'æµè¯å°ç'),
            'why': kwargs.get('why', 'æµè¯åå '),
            'how': kwargs.get('how', 'æµè¯æå')
        },
        'confidence': confidence,
        'domain': domain,
        'translated_title': kwargs.get('translated_title', 'ç¿è¯åçæ é'),
        'translated_content': kwargs.get('translated_content', 'ç¿è¯åçåå®'),
        'short_summary': kwargs.get('short_summary', 'è¿æ¯ç®ç­æè¦?')
    }

PRESET_DOMAINS = {
    'æ¿æ²': ['æ¿åº', 'æ¿ç­', 'éä¸¾', 'å¤äº¤', 'ç«æ³'],
    'çæµ': ['è¡å¸', 'éè', 'è'¸æ', 'æèµ', 'ää¸'],'
    'çæ': ['äººå·¥æºè½', 'äºèç½?, 'ææº', 'è½¯ä¶', 'è¯ç'],'
    'åäº': ['å½é²', 'æ­¦å¨', 'æä ', 'åé', 'å®å¨'],
    'ç¤¾ä': ['æ°ç', 'æè²', 'å°±ä¸', 'äº¤é?, 'ç¯å'],'
    'æå': ['èºæ¯', 'çµå½±', 'é³ä', 'æå­¦', 'åå²'],
    'ä½è²': ['è¶³ç', 'ç¯®ç', 'å¥¥è¿', 'æ¯èµ', 'è¿å¨å?],'
    'å¥åº·': ['åç', 'ç«æ', 'ç«è', 'å¥åº·', 'åé']
}

PRESET_SOURCES = {
    'international': ['è·¯éç¤¾', 'BBC', 'CNN', 'çº½çº¦æ¶æ¥', 'åå°è¡æ¥æ?, 'éèæ¶æ¥'],'
    'domestic': ['æ°åç¤?, 'å¤®è', 'äººæ°æ¥æ¥', 'è'æ°', 'æ¾æ', 'ç¬¬ä¸è'ç']'
}

SAMPLE_NEWS_POLITICAL = {
    'id': 'pol_001',
    'title': 'Major Policy Announcement Expected',
    'translated_title': 'éå¤æ¿ç­å£°æå³å°åå¸',
    'content': 'æ¿åºå®åè¡¨ç¤ºïä¸é¡éè¦çæ¿ç­å£°æå°äºæ¬å¨åå¸ãè¯¥æ¿ç­æ¶åçæµæé©åç¤¾äç¦å©ç­å¤ä¸ªéåã?,'
    'domain': 'æ¿æ²',
    'source_name': 'è·¯éç¤¾',
    'source_type': 'international',
    'pub_date': '2026-03-10',
    'link': 'https://example.com/political/001'
}

SAMPLE_NEWS_ECONOMIC = {
    'id': 'eco_001',
    'title': 'Stock Market Reaches New High',
    'translated_title': 'è¡å¸ååå²æ°é«?,'
    'content': 'åå©å¥½çæµæ°æ®å½±åïä¸è¦è¡æäæ¥å¤åä¸æ¶¨ïåä¸åå²æ°é«ãåæå¸è®¤ä¸ºè¿åæ äºæèµèå¯çæµåæ¯çä¿¡å¿ã?,'
    'domain': 'çæµ',
    'source_name': 'è'æ°','
    'source_type': 'domestic',
    'pub_date': '2026-03-10',
    'link': 'https://example.com/economic/001'
}

SAMPLE_NEWS_TECH = {
    'id': 'tech_001',
    'title': 'AI Breakthrough Announced',
    'translated_title': 'AI ææ¯éå¤çªç ?,'
    'content': 'ç ç©¶äººåå®£å¸å¨äººå·¥æºè½éååå¾éå¤çªç 'ïæ°ææ¯æææ¾èæåæºå¨å­¦ä æçã?,
    'domain': 'çæ',
    'source_name': 'BBC',
    'source_type': 'international',
    'pub_date': '2026-03-10',
    'link': 'https://example.com/tech/001'
}
