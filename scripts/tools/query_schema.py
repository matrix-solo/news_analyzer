#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询数据库Schema"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "news.db"

def get_schema():
    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"数据库路径: {DB_PATH}")
    print(f"表数量: {len(tables)}")
    print("=" * 80)
    
    for table in tables:
        print(f"\n## 表: {table}")
        print("-" * 60)
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        print("| 字段名 | 类型 | 是否NULL | 默认值 | 主键 |")
        print("|--------|------|----------|--------|------|")
        for col in columns:
            name = col['name']
            dtype = col['type'] or '-'
            notnull = 'NOT NULL' if col['notnull'] else 'NULL'
            default = col['dflt_value'] or '-'
            pk = 'PK' if col['pk'] else ''
            print(f"| {name} | {dtype} | {notnull} | {default} | {pk} |")
        
        # 获取索引
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        if indexes:
            print(f"\n索引:")
            for idx in indexes:
                print(f"  - {idx['name']}")
    
    conn.close()

if __name__ == "__main__":
    get_schema()
