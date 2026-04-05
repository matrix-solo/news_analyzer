#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

系统自检模块 - 定期检查各模块工作状态

功能:

1. 检查数据库连接和表结构

2. 检查API密钥配置

3. 检查RSS源可用性

4. 检查存储空间

5. 检查知识库状态

6. 生成自检报告

使用方式:

- 手动运行: python scripts/system_check.py

- 定时运行: 集成到任务调度器中

"""

import os

import sys

import json

import logging

import sqlite3

from datetime import datetime, timedelta

from pathlib import Path

from typing import Dict, List, Any, Optional

from dataclasses import dataclass, asdict

project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))

from utils.logging_config import setup_logging, get_logger

logger = get_logger("SystemCheck")

@dataclass

class CheckResult:

    """检查结果"""

    module: str

    status: str  # ok, warning, error

    message: str

    details: Optional[Dict] = None

    timestamp: str = ""

    def __post_init__(self):

        if not self.timestamp:

            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

class SystemChecker:

    """系统自检器"""

    def __init__(self, output_dir: Optional[str] = None):

        self.project_root = Path(__file__).parent.parent

        self.output_dir = Path(output_dir) if output_dir else (self.project_root / "data" / "checks")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[CheckResult] = []

        self.start_time: Optional[datetime] = None

        self.end_time: Optional[datetime] = None

    def run_all_checks(self) -> Dict[str, Any]:

        """运行所有检查"""

        self.start_time = datetime.now()

        self.results = []

        logger.info("=" * 60)

        logger.info("开始系统自检")

        logger.info("=" * 60)

        self._check_environment()

        self._check_database()

        self._check_api_keys()

        self._check_rss_sources()

        self._check_storage_space()

        self._check_knowledge_base()

        self._check_log_files()

        self.end_time = datetime.now()

        report = self._generate_report()

        self._save_report(report)

        return report

    def _check_environment(self):

        """检查环境配置"""

        try:

            from core.config.loader import load_env, load_sources

            env_config = load_env()

            sources_config = load_sources()

            self.results.append(CheckResult(

                module="环境配置",

                status="ok",

                message=f"环境变量加载成功,共 {len(env_config)} 项配置",

                details={"env_count": len(env_config), "sources_count": len(sources_config)}

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="环境配置",

                status="error",

                message=f"环境配置加载失败: {e}"

            ))

    def _check_database(self):

        """检查数据库状态"""

        db_path = self.project_root / "data" / "news.db"

        if not db_path.exists():

            self.results.append(CheckResult(

                module="数据库",

                status="warning",

                message="数据库文件不存在"

            ))

            return

        try:

            conn = sqlite3.connect(str(db_path))

            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")

            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['news', 'processed_news', 'rejected_news', 'event_clusters']

            missing_tables = [t for t in expected_tables if t not in tables]

            cursor.execute("SELECT COUNT(*) FROM news")

            news_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM news WHERE pub_date >= date('now', '-1 day')")

            recent_count = cursor.fetchone()[0]

            db_size_mb = db_path.stat().st_size / (1024 * 1024)

            conn.close()

            if missing_tables:

                status = "warning"

                message = f"缺少表: {', '.join(missing_tables)}"

            else:

                status = "ok"

                message = f"数据库正常,共 {news_count} 条新闻,近24小时 {recent_count} 条"

            self.results.append(CheckResult(

                module="数据库",

                status=status,

                message=message,

                details={

                    "tables": tables,

                    "news_count": news_count,

                    "recent_count": recent_count,

                    "size_mb": round(db_size_mb, 2)

                }

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="数据库",

                status="error",

                message=f"数据库检查失败: {e}"

            ))

    def _check_api_keys(self):

        """检查API密钥配置"""

        try:

            from core.config.loader import get_env

            keys_status = {}

            missing_keys = []

            required_keys = [

                ("AI_ANALYSIS_KEY", "深度分析API"),

                ("AI_FILTER_KEY", "快速筛选API"),

            ]

            optional_keys = [

                ("AI_BACKUP_KEY", "备用API"),

                ("NEWS_API_KEY", "NewsAPI"),

                ("SMTP_PASSWORD", "邮件服务"),

            ]

            for key, name in required_keys:

                value = get_env(key)

                if value and len(value) > 10:

                    keys_status[name] = "已配置"

                else:

                    keys_status[name] = "未配置"

                    missing_keys.append(name)

            for key, name in optional_keys:

                value = get_env(key)

                keys_status[name] = "已配置" if value and len(value) > 10 else "未配置(可选)"

            if missing_keys:

                status = "error"

                message = f"缺少必需的API密钥: {', '.join(missing_keys)}"

            else:

                status = "ok"

                message = "所有必需API密钥已配置"

            self.results.append(CheckResult(

                module="API密钥",

                status=status,

                message=message,

                details=keys_status

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="API密钥",

                status="error",

                message=f"API密钥检查失败: {e}"

            ))

    def _check_rss_sources(self):

        """检查RSS源状态"""

        try:

            from health_monitor.health_monitor import HealthMonitor

            monitor = HealthMonitor()

            if hasattr(monitor, 'get_all_status'):

                all_status = monitor.get_all_status()

            elif hasattr(monitor, 'health_data'):

                all_status = monitor.health_data

            else:

                all_status = {}

            total = len(all_status)

            healthy = sum(1 for s in (all_status.values() if isinstance(all_status, dict) else all_status) 

                         if getattr(s, 'status', None) == "healthy")

            failed = sum(1 for s in (all_status.values() if isinstance(all_status, dict) else all_status) 

                        if getattr(s, 'status', None) in ["failed", "disabled"])

            if total == 0:

                status = "warning"

                message = "没有RSS源健康记录"

            elif failed > total * 0.5:

                status = "error"

                message = f"超过50%的RSS源失败 ({failed}/{total})"

            elif failed > 0:

                status = "warning"

                message = f"部分RSS源失败 ({failed}/{total})"

            else:

                status = "ok"

                message = f"所有RSS源正常 ({healthy}/{total})"

            self.results.append(CheckResult(

                module="RSS源",

                status=status,

                message=message,

                details={

                    "total": total,

                    "healthy": healthy,

                    "failed": failed

                }

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="RSS源",

                status="warning",

                message=f"RSS源检查失败: {e}"

            ))

    def _check_storage_space(self):

        """检查存储空间"""

        try:

            data_dir = self.project_root / "data"

            total_size = 0

            dir_sizes = {}

            for subdir in ['backups', 'heartbeats', 'locks', 'archive']:

                subdir_path = data_dir / subdir

                if subdir_path.exists():

                    size = sum(f.stat().st_size for f in subdir_path.rglob('*') if f.is_file())

                    dir_sizes[subdir] = round(size / (1024 * 1024), 2)

                    total_size += size

            total_size_mb = round(total_size / (1024 * 1024), 2)

            if total_size_mb > 1000:

                status = "warning"

                message = f"数据目录较大: {total_size_mb} MB,建议清理"

            else:

                status = "ok"

                message = f"数据目录大小正常: {total_size_mb} MB"

            self.results.append(CheckResult(

                module="存储空间",

                status=status,

                message=message,

                details={

                    "total_mb": total_size_mb,

                    "breakdown": dir_sizes

                }

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="存储空间",

                status="warning",

                message=f"存储空间检查失败: {e}"

            ))

    def _check_knowledge_base(self):

        """检查知识库状态"""

        try:

            kb_dir = self.project_root / "data" / "knowledge_base"

            if not kb_dir.exists():

                self.results.append(CheckResult(

                    module="知识库",

                    status="warning",

                    message="知识库目录不存在(尚未初始化)"

                ))

                return

            chroma_dir = kb_dir / "chroma"

            if chroma_dir.exists():

                from knowledge.chroma_store import ChromaKnowledgeBase

                kb = ChromaKnowledgeBase()

                stats = kb.get_stats()

                self.results.append(CheckResult(

                    module="知识库",

                    status="ok",

                    message=f"知识库正常,共 {stats.get('count', 0)} 条向量",

                    details=stats

                ))

            else:

                self.results.append(CheckResult(

                    module="知识库",

                    status="warning",

                    message="知识库尚未初始化"

                ))

        except ImportError:

            self.results.append(CheckResult(

                module="知识库",

                status="warning",

                message="知识库模块未安装(需要 chromadb)"

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="知识库",

                status="warning",

                message=f"知识库检查失败: {e}"

            ))

    def _check_log_files(self):

        """检查日志文件"""

        try:

            log_dir = self.project_root / "logs"

            if not log_dir.exists():

                self.results.append(CheckResult(

                    module="日志文件",

                    status="warning",

                    message="日志目录不存在"

                ))

                return

            log_files = list(log_dir.glob("*.log"))

            total_size = sum(f.stat().st_size for f in log_files if f.is_file())

            total_size_mb = round(total_size / (1024 * 1024), 2)

            latest_log = max(log_files, key=lambda f: f.stat().st_mtime) if log_files else None

            if latest_log:

                mtime = datetime.fromtimestamp(latest_log.stat().st_mtime)

                age_hours = (datetime.now() - mtime).total_seconds() / 3600

                if age_hours > 48:

                    status = "warning"

                    message = f"日志文件较旧,最后更新: {age_hours:.1f} 小时前"

                else:

                    status = "ok"

                    message = f"日志正常,共 {len(log_files)} 个文件,{total_size_mb} MB"

            else:

                status = "warning"

                message = "没有日志文件"

            self.results.append(CheckResult(

                module="日志文件",

                status=status,

                message=message,

                details={

                    "file_count": len(log_files),

                    "total_mb": total_size_mb,

                    "latest": str(latest_log.name) if latest_log else None

                }

            ))

        except Exception as e:

            self.results.append(CheckResult(

                module="日志文件",

                status="warning",

                message=f"日志检查失败: {e}"

            ))

    def _generate_report(self) -> Dict[str, Any]:

        """生成检查报告"""

        ok_count = sum(1 for r in self.results if r.status == "ok")

        warning_count = sum(1 for r in self.results if r.status == "warning")

        error_count = sum(1 for r in self.results if r.status == "error")

        if error_count > 0:

            overall_status = "error"

        elif warning_count > 0:

            overall_status = "warning"

        else:

            overall_status = "ok"

        duration = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0

        report = {

            "check_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "",

            "duration_seconds": round(duration, 2),

            "overall_status": overall_status,

            "summary": {

                "ok": ok_count,

                "warning": warning_count,

                "error": error_count,

                "total": len(self.results)

            },

            "results": [asdict(r) for r in self.results]

        }

        return report

    def _save_report(self, report: Dict[str, Any]):

        """保存检查报告"""

        report_file = self.output_dir / f"check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w', encoding='utf-8') as f:

            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"检查报告已保存: {report_file}")

        latest_file = self.output_dir / "latest_check.json"

        with open(latest_file, 'w', encoding='utf-8') as f:

            json.dump(report, f, ensure_ascii=False, indent=2)

    def print_summary(self, report: Dict[str, Any]):

        """打印检查摘要"""

        print("\n" + "=" * 60)

        print("系统自检报告")

        print("=" * 60)

        print(f"\n检查时间: {report['check_time']}")

        print(f"检查耗时: {report['duration_seconds']} 秒")

        print(f"整体状态: {report['overall_status'].upper()}")

        print(f"\n统计: OK={report['summary']['ok']} | WARNING={report['summary']['warning']} | ERROR={report['summary']['error']}")

        print("\n详细结果:")

        print("-" * 60)

        for result in report['results']:

            status_icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(result['status'], "❓")

            print(f"{status_icon} [{result['module']}] {result['message']}")

        print("\n" + "=" * 60)

def run_system_check() -> Dict[str, Any]:

    """运行系统自检(便捷函数)"""

    checker = SystemChecker()

    report = checker.run_all_checks()

    checker.print_summary(report)

    return report

if __name__ == "__main__":

    setup_logging(level="INFO")

    run_system_check()
