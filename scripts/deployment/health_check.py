#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""系统健康检查脚本"""

import os

import sys

import sqlite3

import json

from pathlib import Path

from datetime import datetime, timedelta

from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class HealthChecker:

    """系统健康检查器"""

    def __init__(self):

        self.checks = []

        self.results = {

            "timestamp": datetime.now().isoformat(),

            "status": "healthy",

            "checks": {}

        }

    def add_check(self, name: str, check_func):

        """添加检查项"""

        self.checks.append((name, check_func))

    def run_all_checks(self) -> Dict[str, Any]:

        """运行所有检查"""

        all_passed = True

        for name, check_func in self.checks:

            try:

                result = check_func()

                self.results["checks"][name] = {

                    "status": "pass" if result.get("passed", False) else "fail",

                    "message": result.get("message", ""),

                    "details": result.get("details", {})

                }

                if not result.get("passed", False):

                    all_passed = False

            except Exception as e:

                self.results["checks"][name] = {

                    "status": "error",

                    "message": f"检查异常: {str(e)}",

                    "details": {}

                }

                all_passed = False

        self.results["status"] = "healthy" if all_passed else "unhealthy"

        return self.results

    def check_database(self) -> Dict[str, Any]:

        """检查数据库健康状态"""

        db_path = Path("data/news.db")

        if not db_path.exists():

            return {

                "passed": False,

                "message": "数据库文件不存在",

                "details": {"path": str(db_path)}

            }

        try:

            conn = sqlite3.connect(db_path)

            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM news")

            total_news = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM news WHERE pub_date >= datetime('now', '-24 hours')")

            recent_news = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM processed_news")

            processed = cursor.fetchone()[0]

            conn.close()

            return {

                "passed": True,

                "message": f"数据库正常,总新闻数: {total_news},24小时内: {recent_news}",

                "details": {

                    "total_news": total_news,

                    "recent_24h": recent_news,

                    "processed": processed

                }

            }

        except Exception as e:

            return {

                "passed": False,

                "message": f"数据库连接失败: {str(e)}",

                "details": {}

            }

    def check_environment(self) -> Dict[str, Any]:

        """检查环境变量配置"""

        from core.config.manager import get_config_manager

        config = get_config_manager()

        # 检查AI相关环境变量

        analysis_key = config.get_env('ai_analysis_key') or config.get_env('deepseek_api_key')

        filter_key = config.get_env('ai_filter_key') or config.get_env('ark_api_key')

        has_analysis_key = bool(analysis_key)

        has_filter_key = bool(filter_key)

        if has_analysis_key or has_filter_key:

            return {

                "passed": True,

                "message": "环境变量配置正常",

                "details": {

                    "has_analysis_key": has_analysis_key,

                    "has_filter_key": has_filter_key

                }

            }

        else:

            return {

                "passed": False,

                "message": "缺少AI模型API密钥配置",

                "details": {}

            }

    def check_directories(self) -> Dict[str, Any]:

        """检查必需目录"""

        required_dirs = ["data", "logs", "reports", "config"]

        data_subdirs = ["backups", "checks"]

        missing_dirs = []

        existing_dirs = []

        for dir_name in required_dirs:

            dir_path = Path(dir_name)

            if dir_path.exists() and dir_path.is_dir():

                existing_dirs.append(dir_name)

            else:

                missing_dirs.append(dir_name)

        # 检查data目录下的子目录

        data_path = Path("data")

        if data_path.exists() and data_path.is_dir():

            for subdir in data_subdirs:

                subdir_path = data_path / subdir

                if not subdir_path.exists() or not subdir_path.is_dir():

                    missing_dirs.append(f"data/{subdir}")

        if not missing_dirs:

            return {

                "passed": True,

                "message": f"所有必需目录存在: {', '.join(existing_dirs)}",

                "details": {"existing": existing_dirs}

            }

        else:

            return {

                "passed": False,

                "message": f"缺少目录: {', '.join(missing_dirs)}",

                "details": {"missing": missing_dirs, "existing": existing_dirs}

            }

    def check_recent_activity(self) -> Dict[str, Any]:

        """检查最近活动"""

        db_path = Path("data/news.db")

        if not db_path.exists():

            return {

                "passed": False,

                "message": "数据库不存在,无法检查活动",

                "details": {}

            }

        try:

            conn = sqlite3.connect(db_path)

            cursor = conn.cursor()

            cursor.execute('''

                SELECT COUNT(*) FROM news 

                WHERE created_at >= datetime('now', '-24 hours')

            ''')

            recent_inserts = cursor.fetchone()[0]

            cursor.execute('''

                SELECT MAX(created_at) FROM news

            ''')

            last_insert = cursor.fetchone()[0]

            conn.close()

            if recent_inserts > 0:

                return {

                    "passed": True,

                    "message": f"系统活跃,24小时内新增 {recent_inserts} 条新闻",

                    "details": {

                        "recent_inserts": recent_inserts,

                        "last_insert": last_insert

                    }

                }

            else:

                return {

                    "passed": False,

                    "message": "24小时内无新增新闻,请检查采集任务",

                    "details": {"last_insert": last_insert}

                }

        except Exception as e:

            return {

                "passed": False,

                "message": f"活动检查失败: {str(e)}",

                "details": {}

            }

    def check_backup_status(self) -> Dict[str, Any]:

        """检查备份状态"""

        backup_dir = Path("data/backups")

        if not backup_dir.exists():

            return {

                "passed": False,

                "message": "备份目录不存在",

                "details": {}

            }

        backups = list(backup_dir.glob("news.db.backup_*"))

        if not backups:

            return {

                "passed": False,

                "message": "没有找到备份文件",

                "details": {}

            }

        latest_backup = max(backups, key=lambda x: x.stat().st_mtime)

        backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)

        backup_age = datetime.now() - backup_time

        if backup_age < timedelta(hours=24):

            return {

                "passed": True,

                "message": f"备份正常,最新备份: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}",

                "details": {

                    "backup_count": len(backups),

                    "latest_backup": str(latest_backup),

                    "backup_age_hours": backup_age.total_seconds() / 3600

                }

            }

        else:

            return {

                "passed": False,

                "message": f"备份过期,最新备份时间: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}",

                "details": {

                    "backup_count": len(backups),

                    "backup_age_hours": backup_age.total_seconds() / 3600

                }

            }

def main():

    """主函数"""

    print("=" * 60)

    print("🏥 系统健康检查")

    print("=" * 60)

    checker = HealthChecker()

    checker.add_check("数据库状态", checker.check_database)

    checker.add_check("环境变量", checker.check_environment)

    checker.add_check("目录结构", checker.check_directories)

    checker.add_check("最近活动", checker.check_recent_activity)

    checker.add_check("备份状态", checker.check_backup_status)

    results = checker.run_all_checks()

    print(f"\n检查时间: {results['timestamp']}")

    print(f"总体状态: {'✅ 健康' if results['status'] == 'healthy' else '❌ 异常'}")

    print("\n详细检查结果:")

    print("-" * 60)

    for name, result in results["checks"].items():

        status_icon = "✅" if result["status"] == "pass" else "❌"

        print(f"{status_icon} {name}: {result['message']}")

        if result.get("details"):

            for key, value in result["details"].items():

                print(f"   - {key}: {value}")

    print("=" * 60)

    report_path = Path("data/checks") / f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:

        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"📄 检查报告已保存: {report_path}")

    return 0 if results["status"] == "healthy" else 1

if __name__ == "__main__":

    sys.exit(main())
