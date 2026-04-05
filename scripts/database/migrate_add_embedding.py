#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ°æ®åºè¿çèæ¬ïæ·å embeddingå­æ®µ
ç¨äºå­å¨BGE-M3åéï?024ç'æµ®çæ°ï?""""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'news.db')

def migrate():
    """æ·å embeddingå­æ®µ"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # æ£æ¥å­æ®µæ¯å¦å·²å­å¨
    cursor.execute("PRAGMA table_info(news)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'embedding' not in columns:
        print("æ·å embeddingå­æ®µ...")
        cursor.execute("ALTER TABLE news ADD COLUMN embedding BLOB")
        conn.commit()
        print("â?embeddingå­æ®µæ·å æå")
    else:
        print("embeddingå­æ®µå·²å­å¨ïè·³è¿")

    # æ£æ¥embedding_updated_atå­æ®µ
    if 'embedding_updated_at' not in columns:
        print("æ·å embedding_updated_atå­æ®µ...")
        cursor.execute("ALTER TABLE news ADD COLUMN embedding_updated_at DATETIME")
        conn.commit()
        print("â?embedding_updated_atå­æ®µæ·å æå")
    else:
        print("embedding_updated_atå­æ®µå·²å­å¨ïè·³è¿")

    conn.close()
    print("\nè¿çå®æï?")

if __name__ == '__main__':
    migrate()
