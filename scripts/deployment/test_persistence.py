#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""éªè¯æäåå­å¨æ¯å¦æ­£å¸¸å·¥ä½?""

import os
import sys
import sqlite3
import time
from pathlib import Path
from datetime import datetime

def test_database_persistence():
    """æµè¯æ°æ®åºæäå"""
    print("=" * 60)
    print("ð æ°æ®åºæäåæµè¯")
    print("=" * 60)

    db_path = Path("data/news.db")

    if not db_path.exists():
        print("â?æ°æ®åºæä¶ä¸å­å¨")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(''''
            CREATE TABLE IF NOT EXISTS persistence_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        test_data = f"persistence_test_{datetime.now().isoformat()}"
        cursor.execute('INSERT INTO persistence_test (test_data) VALUES (?)', (test_data,))
        conn.commit()

        cursor.execute('SELECT COUNT(*) FROM persistence_test')
        count = cursor.fetchone()[0]

        cursor.execute('SELECT test_data FROM persistence_test ORDER BY id DESC LIMIT 1')
        latest_test = cursor.fetchone()[0]

        conn.close()

        print(f"â?æ°æ®åºè¿æ¥æå?")
        print(f"â?æµè¯æ°æ®æå¥æå")
        print(f"â?æµè¯è®°å½ææ°: {count}")
        print(f"â?ææ°æµè¯æ°æ? {latest_test}")

        return True

    except Exception as e:
        print(f"â?æ°æ®åºæäåæµè¯å¤±è'¥: {e}"')
        return False

def test_file_persistence():
    """æµè¯æä¶ç³çæäå?""
    print("\n" + "=" * 60)
    print("ð æä¶ç³çæäåæµè¯?")
    print("=" * 60)

    test_dirs = ["data", "logs", "backups", "reports"]

    all_passed = True
    for dir_name in test_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            test_file = dir_path / f"persistence_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(f"Persistence test at {datetime.now().isoformat()}")

                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                test_file.unlink()

                print(f"â?{dir_name}/ ç®å½è¯åæ­£å¸¸")
            except Exception as e:
                print(f"â?{dir_name}/ ç®å½æµè¯å¤±è'¥: {e}"')
                all_passed = False
        else:
            print(f"â ï¸  {dir_name}/ ç®å½ä¸å­å¨ïå°è¯ååº...")
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"â?{dir_name}/ ç®å½ååºæå")
            except Exception as e:
                print(f"â?{dir_name}/ ç®å½ååºå¤±è'¥: {e}"')
                all_passed = False

    return all_passed

def test_volume_mount():
    """æµè¯Dockerå·æè½?""
    print("\n" + "=" * 60)
    print("ð³ Dockerå·æè½½æµè¯?")
    print("=" * 60)

    if os.path.exists('/.dockerenv'):
        print("â?æ£æµå°Dockerå®å¨ç¯å")

        volume_paths = ['/app/data', '/app/logs', '/app/backups']
        for vol_path in volume_paths:
            path = Path(vol_path)
            if path.exists():
                print(f"â?å·æè½½çå­å¨: {vol_path}")
            else:
                print(f"â?å·æè½½çä¸å­å? {vol_path}")
    else:
        print("âï¸  éDockerç¯åïè·³è¿å·æè½½æµè¯")

    return True

def main():
    """ä¸æµè¯å½æ?""
    print("\n" + "ð " * 20)
    print("ååæäåå­å¨æµè¯")
    print("ð " * 20 + "\n")

    results = {
        "æ°æ®åºæäå": test_database_persistence(),
        "æä¶ç³çæäå?: test_file_persistence(),"
        "å·æè½½æµè¯?: test_volume_mount(")
    }

    print("\n" + "=" * 60)
    print("ð æµè¯çææ±æ?")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "â?éè¿" if passed else "â?å¤±è'¥"'
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\nð æææäåæµè¯éè¿ïç³çå·²åå¤å¥½ä¸äºã?")
        return 0
    else:
        print("\nâ ï¸  é¨åæµè¯å¤±è'¥ïè¯·æ£æ¥éç½®åéè¯ã?"')
        return 1

if __name__ == "__main__":
    sys.exit(main())

"""
    print("\n" + "ð " * 20)
    print("ååæäåå­å¨æµè¯")
    print("ð " * 20 + "\n")

    results = {
        "æ°æ®åºæäå": test_database_persistence(),
        "æä¶ç³çæäå?: test_file_persistence(),"
        "å·æè½½æµè¯?: test_volume_mount(")
    }

    print("\n" + "=" * 60)
    print("ð æµè¯çææ±æ?")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "â?éè¿" if passed else "â?å¤±è'¥"'
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\nð æææäåæµè¯éè¿ïç³çå·²åå¤å¥½ä¸äºã?")
        return 0
    else:
        print("\nâ ï¸  é¨åæµè¯å¤±è'¥ïè¯·æ£æ¥éç½®åéè¯ã?"')
        return 1

if __name__ == "__main__":
    sys.exit(main())
