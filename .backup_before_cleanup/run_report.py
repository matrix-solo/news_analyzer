#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务2 专用入口：数据库查询 → 生成报告 → 邮件发送
用于每天 00:10 执行（采集后自动运行）

改进点：
1. 使用SQLite查询最近24小时新闻
2. 查询90天历史数据进行关联分析
3. 支持任意时刻生成报告
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_current_date, get_project_root
PROJECT_ROOT = get_project_root()

from core.storage.database import NewsDatabase
from core.processor.generators.report_generator import ReportGenerator

(Path(PROJECT_ROOT) / "logs").mkdir(parents=True, exist_ok=True)
(Path(PROJECT_ROOT) / "reports").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(PROJECT_ROOT) / "logs" / f"report_{get_current_date()}.log",
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger("Report")


def main(send_email: bool = True, top_n: int = 10):
    """
    生成报告

    Args:
        send_email: 是否发送邮件
        top_n: 报告保留TOP N新闻
    """
    logger.info("=" * 60)
    logger.info("📊 任务2：每日深度分析报告")
    logger.info("=" * 60)

    db = NewsDatabase()
    report_generator = ReportGenerator()

    # ========== 阶段1：查询最近24小时新闻 ==========
    logger.info("")
    logger.info("📥 阶段1：查询最近24小时新闻")
    logger.info("-" * 50)

    recent_news = db.get_recent_news(hours=24)
    logger.info(f"最近24小时新闻: {len(recent_news)} 条")

    delay_days = 0
    if not recent_news:
        logger.warning("最近24小时没有新闻，尝试查询最新可用数据...")
        history_news = db.get_history_news(days=7)
        if history_news:
            latest_date = max(news['pub_date'] for news in history_news if news.get('pub_date'))
            recent_news = [n for n in history_news if n.get('pub_date') == latest_date]
            logger.info(f"使用最新可用数据: {latest_date}, {len(recent_news)} 条")
        else:
            logger.error("数据库中没有新闻数据，任务结束")
            return 1

    # ========== 阶段2：查询历史新闻（关联分析用） ==========
    logger.info("")
    logger.info("📚 阶段2：查询历史新闻（关联分析）")
    logger.info("-" * 50)

    history_news = db.get_history_news(days=90)
    logger.info(f"历史新闻（90天）: {len(history_news)} 条")

    if recent_news and recent_news[0].get('pub_date'):
        try:
            latest_news_date = datetime.fromisoformat(recent_news[0]['pub_date'].replace('Z', '+00:00'))
            delay = datetime.now() - latest_news_date.replace(tzinfo=None)
            delay_days = delay.days
            if delay_days > 0:
                logger.warning(f"⚠️ 数据延迟: {delay_days} 天")
        except Exception:
            pass

    # ========== 阶段3：生成报告 ==========
    logger.info("")
    logger.info("📝 阶段3：生成报告")
    logger.info("-" * 50)

    report_date = get_current_date()

    brief_report_file = report_generator.generate_brief_report(recent_news, report_date)
    logger.info(f"简要摘要报告: {brief_report_file}")

    depth_reports = report_generator.generate_depth_reports(
        recent_news,
        report_date,
        history_news=history_news
    )
    logger.info(f"深度分析报告: {len(depth_reports)} 个领域")

    # ========== 阶段4：发送邮件 ==========
    if send_email:
        logger.info("")
        logger.info("📧 阶段4：发送邮件")
        logger.info("-" * 50)

        from core.utils.email_sender import send_email_with_attachments, is_email_configured

        if is_email_configured():
            report_files = []
            reports_dir = Path(PROJECT_ROOT) / "reports" / report_date

            if reports_dir.exists():
                brief_dir = reports_dir / "brief"
                if brief_dir.exists():
                    for f in brief_dir.glob("*.md"):
                        report_files.append(f)

                depth_dir = reports_dir / "depth"
                if depth_dir.exists():
                    for f in depth_dir.glob("*.pdf"):
                        report_files.append(f)

            if report_files:
                brief_content = ""
                brief_md_files = [f for f in report_files if f.suffix == ".md"]
                if brief_md_files:
                    with open(brief_md_files[0], 'r', encoding='utf-8') as f:
                        brief_content = f.read()

                pdf_files = [f for f in report_files if f.suffix == ".pdf"]

                if delay_days > 0:
                    subject = f"【{report_date}】全球权威新闻分析报告（数据延迟{delay_days}天）"
                else:
                    subject = f"【{report_date}】全球权威新闻分析报告"

                if send_email_with_attachments(subject, brief_content, pdf_files):
                    logger.info("✅ 邮件发送成功")
                else:
                    logger.warning("⚠️ 邮件发送失败")
            else:
                logger.warning("没有找到报告文件")
        else:
            logger.info("邮件未配置，跳过发送")

    # ========== 打印统计 ==========
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 任务2执行完成")
    logger.info("=" * 60)

    db_stats = db.get_stats()
    logger.info(f"数据库总量: {db_stats['total_news']} 条")
    logger.info(f"最近24小时: {db_stats['recent_24h']} 条")
    logger.info(f"最近7天: {db_stats['recent_7d']} 条")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成新闻分析报告")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--top-n", type=int, default=10, help="报告保留TOP N新闻")

    args = parser.parse_args()

    sys.exit(main(send_email=not args.no_email, top_n=args.top_n))
