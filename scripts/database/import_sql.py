#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
å¯å¥SQLæä¶å°æ°æ°æ®åº?V3 - ç²¾ç¡®è¿æ¤FTSè¯­å¥
"""

import sqlite3
import os
import shutil
from datetime import datetime

def import_sql_v3():
    data_dir = r'c:\Users\matrix\Desktop\news_workflow\news_analyzer\data'
    sql_path = os.path.join(data_dir, 'news_export.sql')
    new_db_path = os.path.join(data_dir, 'news.db.new')
    db_path = os.path.join(data_dir, 'news.db')

    print(f"è¯åSQL: {sql_path}")

    # è¯åSQL
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # åå²æè¯­å?    statements = sql_content.split(';')

    # è¿æ¤æFTSç¸å³è¯­å¥
    filtered_statements = []
    for stmt in statements:
        stmt_stripped = stmt.strip()
        if not stmt_stripped:
            continue

        # æ£æ¥æ¯å¦åå«FTSå³é®å­?        stmt_lower = stmt_stripped.lower()
        if any(keyword in stmt_lower for keyword in [
            'news_fts', 'virtual table', 'fts5', 'processed_news'
        ]):
            print(f"è·³è¿FTSè¯­å¥: {stmt_stripped[:60]}...")
            continue

        filtered_statements.append(stmt_stripped)

    # éæ°çè£SQL
    filtered_sql = ';\n'.join(filtered_statements) + ';'

    # ååºæ°æ°æ®åº
    conn = sqlite3.connect(new_db_path)

    try:
        # æè¡è¿æ¤åçSQL
        conn.executescript(filtered_sql)
        print("â?åºç¡è¡¨ååºæå?")

        # ååºè¾å©è¡?        cursor = conn.cursor()

        # ååºprocessed_newsè¡?        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_news (
                news_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("â?processed_newsè¡¨ååºæå?")

        # ååºFTSèæè¡?        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                title, translated_title, content,
                content_rowid=rowid
            )
        ''')
        print("â?news_ftsèæè¡¨ååºæå?")

        # å¡«åFTSè¡?        cursor.execute('''
            INSERT INTO news_fts(rowid, title, translated_title, content)
            SELECT rowid, title, translated_title, content FROM news
        ''')
        print("â?FTSè¡¨æ°æ®å¡«åå®æ?")

        conn.commit()
        conn.close()
        print(f"â?æ°æ°æ®åºååºæå: {new_db_path}")

        # å¤ä½ææ°æ®åº
        if os.path.exists(db_path):
            backup_name = f'news.db.corrupt_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            backup_path = os.path.join(data_dir, backup_name)
            shutil.move(db_path, backup_path)
            print(f"â?ææ°æ®åºå·²å¤ä? {backup_path}")

        # æ¿æä¸ºæ°æ°æ®åº?        shutil.move(new_db_path, db_path)
        print(f"â?æ°æ®åºå·²æ¿æ: {db_path}")

        # å é¤ä¸'æ¶SQLæä¶
        os.remove(sql_path)
        print("â?ä¸'æ¶æä¶å·²æ¸ç?"')

        print("\nâ?æ°æ®åºéåºå®æï")
        return True

    except Exception as e:
        print(f"\nâ?å¯å¥å¤±è'¥: {e}"')
        import traceback
        traceback.print_exc()
        conn.close()
        return False

if __name__ == "__main__":
    import_sql_v3()
