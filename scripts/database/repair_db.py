#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ä¿®å¤æåçSQLiteæ°æ®åº?""

import sqlite3
import os
import shutil
from datetime import datetime

def repair_db():
    db_path = r'c:\Users\matrix\Desktop\news_workflow\news_analyzer\data\news.db'
    backup_path = f'{db_path}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    print(f"æ°æ®åºè·¯å¾? {db_path}")

    # å¤ä½åæ°æ®åº
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"å·²å¤ä½å°: {backup_path}")

    # å°è¯ä¿®å¤
    try:
        # ææ³1: ä½¿ç¨PRAGMA integrity_check
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("æè¡å®æ'ææ£æ?.."')
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        print(f"å®æ'ææ£æ¥çæ? {result[0]}"')

        # ææ³2: å¯åºå¶éæ°å¯å?        if result[0] != 'ok':
            print("æ°æ®åºæåïå°è¯å¯åºå¶éæ°å¯å?..")

            new_db_path = db_path + '.new'

            # å¯åºSQL
            with open(db_path + '.sql', 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(line + '\n')

            print("SQLå¯åºå®æ")

            # ååºæ°æ°æ®åº
            new_conn = sqlite3.connect(new_db_path)
            with open(db_path + '.sql', 'r', encoding='utf-8') as f:
                new_conn.executescript(f.read())
            new_conn.close()

            print("æ°æ°æ®åºååºå®æ")

            # æ¿æåæ°æ®åº
            conn.close()
            os.remove(db_path)
            shutil.move(new_db_path, db_path)

            print("æ°æ®åºå·²æ¿æ")
        else:
            print("æ°æ®åºå®æ'ææ­£å¸?"')

        conn.close()

    except Exception as e:
        print(f"ä¿®å¤å¤±è'¥: {e}"')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    repair_db()

"""

import sqlite3
import os
import shutil
from datetime import datetime

def repair_db():
    db_path = r'c:\Users\matrix\Desktop\news_workflow\news_analyzer\data\news.db'
    backup_path = f'{db_path}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    print(f"æ°æ®åºè·¯å¾? {db_path}")

    # å¤ä½åæ°æ®åº
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"å·²å¤ä½å°: {backup_path}")

    # å°è¯ä¿®å¤
    try:
        # ææ³1: ä½¿ç¨PRAGMA integrity_check
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("æè¡å®æ'ææ£æ?.."')
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        print(f"å®æ'ææ£æ¥çæ? {result[0]}"')

        # ææ³2: å¯åºå¶éæ°å¯å?        if result[0] != 'ok':
            print("æ°æ®åºæåïå°è¯å¯åºå¶éæ°å¯å?..")

            new_db_path = db_path + '.new'

            # å¯åºSQL
            with open(db_path + '.sql', 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(line + '\n')

            print("SQLå¯åºå®æ")

            # ååºæ°æ°æ®åº
            new_conn = sqlite3.connect(new_db_path)
            with open(db_path + '.sql', 'r', encoding='utf-8') as f:
                new_conn.executescript(f.read())
            new_conn.close()

            print("æ°æ°æ®åºååºå®æ")

            # æ¿æåæ°æ®åº
            conn.close()
            os.remove(db_path)
            shutil.move(new_db_path, db_path)

            print("æ°æ®åºå·²æ¿æ")
        else:
            print("æ°æ®åºå®æ'ææ­£å¸?"')

        conn.close()

    except Exception as e:
        print(f"ä¿®å¤å¤±è'¥: {e}"')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    repair_db()
