#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容解析模块 - 规则解析中间层

包含：
1. RuleBasedParser: 基于 YAML 规则的领域/标签/内容解析
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# ==================== RuleBasedParser 部分 ====================


@dataclass
class ParseConfidence:
    domain: float = 0.0
    tags: float = 0.0
    w5h1: float = 0.0


@dataclass
class ParseResult:
    # 结构化输出（当前阶段主要覆盖 domain/tags/content）
    domain: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    content: Optional[str] = None

    # 解释性与回放信息
    extraction_method: str = "rule_only"  # rule_only/ai_fallback/ai_only
    matched_rules: List[str] = field(default_factory=list)
    confidence: ParseConfidence = field(default_factory=ParseConfidence)


class ParsingRules:
    """加载并持有 YAML 规则。"""

    def __init__(self, rules_path: Optional[str] = None):
        project_root = Path(__file__).parent.parent
        default_path = project_root / "config" / "parsing_rules.yaml"
        example_path = project_root / "config" / "parsing_rules.example.yaml"

        path = Path(rules_path) if rules_path else default_path
        if not path.exists():
            path = example_path

        self.path = path
        self.raw: Dict[str, Any] = {}
        self.defaults: Dict[str, Any] = {}
        self.sources: Dict[str, Any] = {}

        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.raw = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"解析规则加载失败: {self.path} - {e}")
            self.raw = {}

        self.defaults = self.raw.get("defaults", {}) or {}
        self.sources = self.raw.get("sources", {}) or {}


class RuleBasedParser:
    """
    规则优先解析器：输入采集阶段的 news dict，输出 ParseResult。

    约定输入字段：title, content, source_name, source_type, category, pub_date, link
    """

    def __init__(self, rules: Optional[ParsingRules] = None):
        self.rules = rules or ParsingRules()

    def parse(self, news: Dict[str, Any]) -> ParseResult:
        source_name = (news.get("source_name") or "").strip()
        source_type = (news.get("source_type") or "").strip()
        language = (news.get("language") or "").strip()

        src_cfg = self._select_source_config(source_name, source_type, language)

        content = self._extract_content(news, src_cfg)

        domain, domain_conf, tags, tags_conf, matched = self._apply_rules(
            news=news,
            content=content or "",
            src_cfg=src_cfg,
        )

        return ParseResult(
            domain=domain,
            tags=tags,
            content=content,
            extraction_method="rule_only",
            matched_rules=matched,
            confidence=ParseConfidence(domain=domain_conf, tags=tags_conf, w5h1=0.0),
        )

    def should_ai_fallback(self, result: ParseResult) -> bool:
        th = (self.rules.defaults.get("confidence_threshold") or {}) if self.rules else {}
        domain_th = float(th.get("domain", 0.7))
        tags_th = float(th.get("tags", 0.6))
        return (result.domain is None or result.confidence.domain < domain_th) and (
            not result.tags or result.confidence.tags < tags_th
        )

    def _select_source_config(self, source_name: str, source_type: str, language: str) -> Dict[str, Any]:
        if not self.rules or not self.rules.sources:
            return {}

        cfg = self.rules.sources.get(source_name)
        if not isinstance(cfg, dict):
            return {}

        match = cfg.get("match", {}) or {}
        if match.get("source_name") and match.get("source_name") != source_name:
            return {}
        if match.get("type") and match.get("type") != source_type:
            return {}
        if language and match.get("language") and match.get("language") != language:
            return {}
        return cfg

    def _extract_content(self, news: Dict[str, Any], src_cfg: Dict[str, Any]) -> str:
        defaults = (self.rules.defaults.get("content") or {}) if self.rules else {}
        content_cfg = defaults.copy()
        content_cfg.update(src_cfg.get("content", {}) or {})

        prefer_fields = content_cfg.get("prefer_fields") or ["content", "description"]
        min_length = int(content_cfg.get("min_length", 80))
        strip_html = bool(content_cfg.get("strip_html", True))

        raw = ""
        for f in prefer_fields:
            v = news.get(f)
            if isinstance(v, str) and v.strip():
                raw = v
                break

        cleaned = raw.strip()
        if strip_html:
            cleaned = self._strip_html(cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned if len(cleaned) >= min_length else cleaned

    def _apply_rules(
        self, news: Dict[str, Any], content: str, src_cfg: Dict[str, Any]
    ) -> Tuple[Optional[str], float, List[str], float, List[str]]:
        title = (news.get("title") or "").strip()
        rss_category = (news.get("category") or "").strip()

        text = f"{title}\n{content}".lower()

        matched_rules: List[str] = []
        domain: Optional[str] = None
        tags: List[str] = []
        domain_conf = 0.0
        tags_conf = 0.0

        candidates: List[Dict[str, Any]] = []
        candidates.extend((src_cfg.get("rules") or []) if isinstance(src_cfg.get("rules"), list) else [])
        defaults = (self.rules.defaults or {}) if self.rules else {}
        candidates.extend((defaults.get("domain_rules") or []) if isinstance(defaults.get("domain_rules"), list) else [])

        for rule in candidates:
            if not isinstance(rule, dict):
                continue
            rule_name = rule.get("name") or "unnamed_rule"
            match = rule.get("match") or {}
            if not isinstance(match, dict):
                continue

            if not self._match_rule(match, text=text, rss_category=rss_category):
                continue

            matched_rules.append(rule_name)
            setv = rule.get("set") or {}
            if isinstance(setv, dict):
                if setv.get("domain") and not domain:
                    domain = str(setv["domain"])
                    domain_conf = max(domain_conf, 0.85 if rule in (src_cfg.get("rules") or []) else 0.75)
                add_tags = setv.get("tags_add") or []
                if isinstance(add_tags, list):
                    for t in add_tags:
                        if isinstance(t, str) and t and t not in tags:
                            tags.append(t)
                    if add_tags:
                        tags_conf = max(tags_conf, 0.8 if rule in (src_cfg.get("rules") or []) else 0.65)

        return domain, domain_conf, tags, tags_conf, matched_rules

    def _match_rule(self, match: Dict[str, Any], text: str, rss_category: str) -> bool:
        kwa = match.get("keywords_any")
        if isinstance(kwa, list) and kwa:
            if not any(str(k).lower() in text for k in kwa if isinstance(k, (str, int, float))):
                return False

        rca = match.get("rss_category_contains_any")
        if isinstance(rca, list) and rca:
            rc_low = rss_category.lower()
            if not any(str(k).lower() in rc_low for k in rca if isinstance(k, (str, int, float))):
                return False

        return True

    def _strip_html(self, text: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return text
