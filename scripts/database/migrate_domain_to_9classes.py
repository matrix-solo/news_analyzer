#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：统一 domain 分类为9类

映射规则：
- 健康、环境 → 社会
- 娱乐 → 文化
- 复合类型（政治/经济、政治/经济 等）→ 政治
- 其他（社会/安全事故）→ 社会
- 已拒绝 → 保持不变

运行方式：
    python scripts/database/migrate_domain_to_9classes.py
"""

import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def migrate_domain(db_path: str = None):
    """执行数据库迁移"""
    if db_path is None:
        db_path = project_root / "data" / "news.db"

    print(f"数据库路径: {db_path}")

    if not Path(db_path).exists():
        print("数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("\n迁移前 domain 分布：")
        cursor.execute('''
            SELECT domain, COUNT(*) as cnt
            FROM news
            GROUP BY domain
            ORDER BY cnt DESC
        ''')
        for row in cursor.fetchall():
            print(f"  {row[0] or '(空)'}: {row[1]}")

        print("\n执行迁移...")

        migrations = [
            ("UPDATE news SET domain = '社会' WHERE domain = '健康'", "健康 → 社会"),
            ("UPDATE news SET domain = '社会' WHERE domain = '环境'", "环境 → 社会"),
            ("UPDATE news SET domain = '文化' WHERE domain = '娱乐'", "娱乐 → 文化"),
            ("UPDATE news SET domain = '社会' WHERE domain = '其他'", "其他 → 社会"),
            ("UPDATE news SET domain = '社会' WHERE domain = '其他（社会/安全事故）'", "其他（社会/安全事故） → 社会"),
            ("UPDATE news SET domain = '政治' WHERE domain = '政治/经济'", "政治/经济 → 政治"),
            ("UPDATE news SET domain = '政治' WHERE domain = '经济/政治'", "经济/政治 → 政治"),
            ("UPDATE news SET domain = '政治' WHERE domain = '经济/科技'", "经济/科技 → 政治"),
        ]

        for sql, description in migrations:
            cursor.execute(sql)
            print(f"  {description}: {cursor.rowcount} 条")

        print("\n迁移后 domain 分布：")
        cursor.execute('''
            SELECT domain, COUNT(*) as cnt
            FROM news
            GROUP BY domain
            ORDER BY cnt DESC
        ''')
        for row in cursor.fetchall():
            print(f"  {row[0] or '(空)'}: {row[1]}")

        conn.commit()
        print("\n迁移完成！")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="数据库迁移：统一 domain 为9类")
    parser.add_argument("--db", type=str, help="数据库路径")
    args = parser.parse_args()

    migrate_domain(args.db)
