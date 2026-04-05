#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浠庢崯鍧忕殑鏁版嵁搴撲腑瀵煎嚭鏁版嵁骞堕噸寤?V2
"""

import sqlite3
import os
import shutil
import re
from datetime import datetime

def export_and_rebuild_v2():
    data_dir = r'c:\Users\matrix\Desktop\news_workflow\news_analyzer\data'
    db_path = os.path.join(data_dir, 'news.db')

    # 浣跨敤鍙妯″紡灏濊瘯璇诲彇
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        print("鎴愬姛浠ュ彧璇绘ā寮忚繛鎺ユ暟鎹簱")

        # 瀵煎嚭SQL
        sql_path = os.path.join(data_dir, 'news_export.sql')
        with open(sql_path, 'w', encoding='utf-8') as f:
            for line in conn.iterdump():
                f.write(line + '\n')

        print(f"SQL瀵煎嚭瀹屾垚: {sql_path}")
        conn.close()

        # 璇诲彇SQL骞惰繃婊?        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 杩囨护鎺塅TS鍜宲rocessed_news鐩稿叧璇彞
        # 浣跨敤鏇寸簿纭殑姝ｅ垯琛ㄨ揪寮?        filtered_lines = []
        skip_patterns = [
            r'CREATE VIRTUAL TABLE',
            r'CREATE TABLE.*processed_news',
            r'INSERT INTO.*processed_news',
            r'INSERT INTO.*news_fts',
        ]

        for line in sql_content.split('\n'):
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break
            if not should_skip:
                filtered_lines.append(line)

        filtered_sql = '\n'.join(filtered_lines)

        # 鍒涘缓鏂版暟鎹簱
        new_db_path = os.path.join(data_dir, 'news.db.new')
        new_conn = sqlite3.connect(new_db_path)

        # 鎵ц杩囨护鍚庣殑SQL
        new_conn.executescript(filtered_sql)
        new_conn.close()

        print(f"鏂版暟鎹簱鍒涘缓瀹屾垚: {new_db_path}")

        # 澶囦唤鏃ф暟鎹簱
        backup_name = f'news.db.corrupt_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        backup_path = os.path.join(data_dir, backup_name)
        shutil.move(db_path, backup_path)
        print(f"鏃ф暟鎹簱宸插浠? {backup_path}")

        # 鏇挎崲涓烘柊鏁版嵁搴?        shutil.move(new_db_path, db_path)
        print(f"鏁版嵁搴撳凡鏇挎崲涓? {db_path}")

        # 閲嶆柊鍒涘缓FTS琛ㄥ拰processed_news琛?        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 鍒涘缓processed_news琛?        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_news (
                news_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 鍒涘缓FTS琛?        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                title, translated_title, content,
                content_rowid=rowid
            )
        ''')

        # 濉厖FTS琛?        cursor.execute('''
            INSERT INTO news_fts(rowid, title, translated_title, content)
            SELECT rowid, title, translated_title, content FROM news
        ''')

        conn.commit()
        conn.close()
        print("杈呭姪琛ㄩ噸寤哄畬鎴?")

        # 鍒犻櫎涓存椂SQL鏂囦欢
        os.remove(sql_path)

        print("\n鏁版嵁搴撻噸寤烘垚鍔燂紒")
        return True

    except Exception as e:
        print(f"瀵煎嚭澶辫触: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    export_and_rebuild_v2()
