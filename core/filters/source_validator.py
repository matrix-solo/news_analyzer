#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信源校验器
第一步：信源白名单校验
第二步：可信度校验
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import yaml

project_root = Path(__file__).parent.parent.parent


@dataclass
class ValidationResult:
    """校验结果"""
    passed: bool
    source_name: str
    step: str
    reason: str = ""
    credibility: str = ""
    source_type: str = ""
    category: str = ""


class SourceValidator:
    """信源校验器 - 白名单 + 可信度"""
    
    VALID_CREDIBILITY = ['高', '中高']
    
    AUTHORITY_PRIORITY = {
        'official': 1,
        'agency': 2,
        'comprehensive': 3,
        'regional': 4,
        'market': 5,
        'analytical': 6
    }
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger("SourceValidator")
        self.config_path = Path(config_path) if config_path else project_root / "sources.yaml"
        self.whitelist: Dict[str, Dict] = {}
        self._load_whitelist()
    
    def _load_whitelist(self):
        """加载白名单配置"""
        if not self.config_path.exists():
            self.logger.error(f"❌ 严重错误: 白名单配置文件不存在: {self.config_path}")
            self.logger.error(f"❌ 所有新闻将被拒绝，请检查配置文件！")
            try:
                from core.utils.heartbeat import get_heartbeat_monitor
                hb = get_heartbeat_monitor()
                hb.fail("source_validator", "白名单配置文件不存在")
            except Exception:
                pass
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            international = config.get('international', {})
            domestic = config.get('domestic', {})
            
            for category_key, sources_list in international.items():
                for source_data in sources_list:
                    name = source_data.get('name', '')
                    if name:
                        self.whitelist[name] = {
                            'name': name,
                            'type': 'international',
                            'category': category_key,
                            'credibility': source_data.get('credibility', ''),
                            'region': source_data.get('region', ''),
                            'enabled': source_data.get('enabled', True),
                            'rss_url': source_data.get('rss_url', '')
                        }
            
            for category_key, sources_list in domestic.items():
                for source_data in sources_list:
                    name = source_data.get('name', '')
                    if name:
                        self.whitelist[name] = {
                            'name': name,
                            'type': 'domestic',
                            'category': category_key,
                            'credibility': source_data.get('credibility', ''),
                            'region': source_data.get('region', ''),
                            'enabled': source_data.get('enabled', True),
                            'rss_url': source_data.get('rss_url', '')
                        }
            
            self.logger.info(f"加载白名单: {len(self.whitelist)}个信源")
            
        except yaml.YAMLError as e:
            self.logger.error(f"❌ YAML解析错误: {self.config_path}")
            self.logger.error(f"❌ 错误详情: {e}")
            self.logger.error(f"❌ 请检查YAML格式（缩进、引号、特殊字符等）")
            try:
                from core.utils.heartbeat import get_heartbeat_monitor
                hb = get_heartbeat_monitor()
                hb.fail("source_validator", f"YAML解析错误: {e}")
            except Exception:
                pass
            
        except Exception as e:
            self.logger.error(f"❌ 加载白名单失败: {type(e).__name__}: {e}")
            try:
                from core.utils.heartbeat import get_heartbeat_monitor
                hb = get_heartbeat_monitor()
                hb.fail("source_validator", f"加载失败: {e}")
            except Exception:
                pass
    
    def validate_source(self, source_name: str) -> ValidationResult:
        """
        校验信源（白名单 + 可信度）
        
        Args:
            source_name: 信源名称
        
        Returns:
            ValidationResult: 校验结果
        """
        result = self._check_whitelist(source_name)
        if not result.passed:
            return result
        
        result = self._check_credibility(source_name, result)
        return result
    
    def _check_whitelist(self, source_name: str) -> ValidationResult:
        """第一步：白名单校验"""
        if source_name in self.whitelist:
            source_info = self.whitelist[source_name]
            return ValidationResult(
                passed=True,
                source_name=source_name,
                step="whitelist",
                credibility=source_info.get('credibility', ''),
                source_type=source_info.get('type', ''),
                category=source_info.get('category', '')
            )
        
        self.logger.warning(f"非白名单信源: {source_name}")
        return ValidationResult(
            passed=False,
            source_name=source_name,
            step="whitelist",
            reason="非白名单信源"
        )
    
    def _check_credibility(self, source_name: str, result: ValidationResult) -> ValidationResult:
        """第二步：可信度校验"""
        source_info = self.whitelist.get(source_name, {})
        credibility = source_info.get('credibility', '')
        
        if credibility in self.VALID_CREDIBILITY:
            result.credibility = credibility
            return result
        
        self.logger.warning(f"可信度不达标: {source_name} (credibility={credibility})")
        return ValidationResult(
            passed=False,
            source_name=source_name,
            step="credibility",
            reason=f"可信度不达标: {credibility}"
        )
    
    def get_source_info(self, source_name: str) -> Optional[Dict]:
        """获取信源信息"""
        return self.whitelist.get(source_name)
    
    def get_authority_priority(self, source_name: str) -> int:
        """获取信源权威优先级（数字越小越优先）"""
        source_info = self.whitelist.get(source_name)
        if not source_info:
            return 999
        
        category = source_info.get('category', '')
        return self.AUTHORITY_PRIORITY.get(category, 999)
    
    def is_official_source(self, source_name: str) -> bool:
        """判断是否为官媒"""
        source_info = self.whitelist.get(source_name)
        if not source_info:
            return False
        return source_info.get('category') == 'official'
    
    def is_agency_source(self, source_name: str) -> bool:
        """判断是否为通讯社"""
        source_info = self.whitelist.get(source_name)
        if not source_info:
            return False
        return source_info.get('category') == 'agency'
    
    def get_fact_source_type(self, source_name: str) -> str:
        """获取事实源类型"""
        source_info = self.whitelist.get(source_name)
        if not source_info:
            return "unknown"
        
        category = source_info.get('category', '')
        
        if category == 'official':
            return "中央媒体"
        elif category == 'agency':
            return "通讯社"
        else:
            return "权威第三方"
    
    def get_region_tag(self, source_name: str) -> str:
        """获取地域标签"""
        source_info = self.whitelist.get(source_name)
        if not source_info:
            return "unknown"
        
        source_type = source_info.get('type', '')
        if source_type == 'domestic':
            return "国内"
        else:
            region = source_info.get('region', '')
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
    
    def list_whitelist(self) -> List[str]:
        """列出所有白名单信源"""
        return list(self.whitelist.keys())
