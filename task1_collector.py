#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

任务1:高频新闻采集任务

触发:每天3次(07:00、15:00、23:00)

流程:采集 → 基础过滤 → AI校验 → 存入数据库(事务安全)

改进点:

1. 使用批量查询优化N+1问题

2. 使用事务保证原子性

3. 批量插入提高性能

"""

import sys

import os

import logging

import hashlib

import json

from pathlib import Path

from datetime import datetime, timedelta

from typing import List, Dict, Any, Set, Optional

from dotenv import load_dotenv

# 加载环境变量

project_root = Path(__file__).parent

load_dotenv(project_root / '.env')

sys.path.insert(0, str(project_root))

from core.config import get_current_date, get_project_root

PROJECT_ROOT = get_project_root()

from core.collector import RSSSourceManager, UnifiedRSSCollector

from core.filters import SourceValidator

from core.storage.database import NewsDatabase, NewsData

from core.processor.ai_fallback_extractor import AIFallbackExtractor

from core.processor.content_parser import RuleBasedParser

from core.processor import FieldNormalizer, LightweightClassifier, CombinedProcessor, HeatProcessor, DataValidator

from core.utils.source_scorer import get_source_score

from core.utils.task_lock import task_lock

from core.utils.heartbeat import get_heartbeat_monitor

from core.utils.incremental_tracker import get_incremental_tracker

from core.utils.workflow_timer import WorkflowTimer

from core.utils.defaults import DefaultValues

_log_dir = Path(PROJECT_ROOT) / 'logs'

_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(

    level=logging.INFO,

    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    handlers=[

        logging.StreamHandler(),

        logging.FileHandler(

            _log_dir / f'task1_collect_{datetime.now().strftime("%Y-%m-%d")}.log',

            encoding='utf-8'

        )

    ]

)

logger = logging.getLogger("Task1Collector")

# === 废弃字段/表警告 ===
# 以下字段已废弃，禁止在代码中引用或引入：
# - score, score_timeliness, score_importance, score_credibility, score_impact
# - source_reliability_score
# 如需评分相关功能，请使用：final_score, heat_score, influence_score, value_score, source_score
# === 废弃字段警告 ===

# === 废弃表警告 ===
# rejected_news 表已废弃，禁止在代码中写入：
# - 该表无写入代码，历史数据来源不明
# - 对核心目的（新闻采集→AI处理→报告生成）无实际用途
# - 如需审计功能，请使用日志记录
# === 废弃表警告 ===

class Task1NewsCollector:

    """任务1:高频新闻采集器(优化版)"""

    MIN_CONTENT_LENGTH = 50

    MAX_PER_SOURCE = 10

    def __init__(self):

        self.rss_collector = UnifiedRSSCollector(incremental_mode=False)

        self.source_validator = SourceValidator()

        self.db = NewsDatabase()

        self.rule_parser = RuleBasedParser()

        self.ai_fallback = AIFallbackExtractor()

        self.incremental_tracker = get_incremental_tracker()

        # 新增模块

        self.field_normalizer = FieldNormalizer()

        self.lightweight_classifier = LightweightClassifier()

        self.combined_processor = CombinedProcessor()

        self.heat_processor = HeatProcessor()

        self.data_validator = DataValidator(ai_provider=self._ai_remediation_call)

        from core.config.manager import get_config_manager
        config_manager = get_config_manager()
        ai_config = config_manager.get('ai_processing', {})
        self.ai_batch_size = int(os.getenv("AI_BATCH_SIZE", str(ai_config.get('batch_size', 4))))
        self.ai_max_retry = int(os.getenv("AI_MAX_RETRY", str(ai_config.get('max_retry', 1))))
        self.ai_timeout = int(os.getenv("AI_TIMEOUT", str(ai_config.get('timeout', 30))))

        self.enable_incremental = os.getenv("ENABLE_INCREMENTAL_COLLECTION", "true").lower() in {"1", "true", "yes"}

        self.stats = {

            'total_collected': 0,

            'whitelist_passed': 0,

            'credibility_passed': 0,

            'history_passed': 0,

            'content_passed': 0,

            'ai_passed': 0,

            'stored': 0,

            'incremental_filtered': 0,

            'remedial_count': 0,

            'ai_batch_success': 0,

            'ai_batch_failed': 0,

            'ai_retry_success': 0,

            'ai_retry_failed': 0,

            'embedding_generated': 0,

            # P-11 新增：AI补救统计
            'ai_remediation_success': 0,

            'ai_remediation_failed': 0,

        }

    @staticmethod
    def _resolve_field_with_priority(field_name: str, sources: dict, default=None):
        """
        按优先级解析字段值
        
        P-09 修复：统一字段来源优先级逻辑
        
        Args:
            field_name: 字段名
            sources: 来源字典，按优先级排序 {'ai_output': ..., 'classifier': ..., 'rule': ..., 'default': ...}
            default: 默认值
            
        Returns:
            解析后的字段值
        """
        priority_order = ['ai_output', 'classifier', 'rule', 'fallback']
        for source in priority_order:
            if source in sources:
                value = sources[source]
                if value is not None and value != '' and value != []:
                    return value
        return default

    def _ai_remediation_call(self, prompt: str) -> str:
        """
        AI 补救调用函数，供 DataValidator 使用

        Args:
            prompt: 补救 prompt

        Returns:
            AI 返回的文本
        """
        try:
            provider = self.combined_processor._provider
            if provider:
                response = provider.chat(
                    [{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return response
        except Exception as e:
            logger.error(f"AI 补救调用失败: {e}")
        return "{}"

    def _init_hotboard_cache(self):
        try:
            from core.utils.hotboard_manager import get_hotboard_manager, _CACHE_TTL_HOURS
            manager = get_hotboard_manager()
            cache = manager.get_cache()
            if cache:
                logger.info(f"热榜缓存初始化完成: {len(cache.items)} 条, TTL {_CACHE_TTL_HOURS}h")
            else:
                logger.warning("热榜缓存初始化失败,热度评分将使用默认值")
        except Exception as e:
            logger.warning(f"热榜缓存初始化失败(忽略): {e}")

    def run(self, max_per_source: int = None) -> Dict[str, Any]:

        """

        执行采集任务

        Args:

            max_per_source: 每个RSS源最大条目数(默认使用常量)

        """

        max_per_source = max_per_source or self.MAX_PER_SOURCE

        _hb = get_heartbeat_monitor()

        _hb.start("collect", "新闻采集任务开始")

        _timer = WorkflowTimer("task1_collect").start()

        logger.info("=" * 70)

        logger.info("📡 任务1:高频新闻采集任务")

        logger.info(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        logger.info("=" * 70)

        with _timer.stage("热榜缓存初始化"):

            self._init_hotboard_cache()

        # ========== 阶段1:全信源新闻采集 ==========

        _hb.update("collect", 5, "阶段1:全信源新闻采集")

        logger.info("")

        logger.info("📥 阶段1:全信源新闻采集")

        logger.info("-" * 50)

        with _timer.stage("全信源新闻采集"):

            all_news = self._collect_from_sources(max_per_source)

        self.stats['total_collected'] = len(all_news)

        logger.info(f"采集完成: {len(all_news)} 条新闻")

        # ========== 阶段2:接口解析(字段标准化) ==========

        _hb.update("collect", 15, "阶段2:接口解析")

        logger.info("")

        logger.info("🔧 阶段2:接口解析(字段标准化)")

        logger.info("-" * 50)

        with _timer.stage("字段标准化"):

            normalized_news = []

            for news in all_news:

                normalized = self.field_normalizer.normalize_fields(news)

                for key, value in news.items():

                    if key not in normalized:

                        normalized[key] = value

                normalized_news.append(normalized)

        logger.info(f"字段标准化完成: {len(normalized_news)} 条新闻")

        # ========== 阶段3:存储原始数据 ==========

        _hb.update("collect", 25, "阶段3:存储原始数据")

        logger.info("")

        logger.info("💾 阶段3:存储原始数据")

        logger.info("-" * 50)

        with _timer.stage("存储原始数据"):

            self._save_raw_news(normalized_news)

        logger.info(f"原始数据存储完成: {len(normalized_news)} 条新闻")

        # ========== 阶段4:轻量级初筛 ==========

        _hb.update("collect", 35, "阶段4:轻量级初筛")

        logger.info("")

        logger.info("⚡ 阶段4:轻量级初筛(信源赋分、快速分类)")

        logger.info("-" * 50)

        with _timer.stage("轻量级分类"):

            classified_news = self.lightweight_classifier.classify_batch(normalized_news)

            # 将分类结果合并回新闻数据：仅在无规则层 domain 时采用

            for news, cls in zip(normalized_news, classified_news):

                # P-03 修复：存储分类置信度
                news['classification_confidence'] = cls.get('confidence', 0.5)
                
                if not news.get('domain') and cls.get('confidence', 0) >= 0.7:
                    news['domain'] = cls['domain']

        logger.info(f"轻量级分类完成: {len(normalized_news)} 条新闻")

        # ========== 阶段5:基础三层过滤 ==========

        _hb.update("collect", 45, "阶段5:基础三层过滤")

        logger.info("")

        logger.info("🔍 阶段5:基础三层过滤")

        logger.info("-" * 50)

        with _timer.stage("基础三层过滤"):

            passed_news = self._apply_basic_filters(normalized_news)

        # ========== 阶段6:三阶段合并处理 ==========

        _hb.update("collect", 55, "阶段6:三阶段合并处理")

        logger.info("")

        logger.info("🤖 阶段6:三阶段合并处理(翻译、摘要、5W1H提取)")

        logger.info("-" * 50)

        logger.info(f"批量处理配置: 批次大小={self.ai_batch_size}, 最大重试={self.ai_max_retry}")

        with _timer.stage("三阶段合并处理(AI)"):

            processed_news = []

            failed_news = []

            batch_size = self.ai_batch_size

            total_batches = (len(passed_news) + batch_size - 1) // batch_size

            for batch_idx in range(0, len(passed_news), batch_size):

                batch = passed_news[batch_idx:batch_idx + batch_size]

                batch_num = batch_idx // batch_size + 1

                logger.info(f"批量处理 [{batch_num}/{total_batches}]: {len(batch)} 条新闻")

                batch_results = self.combined_processor.process_batch(batch)

                for news, result, accuracy in batch_results:

                    if result and result.get('translation'):
                        news['combined_result'] = result
                        news['accuracy_score'] = accuracy
                        processed_news.append(news)

                        self.stats['ai_batch_success'] += 1

                    else:

                        failed_news.append(news)

                        self.stats['ai_batch_failed'] += 1

            logger.info(f"批量处理完成: {len(processed_news)} 成功, {len(failed_news)} 失败")

            if failed_news and self.ai_max_retry > 0:

                logger.info(f"🔄 重试阶段: 对 {len(failed_news)} 条失败新闻进行单条重试...")

                retry_success = 0

                final_failed = []

                for news in failed_news:

                    try:

                        result, accuracy = self.combined_processor.process_news(news)

                        if result and result.get('translation'):
                            news['combined_result'] = result
                            news['accuracy_score'] = accuracy
                            processed_news.append(news)

                            retry_success += 1

                            self.stats['ai_retry_success'] += 1

                        else:

                            final_failed.append(news)

                            self.stats['ai_retry_failed'] += 1

                    except Exception as e:

                        logger.debug(f"重试失败: {news.get('title', '')[:40]}... - {e}")

                        final_failed.append(news)

                        self.stats['ai_retry_failed'] += 1

                logger.info(f"重试完成: {retry_success} 成功, {len(final_failed)} 最终失败")

                if final_failed:

                    logger.debug(f"跳过 {len(final_failed)} 条无法解析的新闻")

                    for news in final_failed:

                        logger.debug(f"  跳过: {news.get('title', '')[:50]}...")

        logger.info(f"三阶段合并处理完成: {len(processed_news)} 条新闻")

        logger.info(f"AI处理统计: 批量成功={self.stats['ai_batch_success']}, 批量失败={self.stats['ai_batch_failed']}, 重试成功={self.stats['ai_retry_success']}, 重试失败={self.stats['ai_retry_failed']}")

        # ========== 阶段7:数据完整性校验 ==========
        _hb.update("collect", 60, "阶段7:数据完整性校验")
        logger.info("")
        logger.info("✅ 阶段7:数据完整性校验")
        logger.info("-" * 50)

        with _timer.stage("数据完整性校验"):
            passed_news = []
            force_stored_news = []

            for news in processed_news:
                validation_result = self.data_validator.validate_combined_result(news, news.get('combined_result', {}))
                news['validation_result'] = validation_result

                # P-11修复：使用补救结果更新 combined_result
                if validation_result['status'] == 'remediated':
                    remediation = validation_result.get('remediation', {})
                    if remediation:
                        news['combined_result'] = remediation
                        news['remediation_applied'] = True
                        news['remediation_fields'] = list(validation_result.get('results', {}).keys())
                        self.stats['ai_remediation_success'] = self.stats.get('ai_remediation_success', 0) + 1
                    else:
                        self.stats['ai_remediation_failed'] = self.stats.get('ai_remediation_failed', 0) + 1
                else:
                    self.stats['ai_remediation_failed'] = self.stats.get('ai_remediation_failed', 0) + 1

                if validation_result['status'] in ['valid', 'remediated', 'default_filled']:
                    news['combined_processing_status'] = 'passed'
                    passed_news.append(news)
                else:
                    news['combined_processing_status'] = 'force_stored'
                    news['repair_count'] = 0
                    self._fill_default_values(news)
                    force_stored_news.append(news)
                    logger.warning(f"数据校验未通过，标记为force_stored: {news.get('title', '')[:30]}...")

        logger.info(f"数据完整性校验完成: passed={len(passed_news)}, force_stored={len(force_stored_news)}")

        # ========== 阶段8:向量化检测与生成 ==========
        _hb.update("collect", 70, "阶段8:向量化检测与生成")
        logger.info("")
        logger.info("🔢 阶段8:向量化检测与生成")
        logger.info("-" * 50)

        with _timer.stage("向量化检测与生成"):
            all_news_for_embedding = passed_news + force_stored_news
            news_needing_embedding = [n for n in all_news_for_embedding if n.get('embedding') is None]

            logger.info(f"需要生成向量的新闻: {len(news_needing_embedding)} 条")

            if news_needing_embedding:
                try:
                    from core.processor.history_relation_engine_bge3 import _get_model
                    model = _get_model()

                    if model:
                        titles_for_embedding = []
                        for news in news_needing_embedding:
                            title = (news.get('combined_result', {}).get('translation') or news.get('translated_title') or news.get('title', '')).strip()
                            titles_for_embedding.append(title if title else " ")

                        embedding_vecs = model.encode(titles_for_embedding, normalize_embeddings=True, show_progress_bar=False)

                        for i, news in enumerate(news_needing_embedding):
                            news['embedding'] = embedding_vecs[i].astype(np.float32)

                        logger.info(f"向量生成完成: {len(news_needing_embedding)} 条")
                        self.stats['embedding_generated'] = len(news_needing_embedding)
                    else:
                        logger.warning("BGE3模型不可用，跳过向量生成")
                        self.stats['embedding_generated'] = 0

                except Exception as e:
                    logger.warning(f"向量生成失败: {e}")
                    self.stats['embedding_generated'] = 0

        # ========== 阶段9:热榜提取与热度评分(仅passed数据) ==========
        _hb.update("collect", 75, "阶段9:热榜提取与热度评分")
        logger.info("")
        logger.info("🔥 阶段9:热榜提取与热度评分")
        logger.info("-" * 50)

        with _timer.stage("热度评分"):
            if passed_news:
                heat_scores = self.heat_processor.calculate_batch(passed_news)
                for news, score in zip(passed_news, heat_scores):
                    news['heat_score'] = score
                logger.info(f"热度评分完成: {len(passed_news)} 条passed新闻")

        # ========== 阶段10:批量存入数据库 ==========
        _hb.update("collect", 85, "阶段10:批量存入数据库")
        logger.info("")
        logger.info("💾 阶段10:批量存入数据库")
        logger.info("-" * 50)

        with _timer.stage("批量存入数据库"):
            all_validated_news = passed_news + force_stored_news
            if all_validated_news:
                stored = self._store_batch_to_database(all_validated_news)
                self.stats['stored'] = stored

                # 关键任务后备份(可通过环境变量关闭)

                enable_backup = os.getenv("ENABLE_DB_BACKUP", "true").lower() in {"1", "true", "yes"}

                if enable_backup:

                    try:

                        self.db.backup_database()

                    except Exception as e:

                        logger.warning(f"数据库备份失败(忽略): {e}")

            else:

                logger.info("没有通过校验的新闻,跳过存储")

        # ========== 阶段11:修复 force_stored 数据 ==========

        _hb.update("collect", 95, "阶段11:修复force_stored数据")
        logger.info("")
        logger.info("🔧 阶段11:修复force_stored数据")
        logger.info("-" * 50)
        with _timer.stage("修复force_stored数据"):
            self._reprocess_pending_news()

        # ========== 任务完成/打印统计 ==========

        _hb.update("collect", 100, "任务完成")
        self._print_summary()
        self.combined_processor.save_summary_log()
        _hb.success("collect", f"采集完成,存储 {self.stats['stored']} 条新闻")

        _timer.finish(status="success", summary=self.stats)

        return {

            'success': True,

            'stats': self.stats

        }

    def _collect_from_sources(self, max_per_source: int) -> List[Dict]:

        """从所有信源采集新闻(支持增量采集)"""

        all_news = []

        sources = self.rss_collector.source_manager.get_enabled_sources()

        logger.info(f"启用的信源: {len(sources)} 个")

        if self.enable_incremental:

            logger.info("增量采集模式已启用")

        for source in sources:

            try:

                source_max = max_per_source

                if self.enable_incremental:

                    source_max = self.incremental_tracker.get_suggested_max_items(source.name, max_per_source)

                feed = self.rss_collector.fetch_feed(source)

                if feed and feed.items:

                    cutoff_date = None

                    if self.enable_incremental:

                        # 统一使用智能回溯(已与全局采样频率联动)

                        cutoff_date = self.incremental_tracker.get_intelligent_cutoff_date(source.name)

                        # 记录中断诊断信息(仅用于日志)

                        downtime_hours = self.incremental_tracker.get_downtime_hours(source.name)

                        if downtime_hours > 1:

                            interruption_type = self.incremental_tracker.diagnose_interruption_type(source.name)

                            logger.debug(

                                f"中断类型 {source.name}: {interruption_type} (中断{downtime_hours:.1f}h)"

                            )

                        # 检查中断风险

                        if downtime_hours > 6:

                            logger.warning(f"高风险源: {source.name} 中断{downtime_hours:.1f}小时,可能丢失新闻")

                    source_news_count = 0

                    latest_pub_date = None

                    for item in feed.items[:source_max]:

                        if self.enable_incremental and cutoff_date and item.pub_date:

                            item_pub_date = item.pub_date
                            if item_pub_date.tzinfo is not None:
                                item_pub_date = item_pub_date.replace(tzinfo=None)

                            if item_pub_date < cutoff_date:

                                self.stats['incremental_filtered'] += 1

                                continue

                        if item.pub_date:

                            item_pub_date = item.pub_date
                            if item_pub_date.tzinfo is not None:
                                item_pub_date = item_pub_date.replace(tzinfo=None)

                            if latest_pub_date is None or item_pub_date > latest_pub_date:

                                latest_pub_date = item_pub_date

                        news = {

                            'title': item.title,

                            'link': item.link,

                            'content': item.content or item.description,

                            'source_name': source.name,

                            'source_type': source.type,

                            'category': source.category,

                            'credibility': source.credibility,

                            'pub_date': item.pub_date.isoformat() if item.pub_date else '',

                            'used_backup': getattr(feed, 'used_backup', False),

                            'used_source_type': getattr(feed, 'used_source_type', ''),

                        }

                        try:

                            parse_res = self.rule_parser.parse(news)

                            if parse_res.content:

                                news["content"] = parse_res.content

                            news["rule_parse"] = {

                                "domain": parse_res.domain,

                                "tags": parse_res.tags,

                                "confidence": {

                                    "domain": parse_res.confidence.domain,

                                    "tags": parse_res.confidence.tags,

                                },

                                "matched_rules": parse_res.matched_rules,

                                "extraction_method": parse_res.extraction_method,

                            }

                        except Exception as e:

                            logger.debug(f"规则解析失败(忽略): {source.name} - {e}")

                        all_news.append(news)

                        source_news_count += 1

                    if self.enable_incremental and latest_pub_date:
                        latest_pub_date_str = latest_pub_date.isoformat() if hasattr(latest_pub_date, 'isoformat') else str(latest_pub_date)
                        self.incremental_tracker.update_state(source.name, latest_pub_date_str, source_news_count)

                    # 遗漏检测(返回检测结果)

                    gap_result = self._detect_gap_for_source(source.name, feed, source_news_count)

                    # 显示智能兜底检测日志

                    if gap_result['has_gap']:

                        logger.warning(f"⚠️  智能兜底检测 [{source.name}]: {gap_result.get('suggestion', '')}")

                    else:

                        logger.info(f"✅ 智能兜底检测 [{source.name}]: 无遗漏,采集正常")

                    # 如果检测到遗漏,尽最大努力补救

                    if gap_result['has_gap'] and gap_result['gap_type'] == 'rss_rollover':

                        logger.warning(f"🔧 触发补救采集 [{source.name}]: {gap_result.get('suggestion', '')}")

                        # 记录补救前的遗漏分数

                        gap_score_before = gap_result.get('gap_score', 0)

                        # 执行补救采集

                        remedial_news = self._补救采集(source, gap_result)

                        # 合并补救新闻(去重 - 当前批次 + 数据库)

                        if remedial_news:

                            existing_links = {n['link'] for n in all_news}

                            # C-11: 检查数据库是否已存在
                            remedial_ids = [self._generate_news_id(n) for n in remedial_news]
                            existing_in_db = self.db.filter_processed_ids(remedial_ids)

                            merged_count = 0
                            for news in remedial_news:

                                news_id = self._generate_news_id(news)
                                if news['link'] not in existing_links and news_id not in existing_in_db:

                                    news['news_id'] = news_id
                                    all_news.append(news)

                                    existing_links.add(news['link'])
                                    merged_count += 1

                            logger.info(f"补救采集 [{source.name}]: 补救 {len(remedial_news)} 条, 合并 {merged_count} 条 (数据库已存在 {len(existing_in_db)} 条)")

                        # 补救效果验证:重新检测遗漏

                        logger.info(f"🔍 补救效果验证 [{source.name}]: 重新检测遗漏...")

                        # 重新获取RSS Feed(补救采集可能已更新)

                        feed_after = self.rss_collector.fetch_feed(source)

                        if feed_after and feed_after.items:

                            # 重新检测

                            gap_result_after = self._detect_gap_for_source(

                                source.name, 

                                feed_after, 

                                source_news_count + len(remedial_news)

                            )

                            # 判断补救效果

                            if not gap_result_after['has_gap']:

                                logger.info(f"✅ 补救成功 [{source.name}]: 遗漏已完全补救")

                                if 'remedial_success' not in self.stats:

                                    self.stats['remedial_success'] = 0

                                self.stats['remedial_success'] += 1

                            else:

                                gap_score_after = gap_result_after.get('gap_score', 0)

                                improvement = gap_score_before - gap_score_after

                                if improvement > 0:

                                    logger.warning(

                                        f"⚠️  部分补救 [{source.name}]: "

                                        f"遗漏分数 {gap_score_before:.2f} → {gap_score_after:.2f} "

                                        f"(改善 {improvement:.2f})"

                                    )

                                    if 'remedial_partial' not in self.stats:

                                        self.stats['remedial_partial'] = 0

                                    self.stats['remedial_partial'] += 1

                                else:

                                    logger.error(

                                        f"❌ 补救失败 [{source.name}]: "

                                        f"遗漏分数未改善 ({gap_score_after:.2f}),可能需要人工介入"

                                    )

                                    if 'remedial_failed' not in self.stats:

                                        self.stats['remedial_failed'] = 0

                                    self.stats['remedial_failed'] += 1

                        else:

                            logger.warning(f"⚠️  补救验证失败 [{source.name}]: 无法重新获取RSS Feed")

            except Exception as e:

                logger.warning(f"采集信源失败 {source.name}: {e}")

        if self.stats['incremental_filtered'] > 0:

            logger.info(f"增量采集过滤: {self.stats['incremental_filtered']} 条旧新闻")

        return all_news

    def _fill_default_values(self, news: dict):
        """为缺失字段填充默认值（使用统一默认值常量）"""
        # P-12 修复：使用统一默认值
        if not news.get('influence_score'):
            news['influence_score'] = DefaultValues.SCORE_DEFAULT
        if not news.get('value_score'):
            news['value_score'] = DefaultValues.SCORE_DEFAULT
        if not news.get('source_score'):
            news['source_score'] = DefaultValues.SCORE_DEFAULT
        if not news.get('heat_score'):
            news['heat_score'] = DefaultValues.SCORE_DEFAULT

        if not news.get('final_score') or news.get('final_score') == 0:
            si = news.get('influence_score', DefaultValues.SCORE_DEFAULT)
            v = news.get('value_score', DefaultValues.SCORE_DEFAULT)
            sc = news.get('source_score', DefaultValues.SCORE_DEFAULT)
            h = news.get('heat_score', DefaultValues.SCORE_DEFAULT)
            news['final_score'] = sc * 0.25 + si * 0.25 + v * 0.25 + h * 0.25

        # P-12 修复：使用统一文本默认值
        if not news.get('who'):
            news['who'] = DefaultValues.TEXT_UNKNOWN
        if not news.get('what'):
            news['what'] = DefaultValues.TEXT_UNKNOWN
        if not news.get('when_time'):
            news['when_time'] = news.get('pub_date', DefaultValues.TEXT_UNKNOWN)
        if not news.get('where_place'):
            news['where_place'] = DefaultValues.TEXT_UNKNOWN
        if not news.get('why'):
            news['why'] = DefaultValues.TEXT_UNKNOWN
        if not news.get('how'):
            news['how'] = DefaultValues.TEXT_UNKNOWN

    def _reprocess_pending_news(self):
        """
        force_stored 修复机制已简化：force_stored 数据不会再被自动修复

        设计原则（第一性原理）：
        - 每条数据最多调用1次额外AI补救
        - 不做多轮修复循环，减少AI调用成本
        - force_stored 数据保留但标记，在查询时降权处理

        如果需要重新处理，请使用补救采集或手动重新导入数据
        """
        logger.info("force_stored 修复机制已简化，不再进行自动修复")

    def _save_raw_news(self, normalized_news: List[Dict]) -> Dict[str, int]:
        """
        保存标准化后的新闻数据到 raw_news 表

        Args:
            normalized_news: 标准化后的新闻列表

        Returns:
            {news_id: raw_news_id} 映射
        """
        if not normalized_news:
            return {}

        raw_items = []
        for news in normalized_news:
            news_id = self._generate_news_id(news)
            news['news_id'] = news_id

            raw_items.append({
                'news_id': news_id,
                'raw_json': json.dumps(news, ensure_ascii=False),
                'source_name': news.get('source') or news.get('source_name')
            })

        try:
            id_mapping = self.db.insert_raw_news_batch(raw_items)
            for news in normalized_news:
                news['raw_news_id'] = id_mapping.get(news['news_id'])
            logger.info(f"原始数据保存: {len(id_mapping)}/{len(normalized_news)} 条")
            return id_mapping
        except Exception as e:
            logger.error(f"保存原始数据失败: {e}")
            return {}

    def _apply_basic_filters(self, all_news: List[Dict]) -> List[Dict]:

        """应用基础过滤器"""

        # 过滤1: 白名单+可信度校验（SourceValidator 已包含可信度校验）
        # F-06: 移除重复的可信度校验，统一在 SourceValidator 中处理

        passed_news = []

        for news in all_news:

            result = self.source_validator.validate_source(news['source_name'])

            if result.passed:

                passed_news.append(news)

        self.stats['whitelist_passed'] = len(passed_news)

        logger.info(f"过滤1-白名单+可信度: {len(all_news)} → {len(passed_news)}")

        # 过滤2: 历史去重(优化版 - 批量查询)

        all_news = passed_news

        passed_news = []

        # 使用已有的 news_id（已在 _save_raw_news 中设置）

        news_id_map = {}

        for news in all_news:

            news_id = news.get('news_id') or self._generate_news_id(news)

            news['news_id'] = news_id

            news_id_map[news_id] = news

        # 内容去重统计

        content_dup_count = len(all_news) - len(news_id_map)

        # 批量查询哪些ID已处理(优化N+1)

        all_ids = list(news_id_map.keys())

        processed_ids = self.db.filter_processed_ids(all_ids)

        for news_id, news in news_id_map.items():

            if news_id not in processed_ids:

                passed_news.append(news)

        self.stats['history_passed'] = len(passed_news)

        logger.info(f"过滤2-历史去重: {len(all_news)} → {len(passed_news)} (内容重复: {content_dup_count}, 已处理: {len(processed_ids)})")

        # 过滤3: 垃圾内容清理（精准版）
        # 第一性原理：只过滤"明确无价值"的内容，避免误杀
        all_news = passed_news
        passed_news = []
        spam_stats = {'test_content': 0, 'code_injection': 0, 'ad_spam': 0}
        
        for news in all_news:
            spam_type = self._detect_spam_type(news)
            if spam_type:
                spam_stats[spam_type] = spam_stats.get(spam_type, 0) + 1
                logger.debug(f"垃圾过滤: [{spam_type}] {news.get('title', '')[:40]}...")
            else:
                passed_news.append(news)
        
        self.stats['content_passed'] = len(passed_news)
        
        spam_detail = ', '.join(f"{k}:{v}" for k, v in spam_stats.items() if v > 0)
        logger.info(f"过滤3-垃圾清理: {len(all_news)} → {len(passed_news)} ({spam_detail})")

        return passed_news
    def _detect_gap_for_source(self, source_name: str, feed, collected_count: int) -> Dict[str, Any]:

        """

        检测源的遗漏情况(增强版 - 返回检测结果)

        基于RSS滚动边界检测:

        - 比较数据库中该源最新新闻时间

        - 比较RSS feed中最早新闻时间

        - 如果数据库最新 < RSS最早,说明存在遗漏

        Args:

            source_name: 源名称

            feed: RSS Feed对象

            collected_count: 本次采集数量

        Returns:

            检测结果字典,包含:

            - has_gap: 是否存在遗漏

            - gap_type: 遗漏类型

            - gap_score: 遗漏分数

            - suggestion: 补救建议

            - db_latest: 数据库最新时间

            - rss_earliest: RSS最早时间

        """

        default_result = {

            'has_gap': False,

            'gap_type': 'none',

            'gap_score': 0,

            'suggestion': '',

            'db_latest': None,

            'rss_earliest': None

        }

        try:

            from core.utils.collection_config import get_collection_config_manager

            config_manager = get_collection_config_manager()

            db_latest = self.db.get_source_latest_pub_date(source_name)

            rss_earliest = feed.get_earliest_pub_date()

            rss_latest = feed.get_latest_pub_date()

            result = config_manager.detect_gap(

                source_name=source_name,

                collected_count=collected_count,

                db_latest_pub_date=db_latest,

                rss_earliest_pub_date=rss_earliest,

                rss_latest_pub_date=rss_latest

            )

            # 增强日志输出

            if result['has_gap']:

                logger.warning(f"⚠️  遗漏检测 [{source_name}]: {result['suggestion']}")

            else:

                logger.debug(f"遗漏检测 [{source_name}]: {result['suggestion']}")

            return result

        except Exception as e:

            logger.debug(f"遗漏检测失败 [{source_name}]: {e}")

            return default_result

    def _补救采集(self, source, gap_result: Dict[str, Any], max_items: int = 100) -> List[Dict]:

        """

        尽最大努力补救遗漏的新闻

        补救策略:

        1. 扩大回溯时间到RSS滚动限制

        2. 增加采集条目数

        3. 记录补救统计

        Args:

            source: RSS源对象

            gap_result: 遗漏检测结果

            max_items: 最大补救条目数

        Returns:

            补救的新闻列表

        """

        补救新闻 = []

        try:

            from core.utils.collection_config import get_collection_config_manager

            config_manager = get_collection_config_manager()

            config = config_manager.get_source_config(source.name)

            # 策略1:扩大回溯时间到RSS滚动限制

            rss_rollover_hours = config.rss_rollover_hours

            补救截止时间 = datetime.now() - timedelta(hours=rss_rollover_hours)

            logger.info(f"🔧 补救采集 [{source.name}]: 扩大回溯至 {rss_rollover_hours}小时")

            # 重新获取RSS Feed

            feed = self.rss_collector.fetch_feed(source)

            if not feed or not feed.items:

                logger.warning(f"补救采集失败 [{source.name}]: 无法获取RSS Feed")

                return 补救新闻

            # 采集补救新闻

            for item in feed.items[:max_items]:

                if item.pub_date and item.pub_date.replace(tzinfo=None) < 补救截止时间:

                    continue

                news = {

                    'title': item.title,

                    'link': item.link,

                    'content': item.content or item.description,

                    'source_name': source.name,

                    'source_type': source.type,

                    'category': source.category,

                    'credibility': source.credibility,

                    'pub_date': item.pub_date.isoformat() if item.pub_date else '',

                    'used_backup': getattr(feed, 'used_backup', False),

                    'used_source_type': getattr(feed, 'used_source_type', ''),

                    'is_remedial': True,  # 标记为补救采集

                }

                # 规则解析

                try:

                    parse_res = self.rule_parser.parse(news)

                    if parse_res.content:

                        news["content"] = parse_res.content

                    news["rule_parse"] = {

                        "domain": parse_res.domain,

                        "tags": parse_res.tags,

                        "confidence": {

                            "domain": parse_res.confidence.domain,

                            "tags": parse_res.confidence.tags,

                        },

                        "matched_rules": parse_res.matched_rules,

                        "extraction_method": parse_res.extraction_method,

                    }

                except Exception as e:

                    logger.debug(f"补救新闻规则解析失败(忽略): {source.name} - {e}")

                补救新闻.append(news)

            logger.info(f"补救采集完成 [{source.name}]: 补救 {len(补救新闻)} 条新闻")

            # 更新统计

            if 'remedial_count' not in self.stats:

                self.stats['remedial_count'] = 0

            self.stats['remedial_count'] += len(补救新闻)

        except Exception as e:

            logger.error(f"补救采集异常 [{source.name}]: {e}")

        return 补救新闻

    def _store_batch_to_database(self, news_list: List[Dict]) -> int:

        """批量存入数据库(事务安全 + 向量持久化 + 存储前去重)"""

        if not news_list:
            return 0

        # C-09: 存储前去重检查
        all_ids = [n.get('news_id') for n in news_list if n.get('news_id')]
        if all_ids:
            existing_ids = self.db.filter_processed_ids(all_ids)
            news_list = [n for n in news_list if n.get('news_id') not in existing_ids]
            if len(existing_ids) > 0:
                logger.info(f"存储前去重: 过滤 {len(existing_ids)} 条已存在数据")

        if not news_list:
            logger.info("存储前去重: 无新数据需要存储")
            return 0

        news_data_list = []

        now_iso = datetime.now().isoformat()

        for news in news_list:

            w5h1 = news.get('fact_check', {}).get('w5h1_analysis', {})

            rule_parse = news.get('rule_parse') or {}

            # 解析方法:优先取规则层标记,AI兜底时标记 ai_fallback,否则 rule_only

            extraction_method = rule_parse.get('extraction_method', 'unknown')

            if extraction_method == 'rule_only' and news.get('tags') and not rule_parse.get('tags'):

                extraction_method = 'ai_fallback'

            # 优先从 combined_result 获取 AI 分析结果
            combined = news.get('combined_result', {})
            
            # P-09 修复：使用统一优先级解析字段
            # 领域优先级：AI输出 > 轻量分类器 > 默认值
            domain = self._resolve_field_with_priority(
                'domain',
                {
                    'ai_output': combined.get('domain'),
                    'classifier': news.get('domain'),
                },
                default='其他'
            )
            
            # 标签优先级：AI输出 > 规则解析 > 轻量分类器
            tags = self._resolve_field_with_priority(
                'tags',
                {
                    'ai_output': combined.get('keywords'),
                    'rule': rule_parse.get('tags'),
                    'classifier': news.get('tags'),
                },
                default=[]
            )
            
            # 评分：source_score 由规则计算，influence_score 和 value_score 来自 LLM
            scoring = combined.get('scoring', {})
            source_score = get_source_score(news.get('source_name', ''))
            influence_score = self._resolve_field_with_priority(
                'influence_score',
                {
                    'ai_output': scoring.get('influence_score'),
                    'fallback': news.get('influence_score'),
                }
            )
            value_score = self._resolve_field_with_priority(
                'value_score',
                {
                    'ai_output': scoring.get('value_score'),
                    'fallback': news.get('value_score'),
                }
            )
            
            # 翻译和摘要优先级
            translated_title = self._resolve_field_with_priority(
                'translated_title',
                {
                    'ai_output': combined.get('translation'),
                    'fallback': news.get('translated_title'),
                }
            )
            summary = self._resolve_field_with_priority(
                'summary',
                {
                    'ai_output': combined.get('summary'),
                    'fallback': news.get('short_summary'),
                }
            )
            
            # 5W1H：优先 combined_result.analysis
            analysis = combined.get('analysis', {})
            who = self._resolve_field_with_priority('who', {'ai_output': analysis.get('who'), 'fallback': w5h1.get('who')})
            what = self._resolve_field_with_priority('what', {'ai_output': analysis.get('what'), 'fallback': w5h1.get('what')})
            when_time = self._resolve_field_with_priority('when', {'ai_output': analysis.get('when'), 'fallback': w5h1.get('when')})
            where_place = self._resolve_field_with_priority('where', {'ai_output': analysis.get('where'), 'fallback': w5h1.get('where')})
            why = self._resolve_field_with_priority('why', {'ai_output': analysis.get('why'), 'fallback': w5h1.get('why')})
            how = self._resolve_field_with_priority('how', {'ai_output': analysis.get('how'), 'fallback': w5h1.get('how')})

            # 构建NewsData对象

            news_data = NewsData(

                news_id=news['news_id'],

                title=news['title'],

                translated_title=translated_title,

                link=news['link'],

                source=news.get('source_type'),

                source_name=news['source_name'],

                pub_date=news.get('pub_date'),

                content=news.get('content'),

                summary=summary,

                # 5W1H

                who=who,

                what=what,

                when_time=when_time,

                where_place=where_place,

                why=why,

                how=how,

                # 分类

                domain=domain,

                tags=tags if isinstance(tags, list) else [],

                keywords=tags if isinstance(tags, list) else [],

                # 评分字段
                # 语义字段（主用）
                source_score=source_score,
                heat_score=news.get('heat_score'),
                influence_score=influence_score,
                value_score=value_score,
                final_score=news.get('final_score'),

                extraction_method=extraction_method,

                combined_processing_status=news.get('combined_processing_status'),

                validation_status=news.get('validation_result', {}).get('status'),

                raw_news_id=news.get('raw_news_id'),

                embedding=news.get('embedding'),

                accuracy_score=news.get('accuracy_score'),
                original_summary=combined.get('original_summary'),
                classification_confidence=news.get('classification_confidence'),

            )

            news_data_list.append(news_data)

        # 使用批量插入(事务安全)
        stored = self.db.insert_news_batch(news_data_list)

        # 更新原始数据状态
        for news in news_list:
            if news.get('raw_news_id'):
                self.db.update_raw_news_processed(news['news_id'], news['raw_news_id'])

        logger.info(f"批量存入数据库: {stored}/{len(news_list)} 条")

        return stored

    def _generate_news_id(self, news: Dict) -> str:

        """生成新闻唯一ID"""

        content = f"{news['title']}_{news['link']}"

        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _detect_spam_type(self, news: Dict) -> Optional[str]:
        """
        精准检测垃圾内容类型
        
        第一性原理：
        1. 只检测"明确无价值"的内容
        2. 避免误杀正常新闻（如"核武器测试"）
        3. 返回垃圾类型便于统计分析
        
        Returns:
            None: 正常内容
            str: 垃圾类型（test_content/code_injection/ad_spam）
        """
        title = (news.get('title') or '').strip()
        content = (news.get('content') or '').strip()
        title_lower = title.lower()
        content_lower = content.lower()
        
        # 1. 测试内容检测（只在标题开头匹配，避免误杀"核武器测试"）
        test_prefixes = ['test', 'demo', '测试', '示例', 'demo ']
        for prefix in test_prefixes:
            if title_lower.startswith(prefix):
                return 'test_content'
        
        # 标题过短且全是测试词
        if len(title) < 10:
            if any(word in title_lower for word in ['test', 'demo', '测试']):
                return 'test_content'
        
        # 2. 代码注入检测（网页代码片段）
        code_patterns = ['<!--', '<script', 'javascript:', 'function(', 'var ', 'document.']
        for pattern in code_patterns:
            if pattern in content_lower:
                return 'code_injection'
        
        # 3. 广告垃圾检测（标题开头匹配）
        ad_prefixes = ['广告:', '广告｜', '【广告】', '推广:', '促销:']
        for prefix in ad_prefixes:
            if title.startswith(prefix):
                return 'ad_spam'
        
        return None

    def _recheck_fallback_news(self, fallback_news: List[Dict]):

        """

        重新判断"待分类"新闻(使用高级模型)

        Args:

            fallback_news: 需要重新判断的新闻列表

        """

        if not fallback_news:

            return

        logger.info(f"开始重新判断 {len(fallback_news)} 条待分类新闻...")

        try:

            # 直接使用 AIProcessor 获取 ANALYSIS 模型(深度分析模型)

            from core.processor.ai_processor import AIProcessor

            premium_processor = AIProcessor()

            analysis_provider = premium_processor.get_provider("ANALYSIS")

            if not analysis_provider:

                logger.warning("ANALYSIS 模型不可用,使用 FILTER 模型重新判断")

                analysis_provider = premium_processor.get_provider("FILTER")

            if not analysis_provider:

                logger.error("没有可用的 AI 模型,跳过重新判断")

                return

            logger.info(f"使用高级模型: {analysis_provider.model} ({analysis_provider.provider})")

            # 逐条重新判断

            recheck_passed = 0

            recheck_failed = 0

            for news in fallback_news:

                try:

                    # 构建判断提示词

                    prompt = self._build_recheck_prompt(news)

                    messages = [{"role": "user", "content": prompt}]

                    # 调用高级模型

                    response = analysis_provider.chat(messages)

                    # 解析结果

                    result = self._parse_recheck_response(response, news)

                    if result['is_factual'] and result['w5h1_score'] >= 3:

                        # 重新判断成功,更新数据库

                        self._update_news_after_recheck_v2(news, result)

                        recheck_passed += 1

                        logger.info(f"  [RECHECK PASS] {news['title'][:30]}... (5W1H: {result['w5h1_score']})")

                    else:

                        # 仍然失败,标记为已拒绝

                        self._mark_news_as_rejected_v2(news, result)

                        recheck_failed += 1

                        logger.info(f"  [RECHECK REJECT] {news['title'][:30]}... ({result.get('content_type', '未知')})")

                except Exception as e:

                    logger.warning(f"  [RECHECK ERROR] {news['title'][:30]}... 错误: {e}")

                    recheck_failed += 1

            logger.info(f"重新判断完成: 通过 {recheck_passed} 条, 拒绝 {recheck_failed} 条")

            self.stats['recheck_passed'] = recheck_passed

            self.stats['recheck_failed'] = recheck_failed

        except Exception as e:

            logger.error(f"重新判断失败: {e}")

            logger.warning("待分类新闻将保持原状态,下次采集时会重新处理")

    def _build_recheck_prompt(self, news: Dict) -> str:

        """构建重新判断的提示词"""

        return f"""请分析以下新闻,判断其是否为事实性新闻,并进行5W1H分析。

