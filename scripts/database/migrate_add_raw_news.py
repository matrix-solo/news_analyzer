#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 raw_news 表和 news.raw_news_id 字段

运行方式：
    python scripts/database/migrate_add_raw_news.py
"""

import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def migrate_database(db_path: str = None):
    """执行数据库迁移"""
    if db_path is None:
        db_path = project_root / "data" / "news.db"
    
    print(f"数据库路径: {db_path}")
    
    if not Path(db_path).exists():
        print("数据库文件不存在，将自动创建")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_news'")
        if cursor.fetchone():
            print("raw_news 表已存在，跳过创建")
        else:
            print("创建 raw_news 表...")
            cursor.execute('''
                CREATE TABLE raw_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    news_id TEXT UNIQUE,
                    raw_json TEXT NOT NULL,
                    source_name TEXT,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_news_fetched_at ON raw_news(fetched_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_news_processed ON raw_news(processed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_news_source ON raw_news(source_name)')
            print("raw_news 表创建成功")
        
        cursor.execute("PRAGMA table_info(news)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'raw_news_id' in columns:
            print("news.raw_news_id 字段已存在，跳过添加")
        else:
            print("添加 news.raw_news_id 字段...")
            cursor.execute('ALTER TABLE news ADD COLUMN raw_news_id INTEGER')
            print("news.raw_news_id 字段添加成功")
        
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
    parser = argparse.ArgumentParser(description="数据库迁移：添加 raw_news 表")
    parser.add_argument("--db", type=str, help="数据库路径")
    args = parser.parse_args()
    
    migrate_database(args.db)
