#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行：采集 + 报告生成
用于手动触发，立即获取新闻分析报告
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.insert(0, project_root)

from config import get_current_date, get_project_root
PROJECT_ROOT = get_project_root()

# 确保 logs 目录存在（云端克隆后首次运行）
(Path(PROJECT_ROOT) / 'logs').mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(PROJECT_ROOT) / 'logs' / f'run_now_{datetime.now().strftime("%Y-%m-%d")}.log',
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger("RunNow")


def run_now(max_per_source: int = 10, top_n: int = 10):
    """
    一键运行：采集 + 报告生成

    Args:
        max_per_source: 每个RSS源最大条目数
        top_n: 最终筛选保留条数

    Returns:
        执行结果
    """
    logger.info("=" * 70)
    logger.info("🚀 一键运行：新闻采集 + 报告生成")
    logger.info(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    from task1_collector import Task1NewsCollector
    from task2_reporter import Task2DailyReporter

    logger.info("")
    logger.info("📥 步骤1：执行新闻采集...")
    logger.info("-" * 50)

    collector = Task1NewsCollector()
    collect_result = collector.run(max_per_source=max_per_source)

    if not collect_result.get('success'):
        logger.error("采集失败，终止执行")
        return {'success': False, 'error': 'collect_failed'}

    logger.info("")
    logger.info("📊 步骤2：生成每日报告...")
    logger.info("-" * 50)

    reporter = Task2DailyReporter()
    report_result = reporter.run(top_n=top_n)

    if not report_result.get('success'):
        logger.error("报告生成失败")
        return {'success': False, 'error': 'report_failed'}

    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ 一键运行完成！")
    logger.info("=" * 70)

    collect_stats = collect_result.get('stats', {})
    report_stats = report_result.get('stats', {})

    logger.info(f"采集: {collect_stats.get('stored', 0)} 条新新闻存入待分析池")
    logger.info(f"报告: TOP{top_n} 新闻已生成")

    today = get_current_date()
    report_file = Path(PROJECT_ROOT) / 'reports' / f'daily_report_{today}.md'
    if report_file.exists():
        logger.info(f"报告路径: {report_file}")

    return {
        'success': True,
        'collect_stats': collect_stats,
        'report_stats': report_stats,
        'top_news': report_result.get('top_news', [])
    }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="一键运行：新闻采集 + 报告生成")
    parser.add_argument('--max-per-source', type=int, default=10, help='每个RSS源最大条目数')
    parser.add_argument('--top-n', type=int, default=10, help='最终筛选保留条数')

    args = parser.parse_args()

    result = run_now(max_per_source=args.max_per_source, top_n=args.top_n)
    return 0 if result.get('success') else 1


if __name__ == "__main__":
    sys.exit(main())