## 待分析新闻

标题:{news['title']}

来源:{news.get('source_name', '未知')}

内容:{news.get('content', '')[:1000]}

## 输出要求

请以JSON格式输出:

{{

    "is_factual": true/false,

    "content_type": "新闻/评论/广告/其他",

    "w5h1_analysis": {{

        "who": "事件主体",

        "what": "事件内容",

        "when": "事件时间",

        "where": "事件地点",

        "why": "事件原因",

        "how": "事件方式"

    }},

    "w5h1_score": 0-6,

    "domain": "政治/经济/科技/体育/娱乐/其他",

    "confidence": 0.0-1.0

}}

注意:w5h1_score 是 5W1H 分析的完整度得分(0-6分)。"""

    def _parse_recheck_response(self, response: str, news: Dict) -> Dict:

        """解析重新判断的响应"""

        from utils.text_utils import parse_json_str

        try:

            result = parse_json_str(response)

            if not isinstance(result, dict):

                raise ValueError("响应不是有效的JSON对象")

            return {

                'is_factual': result.get('is_factual', False),

                'content_type': result.get('content_type', '其他'),

                'w5h1_analysis': result.get('w5h1_analysis', {}),

                'w5h1_score': result.get('w5h1_score', 0),

                'domain': result.get('domain', '其他'),

                'confidence': result.get('confidence', 0.0)

            }

        except Exception as e:

            logger.debug(f"解析响应失败: {e}")

            return {

                'is_factual': False,

                'content_type': '解析失败',

                'w5h1_analysis': {},

                'w5h1_score': 0,

                'domain': '其他',

                'confidence': 0.0

            }

    def _update_news_after_recheck_v2(self, news: Dict, result: Dict):

        """重新判断成功后更新数据库"""

        try:

            w5h1 = result.get('w5h1_analysis', {})

            with self.db.transaction() as conn:

                cursor = conn.cursor()

                cursor.execute("""

                    UPDATE news SET

                        domain = ,

                        score = 75.0,

                        who = , what = , when_time = , where_place = , why = , how = 

                    WHERE id = 

                """, (

                    result.get('domain', '其他'),

                    w5h1.get('who', ''),

                    w5h1.get('what', ''),

                    w5h1.get('when', ''),

                    w5h1.get('where', ''),

                    w5h1.get('why', ''),

                    w5h1.get('how', ''),

                    news['news_id']

                ))

            logger.debug(f"已更新新闻: {news['news_id']}")

        except Exception as e:

            logger.error(f"更新新闻失败: {e}")

    def _mark_news_as_rejected_v2(self, news: Dict, result: Dict):

        """标记新闻为已拒绝"""

        try:

            with self.db.transaction() as conn:

                cursor = conn.cursor()

                cursor.execute("""

                    UPDATE news SET

                        domain = '已拒绝',

                        score = 0

                    WHERE id = 

                """, (news['news_id'],))

            logger.debug(f"已标记拒绝: {news['news_id']}")

        except Exception as e:

            logger.error(f"标记拒绝失败: {e}")

    def _print_summary(self):

        """打印统计摘要"""

        logger.info("")

        logger.info("=" * 70)

        logger.info("📊 任务1执行完成")

        logger.info("=" * 70)

        logger.info(f"采集总量: {self.stats['total_collected']} 条")

        if self.stats.get('incremental_filtered', 0) > 0:

            logger.info(f"增量过滤: {self.stats['incremental_filtered']} 条 (旧新闻)")

        logger.info(f"白名单通过: {self.stats['whitelist_passed']} 条")

        logger.info(f"可信度通过: {self.stats['credibility_passed']} 条")

        logger.info(f"历史去重通过: {self.stats['history_passed']} 条")

        logger.info(f"内容校验通过: {self.stats['content_passed']} 条")

        logger.info(f"AI校验通过: {self.stats['ai_passed']} 条")

        if self.stats.get('fallback', 0) > 0:

            logger.info(f"⚠️  兜底处理: {self.stats['fallback']} 条")

            if self.stats.get('recheck_passed', 0) > 0:

                logger.info(f"   └─ 重新判断通过: {self.stats['recheck_passed']} 条")

            if self.stats.get('recheck_failed', 0) > 0:

                logger.info(f"   └─ 重新判断拒绝: {self.stats['recheck_failed']} 条")

        # 补救采集统计

        if self.stats.get('remedial_count', 0) > 0:

            logger.info(f"🔧 补救采集: {self.stats['remedial_count']} 条")

            if self.stats.get('remedial_success', 0) > 0:

                logger.info(f"   └─ ✅ 补救成功: {self.stats['remedial_success']} 个源")

            if self.stats.get('remedial_partial', 0) > 0:

                logger.info(f"   └─ ⚠️  部分补救: {self.stats['remedial_partial']} 个源")

            if self.stats.get('remedial_failed', 0) > 0:

                logger.info(f"   └─ ❌ 补救失败: {self.stats['remedial_failed']} 个源")

        # AI处理统计
        ai_batch_failed = self.stats.get('ai_batch_failed', 0)
        ai_retry_failed = self.stats.get('ai_retry_failed', 0)
        if ai_batch_failed > 0 or ai_retry_failed > 0:
            logger.info(f"🤖 AI处理统计:")
            logger.info(f"   └─ 批量成功: {self.stats.get('ai_batch_success', 0)} 条")
            logger.info(f"   └─ 批量失败: {ai_batch_failed} 条")
            logger.info(f"   └─ 重试成功: {self.stats.get('ai_retry_success', 0)} 条")
            logger.info(f"   └─ 最终失败: {ai_retry_failed} 条")

        if self.stats.get('embedding_generated', 0) > 0:
            logger.info(f"🔢 向量化生成: {self.stats['embedding_generated']} 条")

        logger.info(f"存入数据库: {self.stats['stored']} 条")

        # 打印数据库统计

        db_stats = self.db.get_stats()

        logger.info(f"数据库总量: {db_stats['total_news']} 条")

        logger.info(f"最近24小时: {db_stats['recent_24h']} 条")

        logger.info("=" * 70)

def main():

    """主函数"""

    try:

        with task_lock('collect', timeout=3600, blocking=False):

            collector = Task1NewsCollector()

            result = collector.run()

            return 0 if result['success'] else 1

    except RuntimeError as e:

        logger.error(f"任务锁获取失败: {e}")

        logger.warning("可能有另一个采集任务正在运行,跳过本次执行")

        return 1

if __name__ == "__main__":

    sys.exit(main())
