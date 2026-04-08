#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务2：每日深度分析报告任务
触发：每日00:10运行一次
流程：DB读取近24h新闻 → 去重 → 简要报告 → 深度报告 → 推送
数据源：统一从 SQLite news 表读取（task1 写入同一位置）
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import get_current_date, get_project_root
PROJECT_ROOT = get_project_root()

from core.storage.database import get_db
from core.processor.generators.report_generator import ReportGenerator
from core.utils.email_sender import send_email_with_attachments, is_email_configured
from core.utils.workflow_timer import WorkflowTimer

_log_dir = Path(PROJECT_ROOT) / 'logs'
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            _log_dir / f'task2_report_{datetime.now().strftime("%Y-%m-%d")}.log',
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger("Task2Reporter")


class Task2DailyReporter:
    """任务2：每日深度分析报告生成器"""

    def __init__(self):
        self.db = get_db()
        self.report_generator = ReportGenerator()

        self.stats = {
            'db_total': 0,
            'dedup_passed': 0,
            'brief_report': '',
            'depth_reports': [],
            'report_generated': False
        }

    def run(self, top_n: int = 10) -> Dict[str, Any]:
        _timer = WorkflowTimer("task2_report").start()

        logger.info("=" * 70)
        logger.info("📊 任务2：每日深度分析报告")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        # ========== 阶段1：从 DB 读取近24小时新闻 ==========
        with _timer.stage("读取近24h新闻"):
            recent_news = self.db.get_recent_news(hours=24)
            self.stats['db_total'] = len(recent_news)
        logger.info(f"阶段1：DB 近24h新闻 - {len(recent_news)} 条")

        if not recent_news:
            logger.warning("近24小时无新闻，发送通知并退出...")
            self._send_no_news_notification()
            _timer.finish(status="failed", summary={"reason": "no_news_in_24h"})
            return {'success': False, 'reason': 'no_news_in_24h'}

        report_date = get_current_date()

        # ========== 阶段2：记录新闻数量 ==========
        self.stats['news_count'] = len(recent_news)

        # ========== 阶段3：生成简要摘要报告 ==========
        with _timer.stage("生成简要报告"):
            brief_report_file = self.report_generator.generate_brief_report(recent_news, report_date)
            self.stats['brief_report'] = brief_report_file
        logger.info(f"阶段3：简要报告 - {brief_report_file}")

        # ========== 阶段4：生成深度分析报告 ==========
        with _timer.stage("获取历史关联数据"):
            history_news = self.db.get_history_news(days=90)
        logger.info(f"阶段4：历史关联数据 - {len(history_news)} 条（近90天）")

        with _timer.stage("生成深度报告"):
            depth_reports = self.report_generator.generate_depth_reports(recent_news, report_date=report_date, history_news=history_news)
            self.stats['depth_reports'] = depth_reports
        logger.info(f"阶段4：深度报告 - {len(depth_reports)} 个领域")

        self.stats['report_generated'] = True

        # ========== 阶段6：发送邮件 ==========
        with _timer.stage("发送邮件"):
            if is_email_configured():
                logger.info("阶段6：发送邮件...")
                brief_content = ""
                brief_path = Path(brief_report_file)
                if brief_path.exists():
                    with open(brief_path, 'r', encoding='utf-8') as f:
                        brief_content = f.read()

                pdf_attachments = []
                for depth_report in depth_reports:
                    report_path = Path(depth_report)
                    pdf_path = report_path.with_suffix('.pdf')
                    if pdf_path.exists():
                        pdf_attachments.append(pdf_path)
                    elif report_path.exists():
                        pdf_attachments.append(report_path)

                subject = f"【{report_date}】全球权威新闻分析报告"
                if send_email_with_attachments(subject, brief_content, pdf_attachments):
                    logger.info("✅ 报告已发送（简要版正文 + 深度版PDF附件）")
                else:
                    logger.warning("⚠️ 报告发送失败")
            else:
                logger.info("邮件未配置，跳过发送。")

        self._print_summary()

        _timer.finish(status="success", summary=self.stats)

        return {
            'success': True,
            'stats': self.stats
        }

    def _send_no_news_notification(self):
        """发送"无新数据"通知邮件给开发者"""
        from datetime import datetime

        subject = f"【告警】新闻采集异常 - {get_current_date()}"
        body = f"""新闻采集系统告警

日期：{get_current_date()}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

告警内容：
近24小时内无新新闻入库，请检查：

1. task1_collector.py 采集任务是否正常运行
2. RSS 信源是否可用
3. 数据库写入是否成功
4. AI API 调用是否正常

此告警由 task2_reporter.py 自动发送。
"""

        if is_email_configured():
            success = send_email_with_attachments(subject, body, recipients=[])
            if success:
                logger.info("✅ 无新闻通知邮件已发送")
            else:
                logger.error("❌ 无新闻通知邮件发送失败")
        else:
            logger.warning("邮件未配置，跳过通知发送")

    def _select_top_n(self, news_list: List[Dict], n: int) -> List[Dict]:
        """按 final_score 选择TOP N，5W1H 严重缺失时降权"""
        from core.processor.generators.report_generator import ReportGenerator

        def sort_key(x):
            score = x.get('final_score', x.get('influence_score', 0))
            # 5W1H 全部无效时降权 50%
            if not ReportGenerator._has_minimal_5w1h(x, min_valid=1):
                score *= 0.5
            return score

        return sorted(news_list, key=sort_key, reverse=True)[:n]

    def _print_summary(self):
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 任务2执行完成")
        logger.info("=" * 70)
        logger.info(f"DB 近24h: {self.stats['db_total']} 条")
        logger.info(f"报告生成: {'成功' if self.stats['report_generated'] else '失败'}")
        logger.info("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成新闻分析报告")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--top-n", type=int, default=10, help="TOP N 条数")
    args = parser.parse_args()

    if args.no_email:
        import core.utils.email_sender as _es
        _es.is_email_configured = lambda: False

    reporter = Task2DailyReporter()
    result = reporter.run(top_n=args.top_n)
    return 0 if result['success'] else 1


if __name__ == "__main__":
    sys.exit(main())
