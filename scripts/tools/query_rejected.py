#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询rejected_news表详情"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "news.db"

def query_rejected():
    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查询rejected_news表结构和数据
    cursor.execute("SELECT * FROM rejected_news LIMIT 5")
    rows = cursor.fetchall()
    
    print("rejected_news表样例数据：")
    print("-" * 60)
    for row in rows:
        print(f"  news_id: {row['news_id']}")
        print(f"  title: {row['title'][:50] if row['title'] else 'NULL'}...")
        print(f"  reject_reason: {row['reject_reason']}")
        print(f"  reject_type: {row['reject_type']}")
        print(f"  created_at: {row['created_at']}")
        print("-" * 40)
    
    # 统计reject_type分布
    cursor.execute("SELECT reject_type, COUNT(*) as cnt FROM rejected_news GROUP BY reject_type ORDER BY cnt DESC")
    types = cursor.fetchall()
    print("\nreject_type分布：")
    for t in types:
        print(f"  {t[0] or 'NULL'}: {t[1]}条")
    
    # 统计reject_reason分布
    cursor.execute("SELECT reject_reason, COUNT(*) as cnt FROM rejected_news GROUP BY reject_reason ORDER BY cnt DESC LIMIT 10")
    reasons = cursor.fetchall()
    print("\nreject_reason分布（Top 10）：")
    for r in reasons:
        print(f"  {r[0] or 'NULL'}: {r[1]}条")
    
    conn.close()

if __name__ == "__main__":
    query_rejected()
