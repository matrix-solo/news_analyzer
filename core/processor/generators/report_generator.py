#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器 - 生成简要摘要报告和深度分析报告
"""

import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from core.processor.ai_processor import AIProcessor
from core.processor.depth_analyzer import DepthAnalyzer

# BGE-M3 引擎优先，不可用时跳过向量关联
try:
    import faiss  # noqa: F401
    from sentence_transformers import SentenceTransformer  # noqa: F401
    from core.processor.history_relation_engine_bge3 import (
        get_bge3_engine as _get_engine_impl,
        format_related_section,
        format_related_table,
        BGE3HistoryRelationEngine,
    )
    _USING_BGE3 = True
    logger_pre = __import__('logging').getLogger("ReportGenerator")
    logger_pre.info("使用 BGE-M3 (FAISS)")
except ImportError:
    _USING_BGE3 = False
    _get_engine_impl = None

from core.processor.article_fetcher import ArticleFetcher, fetch_original_articles
from core.processor.history_relation_engine_fulltext import (
    BGE3FullTextEngine,
    format_fulltext_related_table,
    format_fulltext_related_section,
)


def _get_engine(history_news):
    if _get_engine_impl is None:
        return None
    return _get_engine_impl(history_news)
from core.processor.investment_advisor import InvestmentAdvisor
from core.storage.database import get_db, NewsDatabase
from core.config import get_current_date, get_project_root
from core.processor.chart_data_service import ChartDataService
from core.utils.market_data_fetcher import get_market_snapshot, MarketSnapshot

PROJECT_ROOT = get_project_root()

# logger 必须在这里定义，因为 _load_source_region_map 会用到
logger = logging.getLogger("ReportGenerator")

# 加载信源区域映射
_SOURCE_REGION_MAP = {}


def _load_source_region_map():
    """从 sources.yaml 加载信源名称 → 区域的映射"""
    global _SOURCE_REGION_MAP
    try:
        import yaml
        yaml_path = PROJECT_ROOT / "sources.yaml"
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            region_map = {}
            # 遍历所有顶级分类（international, china 等）
            for category, sources in data.items():
                if not isinstance(sources, dict):
                    continue
                # 遍历每个分类下的子分类
                for sub_category, source_list in sources.items():
                    if not isinstance(source_list, list):
                        continue
                    for source in source_list:
                        if isinstance(source, dict) and 'name' in source:
                            name = source.get('name', '')
                            region = source.get('region', '')
                            if name and region:
                                region_map[name.lower()] = region.lower()
            _SOURCE_REGION_MAP = region_map
            logger.info(f"加载信源区域映射: {len(region_map)} 个信源")
        else:
            logger.warning(f"sources.yaml 不存在: {yaml_path}")
    except Exception as e:
        logger.warning(f"加载信源区域映射失败: {e}")


# 初始化加载
_load_source_region_map()


@dataclass
class DomainContext:
    """领域分析上下文"""
    name: str
    news: List[Dict]
    clusters: List[Dict]
    stats: Dict


class ReportGenerator:
    """报告生成器 - 生成简要摘要报告和深度分析报告"""
    
    def __init__(self):
        self.ai_processor = AIProcessor()
        # 深度分析与投资顾问使用 ANALYSIS 模型
        self.analysis_provider = self.ai_processor.get_provider("ANALYSIS")
        self.depth_analyzer: Optional[DepthAnalyzer] = None
        self.investment_advisor: Optional[InvestmentAdvisor] = None

        if self.analysis_provider:
            self.depth_analyzer = DepthAnalyzer(self.analysis_provider)
            # 是否启用投资分析，由环境变量控制，默认关闭以节约成本
            enable_invest = os.getenv("ENABLE_INVESTMENT_ANALYSIS", "false").lower() in {
                "1",
                "true",
                "yes",
            }
            if enable_invest:
                self.investment_advisor = InvestmentAdvisor(self.analysis_provider)

        # 数据库用于生成领域统计面板
        self.db: NewsDatabase = get_db()
        self.chart_service = ChartDataService(self.db)
        self.report_dir = Path(PROJECT_ROOT) / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_date_dirs(self, report_date: str) -> tuple:
        """获取按日期分类的目录路径"""
        date_dir = self.report_dir / report_date
        brief_dir = date_dir / "brief"
        depth_dir = date_dir / "depth"
        brief_dir.mkdir(parents=True, exist_ok=True)
        depth_dir.mkdir(parents=True, exist_ok=True)
        return brief_dir, depth_dir
    
    def generate_brief_report(self, all_news: List[Dict], report_date: str = None) -> str:
        """
        生成简要摘要报告（手机版）
        
        Args:
            all_news: 所有新闻列表
            report_date: 报告日期（采集日期），默认使用当前日期
        
        Returns:
            报告文件路径
        """
        today = report_date or get_current_date()
        brief_dir, _ = self._get_date_dirs(today)

        # 分离中国和国外新闻，按 final_score 排序
        def _sort_key(n):
            try:
                score = n.get('final_score') or n.get('influence_score') or 0
                return float(score)
            except (ValueError, TypeError):
                return 0.0

        china_news = sorted(
            [n for n in all_news if self._is_china_news(n)], key=_sort_key, reverse=True
        )
        foreign_news = sorted(
            [n for n in all_news if not self._is_china_news(n)], key=_sort_key, reverse=True
        )
        china_top10 = china_news[:10]
        foreign_top10 = foreign_news[:10]

        # 生成报告
        report_lines = [
            f"# 【{today} 全球新闻简要摘要】",
            "",
            "**排序说明**：本报告按综合评分（final_score）从高到低排序，综合评分由事件影响力、分析价值等因素计算得出。",
            ""
        ]

        report_lines.extend([
            "## 当日中国 TOP10 新闻",
            ""
        ])
        for i, news in enumerate(china_top10, 1):
            title = news.get('translated_title', news.get('title', '无标题'))
            summary = news.get('summary') or news.get('content', '')[:200]
            source = news.get('source_name', news.get('source', '未知来源'))

            report_lines.append(f"### {i}. {title}")
            report_lines.append(f"- **来源**：{source}")
            report_lines.append(f"- **摘要**：{summary}")
            report_lines.append("")

        report_lines.extend([
            "",
            "## 当日国外 TOP10 新闻",
            ""
        ])
        for i, news in enumerate(foreign_top10, 1):
            title = news.get('translated_title', news.get('title', '无标题'))
            summary = news.get('summary') or news.get('content', '')[:200]
            source = news.get('source_name', news.get('source', '未知来源'))

            report_lines.append(f"### {i}. {title}")
            report_lines.append(f"- **来源**：{source}")
            report_lines.append(f"- **摘要**：{summary}")
            report_lines.append("")

        report_lines.extend([
            "",
            "---",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        # 保存报告（添加时间戳避免覆盖）
        report_content = '\n'.join(report_lines)
        timestamp = datetime.now().strftime('%H%M%S')
        report_file = brief_dir / f"daily_report_{today}_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"简要摘要报告已生成: {report_file}")
        
        # 生成 PDF 版本
        try:
            from core.utils.md2pdf import create_pdf_from_md, is_pdf_available
            if is_pdf_available():
                pdf_file = brief_dir / f"daily_report_{today}_{timestamp}.pdf"
                if create_pdf_from_md(report_content, pdf_file):
                    logger.info(f"PDF 报告已生成: {pdf_file}")
        except Exception as e:
            logger.warning(f"PDF 生成失败: {e}")
        
        return str(report_file)
    
    def generate_depth_reports(
        self,
        all_news: List[Dict],
        report_date: str = None,
        history_news: List[Dict] = None,
    ) -> List[str]:
        """
        生成深度分析报告（领域版）

        流程：
        1. 按领域分组
        2. 事件聚类，取TOP5
        3. 获取TOP5原文 + 全文关联
        4. 深度分析（基于全文）

        Args:
            all_news: 所有新闻列表
            history_news: 历史新闻列表（近90天）
            report_date: 报告日期

        Returns:
            报告文件路径列表
        """
        today = report_date or get_current_date()
        _, depth_dir = self._get_date_dirs(today)
        report_files = []

        # 深度报告领域配置：当前仅处理核心领域（政治/经济/科技）
        # 其他领域（军事/社会/文化/体育/娱乐）的新闻数据量较少，暂不生成深度报告
        # 如需扩展，修改此列表即可
        domains = ['政治', '经济', '科技']

        for domain in domains:
            domain_news = [n for n in all_news if n.get('domain', '其他') == domain]

            if not domain_news:
                continue

            domain_news.sort(key=lambda x: x.get('final_score') or 0, reverse=True)

            clusters = self.ai_processor.cluster_events(domain_news)

            if not clusters:
                clusters = [
                    {
                        'event_name': n.get('translated_title', n.get('title', ''))[:30],
                        'news_ids': [n.get('news_id')],
                        'representative_id': n.get('news_id'),
                        'reason': '独立事件'
                    }
                    for n in domain_news[:5]
                ]

            clusters = clusters[:5]

            for cluster in clusters:
                rep_id = cluster.get('representative_id')
                news_ids = cluster.get('news_ids', [])

                rep_news = next((n for n in domain_news if n.get('news_id') == rep_id), None)
                if not rep_news and domain_news:
                    rep_news = domain_news[0]

                cluster['representative_news'] = rep_news

                related_news = [n for n in domain_news if n.get('news_id') in news_ids and n.get('news_id') != rep_id]
                cluster['related_news'] = related_news

            clusters = self._fetch_fulltext_for_clusters(clusters, history_news or [])

            domain_context = self._build_domain_context(domain, domain_news, clusters, today)
            report_lines = self._build_domain_report(domain_context, history_news or [], today)

            for i, cluster in enumerate(domain_context.clusters, 1):
                event_lines = self._format_depth_event(i, cluster, history_news or [])
                report_lines.extend(event_lines)

            overview = self.ai_processor.generate_domain_overview(domain, domain_context.clusters)
            report_lines.extend([
                "",
                "## 领域当日整体分析",
                "",
                overview,
                ""
            ])

            report_lines.extend([
                "",
                "---",
                f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])

            report_content = '\n'.join(report_lines)
            timestamp = datetime.now().strftime('%H%M%S')
            report_file = depth_dir / f"daily_report_depth_{domain}_{today}_{timestamp}.md"

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)

            report_files.append(str(report_file))
            logger.info(f"{domain}领域深度分析报告已生成: {report_file}")

            try:
                from core.utils.md2pdf import create_pdf_from_md, is_pdf_available
                if is_pdf_available():
                    pdf_file = depth_dir / f"daily_report_depth_{domain}_{today}_{timestamp}.pdf"
                    if create_pdf_from_md(report_content, pdf_file):
                        logger.info(f"PDF 报告已生成: {pdf_file}")
            except Exception as e:
                logger.warning(f"PDF 生成失败: {e}")

        return report_files

    def _fetch_fulltext_for_clusters(self, clusters: List[Dict], history_news: List[Dict]) -> List[Dict]:
        """获取聚类新闻原文并进行历史关联"""
        logger.info("=" * 50)
        logger.info("开始获取聚类新闻原文与历史关联...")

        fetcher = ArticleFetcher(timeout=10)
        fulltext_engine = BGE3FullTextEngine()

        all_need_fetch = []
        news_id_to_news = {}
        news_id_to_cluster = {}

        for cluster in clusters:
            rep_news = cluster.get('representative_news')
            if not rep_news:
                continue

            news_id = rep_news.get('news_id')
            if news_id:
                all_need_fetch.append(rep_news)
                news_id_to_news[news_id] = rep_news
                news_id_to_cluster[news_id] = cluster

        if history_news and all_need_fetch:
            logger.info("构建历史关联引擎...")
            history_engine = BGE3HistoryRelationEngine(history_news)

            for rep_news in all_need_fetch:
                news_id = rep_news.get('news_id')
                cluster = news_id_to_cluster.get(news_id)
                if not cluster:
                    continue
                related_records = history_engine.find_related_news(rep_news, top_k=5)
                if related_records:
                    cluster['history_related'] = related_records
                    logger.info(f"  找到 {len(related_records)} 条历史关联: {news_id}")

                    for rec in related_records:
                        hist_news = next((n for n in history_news if n.get('news_id') == rec.news_id), None)
                        if hist_news and rec.news_id not in news_id_to_news:
                            all_need_fetch.append(hist_news)
                            news_id_to_news[rec.news_id] = hist_news

        if not all_need_fetch:
            logger.info("没有需要获取原文的新闻")
            return clusters

        all_need_fetch = list(news_id_to_news.values())
        logger.info(f"并行获取 {len(all_need_fetch)} 篇原文...")

        fetched = fetcher.fetch_batch(all_need_fetch, max_workers=10)
        for news in all_need_fetch:
            news_id = news.get('news_id')
            if news_id in fetched:
                news['original_article'] = fetched[news_id]
                logger.info(f"  成功获取原文: {news_id} ({len(fetched[news_id])} chars)")
            else:
                news['original_article'] = news.get('content', '') or news.get('summary', '')
                logger.warning(f"  获取原文失败，使用摘要: {news_id}")

        for news in all_need_fetch:
            text = news.get('original_article', '')
            if text:
                fulltext_engine.add_news(news)

        for cluster in clusters:
            rep_news = cluster.get('representative_news')
            if not rep_news or not rep_news.get('original_article'):
                continue

            if not fulltext_engine._index.size:
                continue

            target_text = rep_news.get('original_article', '')
            related = fulltext_engine.find_related_full_text(
                target_text,
                top_k=5,
                min_score=0.3,
                dynamic_percentile=0.2
            )

            if related:
                logger.info(f"  找到 {len(related)} 条全文关联")
                cluster['fulltext_related'] = related

        fetcher.close()

        logger.info("聚类新闻原文获取完成")
        logger.info("=" * 50)
        return clusters

    def _build_domain_context(
        self,
        domain: str,
        domain_news: List[Dict],
        clusters: List[Dict],
        today: str,
    ) -> DomainContext:
        """构造领域分析上下文（含统计数据）"""
        # 高分阈值配置
        HIGH_SCORE_THRESHOLD = 80.0
        
        stats = {
            "count_today": len(domain_news),
            "avg_score_today": 0.0,
            "max_score_today": 0.0,
            "high_score_count_today": 0,
            "high_score_ratio_today": 0.0,
            "avg_daily_count_7d": 0.0,
            "avg_daily_count_30d": 0.0,
            "avg_score_7d": 0.0,
            "avg_score_30d": 0.0,
            "high_score_avg_7d": 0.0,
            "high_score_avg_30d": 0.0,
            "today_score_percentile_30d": 0.0,
        }

        if domain_news:
            scores = [n.get("final_score") or 0.0 for n in domain_news]
            stats["avg_score_today"] = round(sum(scores) / len(scores), 1)
            stats["max_score_today"] = max(scores)
            # 高分事件统计
            high_scores = [s for s in scores if s >= HIGH_SCORE_THRESHOLD]
            stats["high_score_count_today"] = len(high_scores)
            stats["high_score_ratio_today"] = round(len(high_scores) / len(scores) * 100, 1)

        # 领域历史统计（简单实现：用 get_history_news 结果在内存中过滤）
        try:
            history_7d = self.db.get_history_news(days=7)
            history_30d = self.db.get_history_news(days=30)
        except Exception as e:
            logger.warning(f"获取历史统计失败: {e}")
            history_7d = []
            history_30d = []

        def _calc_domain_stats(records: List[Dict]) -> Dict[str, float]:
            domain_recs = [r for r in records if r.get("domain") == domain]
            if not domain_recs:
                return {
                    "count": 0.0, 
                    "avg_score": 0.0,
                    "high_score_count": 0.0,
                    "daily_high_score_avg": 0.0,
                }
            scores = [r.get("final_score") or 0.0 for r in domain_recs]
            # 按天统计高分事件数
            daily_high_scores = defaultdict(int)
            for r in domain_recs:
                date = r.get("publish_date", "")[:10]  # 取日期部分
                if (r.get("final_score") or 0.0) >= HIGH_SCORE_THRESHOLD:
                    daily_high_scores[date] += 1
            
            avg_daily_high = sum(daily_high_scores.values()) / max(len(daily_high_scores), 1)
            
            return {
                "count": float(len(domain_recs)),
                "avg_score": round(sum(scores) / len(scores), 1),
                "high_score_count": sum(1 for s in scores if s >= HIGH_SCORE_THRESHOLD),
                "daily_high_score_avg": round(avg_daily_high, 1),
            }

        s7 = _calc_domain_stats(history_7d)
        s30 = _calc_domain_stats(history_30d)

        # 近7/30天按"天"为单位的平均新闻数，这里简单用总数/天数近似
        stats["avg_daily_count_7d"] = round(s7["count"] / 7.0, 1)
        stats["avg_daily_count_30d"] = round(s30["count"] / 30.0, 1)
        stats["avg_score_7d"] = s7["avg_score"]
        stats["avg_score_30d"] = s30["avg_score"]
        stats["high_score_avg_7d"] = s7["daily_high_score_avg"]
        stats["high_score_avg_30d"] = s30["daily_high_score_avg"]
        
        # 计算当日平均分在近30天中的百分位
        if history_30d and stats["avg_score_today"] > 0:
            # 获取近30天每天的平均分
            daily_scores = defaultdict(list)
            for r in history_30d:
                if r.get("domain") == domain:
                    date = r.get("publish_date", "")[:10]
                    daily_scores[date].append(r.get("final_score") or 0.0)
            
            daily_avgs = []
            for date, scores in daily_scores.items():
                if scores:
                    daily_avgs.append(sum(scores) / len(scores))
            
            if daily_avgs:
                # 计算百分位：小于等于当日分数的天数占比
                below_count = sum(1 for avg in daily_avgs if avg <= stats["avg_score_today"])
                stats["today_score_percentile_30d"] = round(below_count / len(daily_avgs) * 100, 1)

        return DomainContext(name=domain, news=domain_news, clusters=clusters, stats=stats)

    def _build_domain_report(
        self,
        ctx: DomainContext,
        history_news: List[Dict],
        today: str,
    ) -> List[str]:
        """生成领域级报告头部（总览 + 事件列表）"""
        lines: List[str] = []

        lines.append(f"# {ctx.name}领域深度分析报告（{today}）")
        lines.append("")
        lines.append(
            "**排序说明**：本报告按当日事件聚类重要性从高到低排序，事件重要性由该事件涉及新闻的综合评分、新闻数量等因素计算得出。"
        )
        lines.append("")
        lines.append(
            f"当日{ctx.name}领域共采集事实新闻 {ctx.stats['count_today']} 条，"
            "下表为当日与近7/30天的对比概览："
        )
        lines.append("")

        # 领域数据总览表（扩展版）
        lines.extend(
            [
                "| 指标 | 当日 | 近7天日均 | 近30天日均 | 说明 |",
                "|------|------|-----------|------------|------|",
                f"| 新闻数量 | {ctx.stats['count_today']} | {ctx.stats['avg_daily_count_7d']} | {ctx.stats['avg_daily_count_30d']} | "
                "数值越高，信息密度越大 |",
                f"| 平均综合评分 | {ctx.stats['avg_score_today']} | {ctx.stats['avg_score_7d']} | {ctx.stats['avg_score_30d']} | "
                "越高代表整体事件重要性越高 |",
                f"| 最高分事件 | {ctx.stats['max_score_today']} | - | - | 以下事件列表按综合评分排序 |",
                f"| 高分事件数(≥80分) | {ctx.stats['high_score_count_today']} | {ctx.stats['high_score_avg_7d']} | {ctx.stats['high_score_avg_30d']} | "
                "重大事件数量 |",
                f"| 高分事件占比 | {ctx.stats['high_score_ratio_today']}% | - | - | 当日重大事件占比 |",
                "",
            ]
        )

        # 热度与重要性趋势概览
        lines.append("### 热度与重要性趋势概览")
        lines.append("")
        
        # 构建趋势描述
        trend_desc = []
        
        # 高分事件数对比
        if ctx.stats['high_score_count_today'] > ctx.stats['high_score_avg_7d'] * 1.2:
            trend_desc.append(f"当日高分事件数（{ctx.stats['high_score_count_today']}条）**显著高于**近7天均值（{ctx.stats['high_score_avg_7d']}条），显示该领域今日有重大事件发生")
        elif ctx.stats['high_score_count_today'] < ctx.stats['high_score_avg_7d'] * 0.8:
            trend_desc.append(f"当日高分事件数（{ctx.stats['high_score_count_today']}条）**低于**近7天均值（{ctx.stats['high_score_avg_7d']}条），该领域今日相对平静")
        else:
            trend_desc.append(f"当日高分事件数（{ctx.stats['high_score_count_today']}条）与近7天均值（{ctx.stats['high_score_avg_7d']}条）**基本持平**")
        
        # 平均分百分位
        percentile = ctx.stats['today_score_percentile_30d']
        if percentile >= 80:
            trend_desc.append(f"当日平均分处于近30天的**前{100-percentile:.0f}%**（即高于{percentile:.0f}%的日期），属于**高活跃度**水平")
        elif percentile >= 60:
            trend_desc.append(f"当日平均分处于近30天的**前{100-percentile:.0f}%**（即高于{percentile:.0f}%的日期），属于**中等偏上**水平")
        elif percentile >= 40:
            trend_desc.append(f"当日平均分处于近30天的**中等水平**（约{percentile:.0f}%分位）")
        else:
            trend_desc.append(f"当日平均分处于近30天的**后{percentile:.0f}%**（即仅高于{percentile:.0f}%的日期），属于**低活跃度**水平")
        
        # 新闻数量对比
        if ctx.stats['count_today'] > ctx.stats['avg_daily_count_7d'] * 1.3:
            trend_desc.append(f"当日新闻数量（{ctx.stats['count_today']}条）**明显多于**近7天均值（{ctx.stats['avg_daily_count_7d']}条），信息密度较高")
        elif ctx.stats['count_today'] < ctx.stats['avg_daily_count_7d'] * 0.7:
            trend_desc.append(f"当日新闻数量（{ctx.stats['count_today']}条）**少于**近7天均值（{ctx.stats['avg_daily_count_7d']}条），信息密度较低")
        
        lines.append("；".join(trend_desc) + "。")
        lines.append("")

        # 最小可用：补一张“近30天每日新闻数/均分”表格（后续可替换为图表图片）
        try:
            metrics = self.chart_service.get_domain_daily_metrics(ctx.name, days=30)
            if metrics:
                lines.append("### 近30天趋势数据（每日）")
                lines.append("")
                lines.append("| 日期 | 新闻数 | 平均分 |")
                lines.append("|------|--------|--------|")
                # 只展示最近 14 天，避免表格过长
                for m in metrics[-14:]:
                    lines.append(f"| {m.date} | {m.count} | {m.avg_score:.1f} |")
                lines.append("")
        except Exception:
            # 报告生成不因图表数据失败而中断
            pass

        # 领域事件一览表
        lines.append("## 当日重点事件一览")
        lines.append("")
        lines.extend(
            [
                "| 排名 | 事件标题 | 代表新闻来源 | 综合得分 | 影响力 | 热度 |",
                "|------|----------|--------------|----------|--------|------|",
            ]
        )

        for idx, cluster in enumerate(ctx.clusters, 1):
            rep_news = cluster.get("representative_news") or {}
            title = cluster.get("event_name") or rep_news.get(
                "translated_title", rep_news.get("title", "")
            )
            source = rep_news.get("source_name", rep_news.get("source", "未知"))
            score = rep_news.get("final_score") or 0.0
            influence = rep_news.get("influence_score") or 0.0
            heat = rep_news.get("heat_score") or 0.0

            lines.append(
                f"| {idx} | {title} | {source} | {score} | {influence} | {heat} |"
            )

        lines.append("")
        lines.append("以下为各重点事件的详细分析：")
        lines.append("")

        return lines
    
    # ──────────────────────────────────────────────
    # 新增：市场快照 / 跨域推演 / 领域 TOP1
    # ──────────────────────────────────────────────

    def _safe_get_market_snapshot(self) -> Optional[MarketSnapshot]:
        """静默获取市场快照，失败不阻断报告生成"""
        try:
            return get_market_snapshot()
        except Exception as e:
            logger.warning(f"市场数据获取失败（已跳过）: {e}")
            return None

    def _get_domain_top1(self, all_news: List[Dict]) -> Dict[str, Dict]:
        """从全量新闻中提取各领域得分最高的1条"""
        domains = {}
        for n in all_news:
            domain = n.get('domain', '其他')
            final_score = n.get('final_score')
            score = float(final_score) if final_score is not None else 0.0
            if domain not in domains:
                domains[domain] = n
            else:
                existing_score = float(domains[domain].get('final_score')) if domains[domain].get('final_score') is not None else 0.0
                if score > existing_score:
                    domains[domain] = n
        return domains

    def _generate_cross_domain_insight(self, domain_tops: Dict[str, Dict]) -> str:
        """跨领域共振推演（1次 ANALYSIS 调用，300字以内）"""
        if not self.analysis_provider or len(domain_tops) < 2:
            return ""
        try:
            items = []
            for domain, news in list(domain_tops.items())[:4]:
                title = news.get('translated_title') or news.get('title', '')
                summary = (news.get('summary') or news.get('content') or '')[:200]
                items.append(f"【{domain}】{title}\n摘要：{summary}")

            prompt = (
                "以下是今日各领域最重要新闻。请分析它们之间是否存在隐性关联或正在形成某种共振，"
                "推演在1-3个月内最可能催生的宏观风险或机会。\n"
                "要求：聚焦最有价值的1-2个关联点，200字以内，语言精炼，有具体依据，不做空洞推测。\n\n"
                + "\n\n".join(items)
            )
            result = self.analysis_provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,
            )
            return result.strip()
        except Exception as e:
            logger.warning(f"跨域推演失败（已跳过）: {e}")
            return ""

    # ──────────────────────────────────────────────

    def _is_china_news(self, news: Dict) -> bool:
        """
        判断是否为中国新闻

        判断逻辑：
        1. 从 sources.yaml 加载的信源 region 中包含"中国" → 中国新闻
        2. 其他 → 国际新闻
        """
        source_name = news.get('source_name', '').lower()

        # 从预加载的映射中查找
        region = _SOURCE_REGION_MAP.get(source_name, '')

        # 判断 region 是否包含"中国"
        return '中国' in region
    
    def _format_brief_news(self, index: int, news: Dict) -> List[str]:
        """格式化简要摘要新闻"""
        lines = []
        
        title = news.get('translated_title', news.get('title', ''))
        source = news.get('source_name', news.get('source', '未知'))
        summary = news.get('summary') or news.get('content', '')[:150]
        url = news.get('link') or news.get('url') or news.get('official_url', '')
        domain = news.get('domain', '其他')
        core_tags = news.get('tags', [])
        
        lines.append(f"### {index}. {title}")
        lines.append(f"- **来源**：{source}")
        lines.append(f"- **摘要**：{summary}")
        if url:
            lines.append(f"- **原文链接**：[点击查看]({url})")
        lines.append(f"- **领域**：{domain}")
        if core_tags:
            lines.append(f"- **标签**：{', '.join(core_tags)}")
        lines.append("")
        
        return lines
    
    def _generate_insight_with_fallback(self, rep_news: Dict) -> str:
        """生成事件洞察，带兜底逻辑"""
        try:
            insight = self.ai_processor.generate_event_insight(
                rep_news, [], purpose="ANALYSIS"
            )
            return insight
        except Exception as e:
            logger.warning(f"ANALYSIS Provider 生成洞察失败: {e}，尝试 BACKUP...")
            try:
                insight = self.ai_processor.generate_event_insight(
                    rep_news, [], purpose="BACKUP"
                )
                return insight
            except Exception as e2:
                logger.error(f"BACKUP Provider 也失败: {e2}")
                return "（深度分析暂时不可用）"
    
    def _format_depth_event(self, index: int, cluster: Dict, history_news: List[Dict]) -> List[str]:
        """格式化深度分析事件"""
        lines = []

        event_name = cluster.get('event_name', '未知事件')
        rep_news = cluster.get('representative_news', {})
        related_news = cluster.get('related_news', [])

        lines.append(f"## 事件{index}：{event_name}")
        lines.append("")

        title = rep_news.get('translated_title', rep_news.get('title', ''))
        source = rep_news.get('source_name', rep_news.get('source', '未知'))
        url = rep_news.get('link') or rep_news.get('url') or rep_news.get('official_url', '')
        domain = rep_news.get('domain', '其他')
        core_tags = rep_news.get('tags', rep_news.get('core_tags', []))

        lines.append("### 基础信息")
        lines.append("")
        lines.append(f"- **标题**：{title}")
        lines.append(f"- **来源**：{source}")
        if url:
            lines.append(f"- **原文链接**：[点击查看]({url})")
        lines.append(f"- **领域**：{domain}")
        if core_tags:
            lines.append(f"- **标签**：{', '.join(core_tags) if isinstance(core_tags, list) else core_tags}")

        if related_news:
            lines.append("")
            lines.append("**相关新闻**：")
            for rn in related_news:
                rn_title = rn.get('translated_title', rn.get('title', ''))
                rn_url = rn.get('url', '')
                if rn_url:
                    lines.append(f"- [{rn_title}]({rn_url})")
                else:
                    lines.append(f"- {rn_title}")

        fulltext_related = cluster.get('fulltext_related', [])

        if fulltext_related:
            lines.append("")
            lines.append("### 历史关联（全文向量匹配）")
            lines.append("")
            table_md = format_fulltext_related_table(fulltext_related)
            if table_md:
                lines.append(table_md)
            lines.append("")
            related_section = format_fulltext_related_section(fulltext_related, title)
            if related_section:
                lines.append(related_section)
                lines.append("")
        elif history_news:
            lines.append("")
            lines.append("### 历史关联分析")
            lines.append("")
            try:
                engine = _get_engine(history_news)
                if engine is None:
                    lines.append("*BGE-M3 不可用，跳过向量关联*")
                    raise RuntimeError("no engine")
                _threshold = 0.53 if _USING_BGE3 else 0.1
                related_history_records = engine.find_related_news(
                    rep_news, top_k=5, threshold=_threshold
                )

                table_md = format_related_table(related_history_records)
                if table_md:
                    lines.append(table_md)
                lines.append("")
                related_section = format_related_section(related_history_records, title)
                lines.append(related_section)
            except Exception as e:
                logger.warning(f"历史关联分析失败: {e}")

        history_for_depth = []
        if fulltext_related:
            for r in fulltext_related:
                hist_record = {
                    "title": r.title,
                    "pub_date": r.pub_date,
                    "summary": r.full_text[:200] if r.full_text else '',
                    "content": r.full_text or '',
                    "unified_score": r.unified_score,
                }
                rel_hist = next((h for h in history_news if h.get('news_id') == r.news_id), None)
                if rel_hist:
                    rel_hist['original_article'] = r.full_text
                history_for_depth.append(hist_record)
        elif history_news:
            try:
                engine = _get_engine(history_news)
                related_history_records = engine.find_related_news(rep_news, top_k=5, threshold=0.53 if _USING_BGE3 else 0.1)
                history_for_depth = [
                    {
                        "title": r.title,
                        "pub_date": r.pub_date,
                        "summary": getattr(r, "summary", ""),
                        "content": getattr(r, "content", ""),
                    }
                    for r in related_history_records
                ]
            except Exception:
                pass

        if self.depth_analyzer and self.analysis_provider:
            try:
                market_anchor = ""
                news_domain = rep_news.get("domain", "")
                if news_domain in ("经济", "金融", "科技", "能源"):
                    try:
                        snap = get_market_snapshot()
                        market_anchor = snap.as_anchor_text()
                    except Exception:
                        pass

                depth_analysis = self.depth_analyzer.analyze(
                    rep_news,
                    related_history=history_for_depth,
                    market_anchor=market_anchor,
                )
                lines.extend(self.depth_analyzer.format_for_report(depth_analysis))
            except Exception as e:
                logger.warning(f"DepthAnalyzer 生成深度洞察失败: {e}")
                insight_text = self._generate_insight_with_fallback(rep_news)
                lines.append("### 单事件深度洞察")
                lines.append("")
                lines.append(insight_text)
                lines.append("")
        else:
            insight_text = self._generate_insight_with_fallback(rep_news)
            lines.append("### 单事件深度洞察")
            lines.append("")
            lines.append(insight_text)
            lines.append("")

        if self.investment_advisor and self.analysis_provider:
            try:
                advice = self.investment_advisor.analyze(
                    rep_news,
                    history_news or [],
                )
                advice_md = self.investment_advisor.format_advice_section(advice)
                lines.append(advice_md)
                lines.append("")
            except Exception as e:
                logger.warning(f"InvestmentAdvisor 分析失败: {e}")

        return lines
