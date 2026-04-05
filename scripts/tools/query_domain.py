#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询数据库domain字段实际值"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "news.db"

def query_domain_values():
    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 查询domain字段的所有不同值
    cursor.execute("SELECT domain, COUNT(*) as cnt FROM news GROUP BY domain ORDER BY cnt DESC")
    results = cursor.fetchall()
    
    print("news表domain字段实际值统计：")
    print("-" * 40)
    for row in results:
        print(f"  {row[0] or 'NULL'}: {row[1]}条")
    
    # 查询rejected_news表数据量
    cursor.execute("SELECT COUNT(*) FROM rejected_news")
    rejected_count = cursor.fetchone()[0]
    print(f"\nrejected_news表记录数: {rejected_count}")
    
    # 查询news_raw表数据量
    cursor.execute("SELECT COUNT(*) FROM news_raw")
    raw_count = cursor.fetchone()[0]
    print(f"news_raw表记录数: {raw_count}")
    
    conn.close()

if __name__ == "__main__":
    query_domain_values()
