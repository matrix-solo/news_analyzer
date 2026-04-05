#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ç®åæå¤æ°æ®åº - ä½¿ç¨sqlite3å½ä¤è¡?""""

import subprocess
import os
import shutil
from datetime import datetime

def restore_db_simple():
    data_dir = r'c:\Users\matrix\Desktop\news_workflow\news_analyzer\data'
    sql_path = os.path.join(data_dir, 'news_export.sql')
    new_db_path = os.path.join(data_dir, 'news.db.new')
    db_path = os.path.join(data_dir, 'news.db')

    print(f"ä½¿ç¨sqlite3å¯å¥SQL...")

    # ä½¿ç¨sqlite3å½ä¤è¡å¯å?    # æ³¨æïWindowsä¸éè¦ä½¿ç¨cmd /c
    cmd = f'sqlite3 "{new_db_path}" ".read {sql_path}"'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print(f"â?SQLå¯å¥æå")

            # å¤ä½ææ°æ®åº
            if os.path.exists(db_path):
                backup_name = f'news.db.corrupt_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                backup_path = os.path.join(data_dir, backup_name)
                shutil.move(db_path, backup_path)
                print(f"â?ææ°æ®åºå·²å¤ä? {backup_path}")

            # æ¿æä¸ºæ°æ°æ®åº?            shutil.move(new_db_path, db_path)
            print(f"â?æ°æ®åºå·²æ¿æ: {db_path}")

            # å é¤ä¸'æ¶SQLæä¶
            os.remove(sql_path)
            print("â?ä¸'æ¶æä¶å·²æ¸ç?"')

            print("\nâ?æ°æ®åºéåºå®æï")
            return True
        else:
            print(f"â?å¯å¥å¤±è'¥: {result.stderr}"')
            return False

    except Exception as e:
        print(f"â?éè¯¯: {e}")
        return False

if __name__ == "__main__":
    restore_db_simple()

"""

import subprocess
import os
import shutil
from datetime import datetime

def restore_db_simple():
    data_dir = r'c:\Users\matrix\Desktop\news_workflow\news_analyzer\data'
    sql_path = os.path.join(data_dir, 'news_export.sql')
    new_db_path = os.path.join(data_dir, 'news.db.new')
    db_path = os.path.join(data_dir, 'news.db')

    print(f"ä½¿ç¨sqlite3å¯å¥SQL...")

    # ä½¿ç¨sqlite3å½ä¤è¡å¯å?    # æ³¨æïWindowsä¸éè¦ä½¿ç¨cmd /c
    cmd = f'sqlite3 "{new_db_path}" ".read {sql_path}"'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print(f"â?SQLå¯å¥æå")

            # å¤ä½ææ°æ®åº
            if os.path.exists(db_path):
                backup_name = f'news.db.corrupt_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                backup_path = os.path.join(data_dir, backup_name)
                shutil.move(db_path, backup_path)
                print(f"â?ææ°æ®åºå·²å¤ä? {backup_path}")

            # æ¿æä¸ºæ°æ°æ®åº?            shutil.move(new_db_path, db_path)
            print(f"â?æ°æ®åºå·²æ¿æ: {db_path}")

            # å é¤ä¸'æ¶SQLæä¶
            os.remove(sql_path)
            print("â?ä¸'æ¶æä¶å·²æ¸ç?"')

            print("\nâ?æ°æ®åºéåºå®æï")
            return True
        else:
            print(f"â?å¯å¥å¤±è'¥: {result.stderr}"')
            return False

    except Exception as e:
        print(f"â?éè¯¯: {e}")
        return False

if __name__ == "__main__":
    restore_db_simple()
