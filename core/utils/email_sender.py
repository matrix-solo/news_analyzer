#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送模块 - 用于将分析报告发送至指定邮箱
支持 SMTP（含授权码）配置，支持 PDF 附件
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("EmailSender")


def get_email_config() -> dict:
    """从环境变量读取邮件配置"""
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
    except (ImportError, OSError):
        pass
    return {
        "smtp_host": os.getenv("SMTP_HOST", "smtp.qq.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_password": os.getenv("SMTP_PASSWORD", ""),
        "sender": os.getenv("EMAIL_SENDER", ""),
        "recipients": os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else [],
    }


def is_email_configured() -> bool:
    """检查邮件是否已配置"""
    config = get_email_config()
    return bool(
        config["smtp_user"]
        and config["smtp_password"]
        and config["recipients"]
    )


def send_email_with_attachments(
    subject: str,
    body: str,
    attachments: List[Path] = None,
    recipients: List[str] = None
) -> bool:
    """
    发送带附件的邮件
    
    Args:
        subject: 邮件主题
        body: 邮件正文
        attachments: 附件文件路径列表
        recipients: 收件人列表
    
    Returns:
        是否发送成功
    """
    config = get_email_config()
    if not config["smtp_user"] or not config["smtp_password"]:
        logger.warning("邮件未配置：缺少 SMTP_USER 或 SMTP_PASSWORD")
        return False
    
    recipients = recipients or config["recipients"]
    if not recipients:
        logger.warning("邮件未配置：缺少收件人")
        return False
    
    sender = config["sender"] or config["smtp_user"]
    
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    
    # 正文
    text_part = MIMEText(body, "plain", "utf-8")
    msg.attach(text_part)
    
    # 附件
    if attachments:
        for attachment in attachments:
            if not attachment.exists():
                logger.warning(f"附件不存在: {attachment}")
                continue
            
            with open(attachment, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment.name
                )
                msg.attach(part)
            logger.info(f"已添加附件: {attachment.name}")
    
    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.sendmail(sender, recipients, msg.as_string())
        logger.info(f"邮件已发送至 {len(recipients)} 个收件人")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_report_email(
    report_content: str,
    subject: str = None,
    report_date: str = None
) -> bool:
    """
    发送分析报告邮件（纯文本，无附件）
    
    Args:
        report_content: 报告内容（Markdown 或纯文本）
        subject: 邮件主题，默认自动生成
        report_date: 报告日期
    
    Returns:
        是否发送成功
    """
    config = get_email_config()
    if not config["smtp_user"] or not config["smtp_password"]:
        logger.warning("邮件未配置：缺少 SMTP_USER 或 SMTP_PASSWORD")
        return False
    if not config["recipients"]:
        logger.warning("邮件未配置：缺少 EMAIL_RECIPIENTS")
        return False

    sender = config["sender"] or config["smtp_user"]
    if not subject and report_date:
        subject = f"【{report_date}】全球权威新闻分析报告"
    elif not subject:
        subject = "全球权威新闻分析报告"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(config["recipients"])

    text_part = MIMEText(report_content, "plain", "utf-8")
    msg.attach(text_part)

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.sendmail(sender, config["recipients"], msg.as_string())
        logger.info(f"报告已发送至 {len(config['recipients'])} 个收件人")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_report_files_email(
    report_files: List[str],
    report_date: str = None,
    send_pdf: bool = True
) -> bool:
    """
    发送报告文件邮件（带附件）
    
    Args:
        report_files: 报告文件路径列表（MD 文件）
        report_date: 报告日期
        send_pdf: 是否发送 PDF 版本（优先）
    
    Returns:
        是否发送成功
    """
    if not report_files:
        logger.warning("没有报告文件需要发送")
        return False
    
    # 准备附件
    attachments = []
    for report_file in report_files:
        report_path = Path(report_file)
        
        if send_pdf:
            # 优先发送 PDF 版本
            pdf_path = report_path.with_suffix('.pdf')
            if pdf_path.exists():
                attachments.append(pdf_path)
                continue
        
        # 如果没有 PDF 或不发送 PDF，发送 MD 文件
        if report_path.exists():
            attachments.append(report_path)
    
    if not attachments:
        logger.warning("没有找到可发送的附件")
        return False
    
    # 生成邮件主题和正文
    if report_date:
        subject = f"【{report_date}】全球权威新闻分析报告"
    else:
        subject = "全球权威新闻分析报告"
    
    body = f"""
您好！

附件为{report_date or '今日'}的新闻分析报告，请查收。

报告包含：
- 简要摘要报告（中国TOP10 + 国外TOP10）
- 深度分析报告（政治/经济/科技领域）

如有问题，请回复此邮件。

---
此邮件由 AI 新闻分析系统自动发送
"""
    
    return send_email_with_attachments(subject, body, attachments)


def send_report_file_email(report_path: Path) -> bool:
    """
    读取报告文件并发送邮件（兼容旧接口）
    
    Args:
        report_path: 报告文件路径
    
    Returns:
        是否发送成功
    """
    if not report_path.exists():
        logger.error(f"报告文件不存在: {report_path}")
        return False

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    stem = report_path.stem
    report_date = stem.replace("daily_report_", "") if "daily_report_" in stem else ""

    return send_report_email(content, report_date=report_date)
