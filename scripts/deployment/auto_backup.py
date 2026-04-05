#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""èªå¨å¤ä½æå¡"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.storage.database import get_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AutoBackup")

def auto_backup():
    """æè¡èªå¨å¤ä½"""
    logger.info("=" * 60)
    logger.info("ð ååèªå¨å¤ä?..")
    logger.info("=" * 60)

    try:
        db = get_db()
        backup_path = db.backup_database()

        if backup_path:
            logger.info(f"â?å¤ä½æå: {backup_path}")

            cleanup_old_backups()

            return True
        else:
            logger.error("â?å¤ä½å¤±è'¥"')
            return False

    except Exception as e:
        logger.error(f"â?å¤ä½åå¸¸: {e}")
        return False

def cleanup_old_backups(max_age_days: int = 30, max_count: int = 100):
    """æ¸çè¿æå¤ä½æä¶"""
    backup_dir = Path("data/backups")

    if not backup_dir.exists():
        return

    backups = sorted(
        backup_dir.glob("news.db.backup_*"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    deleted_count = 0

    for i, backup in enumerate(backups):
        should_delete = False

        if i >= max_count:
            should_delete = True

        if not should_delete:
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            age = datetime.now() - mtime
            if age.days > max_age_days:
                should_delete = True

        if should_delete:
            try:
                backup.unlink()
                deleted_count += 1
                logger.info(f"ðï¸? å é¤è¿æå¤ä½: {backup.name}")
            except Exception as e:
                logger.warning(f"å é¤å¤ä½å¤±è'¥ {backup.name}: {e}"')

    if deleted_count > 0:
        logger.info(f"æ¸çå®æïå é?{deleted_count} ä¸ªè¿æå¤ä?")

def main():
    """ä¸å½æ?""
    backup_interval = int(os.getenv("BACKUP_INTERVAL", "3600"))

    logger.info("=" * 60)
    logger.info("ð èªå¨å¤ä½æå¡å¯å¨")
    logger.info("=" * 60)
    logger.info(f"å¤ä½é'é: {backup_interval} ç?({backup_interval / 3600:.1f} å°æ¶)"')

    auto_backup()

    schedule.every(backup_interval).seconds.do(auto_backup)

    schedule.every().day.at("00:00").do(auto_backup)
    schedule.every().day.at("12:00").do(auto_backup)

    logger.info("ð å®æ¶å¤ä½è®¡å:")
    logger.info("  - æ¯å¤©åæ¨ 00:00")
    logger.info("  - æ¯å¤©ä¸­å 12:00")
    logger.info(f"  - æ¯?{backup_interval / 3600:.1f} å°æ¶")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("\nð å¤ä½æå¡å·²åæ­?")

if __name__ == "__main__":
    main()

"""
    backup_interval = int(os.getenv("BACKUP_INTERVAL", "3600"))

    logger.info("=" * 60)
    logger.info("ð èªå¨å¤ä½æå¡å¯å¨")
    logger.info("=" * 60)
    logger.info(f"å¤ä½é'é: {backup_interval} ç?({backup_interval / 3600:.1f} å°æ¶)"')

    auto_backup()

    schedule.every(backup_interval).seconds.do(auto_backup)

    schedule.every().day.at("00:00").do(auto_backup)
    schedule.every().day.at("12:00").do(auto_backup)

    logger.info("ð å®æ¶å¤ä½è®¡å:")
    logger.info("  - æ¯å¤©åæ¨ 00:00")
    logger.info("  - æ¯å¤©ä¸­å 12:00")
    logger.info(f"  - æ¯?{backup_interval / 3600:.1f} å°æ¶")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("\nð å¤ä½æå¡å·²åæ­?")

if __name__ == "__main__":
    main()
