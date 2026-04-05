#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送脚本 - 发送最新生成的报告
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import get_current_date, get_project_root
PROJECT_ROOT = get_project_root()

from core.utils.email_sender import send_email_with_attachments, is_email_configured

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("SendEmail")


def get_latest_report_files() -> list:
    """获取最新生成的报告文件"""
    reports_dir = Path(PROJECT_ROOT) / "reports"
    today = get_current_date()

    pdf_files = []

    today_dir = reports_dir / today
    if today_dir.exists():
        brief_dir = today_dir / "brief"
        if brief_dir.exists():
            for f in brief_dir.glob("*.md"):
                pdf_files.append(f)

        depth_dir = today_dir / "depth"
        if depth_dir.exists():
            for f in depth_dir.glob("*.pdf"):
                pdf_files.append(f)

    if not pdf_files:
        all_dirs = sorted(reports_dir.iterdir(), reverse=True)
        for d in all_dirs:
            if d.is_dir() and d.name.startswith("20"):
                brief_dir = d / "brief"
                depth_dir = d / "depth"

                if brief_dir.exists():
                    for f in brief_dir.glob("*.md"):
                        pdf_files.append(f)

                if depth_dir.exists():
                    for f in depth_dir.glob("*.pdf"):
                        pdf_files.append(f)

                if pdf_files:
                    break

    return pdf_files


def main():
    logger.info("=" * 60)
    logger.info("📧 发送报告邮件")
    logger.info("=" * 60)

    if not is_email_configured():
        logger.error("邮件未配置，请检查 SMTP_* 环境变量")
        return 1

    report_files = get_latest_report_files()

    if not report_files:
        logger.warning("没有找到报告文件")
        return 1

    logger.info(f"找到 {len(report_files)} 个报告文件:")
    for f in report_files:
        logger.info(f"  - {f.name}")

    brief_content = ""
    brief_md_files = [f for f in report_files if f.suffix == ".md"]
    if brief_md_files:
        with open(brief_md_files[0], 'r', encoding='utf-8') as f:
            brief_content = f.read()

    pdf_files = [f for f in report_files if f.suffix == ".pdf"]

    today = get_current_date()
    subject = f"【{today}】全球权威新闻分析报告"

    if send_email_with_attachments(subject, brief_content, pdf_files):
        logger.info("✅ 邮件发送成功")
        return 0
    else:
        logger.error("❌ 邮件发送失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
