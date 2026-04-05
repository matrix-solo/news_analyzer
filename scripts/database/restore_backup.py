#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""å¤ä½æå¤èæ¬"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

def list_backups() -> list:
    """ååºææå¯ç¨å¤ä?""
    backup_dir = Path("data/backups")

    if not backup_dir.exists():
        return []

    backups = sorted(
        backup_dir.glob("news.db.backup_*"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    return backups

def restore_backup(backup_file: Path, force: bool = False) -> bool:
    """äå¤ä½æå¤æ°æ®åº"""
    if not backup_file.exists():
        print(f"â?å¤ä½æä¶ä¸å­å? {backup_file}")
        return False

    db_path = Path("data/news.db")

    if db_path.exists() and not force:
        print(f"â ï¸  æ°æ®åºæä¶å·²å­å¨: {db_path}")
        print("ä½¿ç¨ --force åæ°åºå¶è¦ç")
        return False

    try:
        if db_path.exists():
            corrupt_path = db_path.parent / f"{db_path.name}.corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(db_path), str(corrupt_path))
            print(f"ð¦ å·²å°åæ°æ®åºçå¨å? {corrupt_path}")

        shutil.copy2(backup_file, db_path)

        print(f"â?æ°æ®åºæå¤æå? {backup_file}")
        print(f"   æå¤å? {db_path}")

        backup_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        print(f"   å¤ä½æ¶é': {backup_time.strftime('%Y-%m-%d %H:%M:%S')}"')
        print(f"   æä¶å¤å°: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")

        return True

    except Exception as e:
        print(f"â?æå¤å¤±è'¥: {e}"')
        return False

def main():
    """ä¸å½æ?""
    parser = argparse.ArgumentParser(description="æ°æ®åºå¤ä½æå¤å·¥å?")
    parser.add_argument("--list", action="store_true", help="ååºææå¯ç¨å¤ä?")
    parser.add_argument("--latest", action="store_true", help="ä½¿ç¨ææ°å¤ä½æå¤?")
    parser.add_argument("--file", type=str, help="æå®å¤ä½æä¶è·¯å¾")
    parser.add_argument("--force", action="store_true", help="åºå¶è¦çç°ææ°æ®åº?")

    args = parser.parse_args()

    print("=" * 60)
    print("ð æ°æ®åºå¤ä½æå¤å·¥å?")
    print("=" * 60)

    if args.list:
        backups = list_backups()

        if not backups:
            print("â?æ²¡ææ¾å°å¤ä½æä¶")
            return 1

        print(f"\næ¾å° {len(backups)} ä¸ªå¤ä½æä?\n")
        print(f"{'åºå·':<6} {'æä¶å?:<40} {'å¤å°':<12} {'æ¶é''}")
        print("-" * 80)

        for i, backup in enumerate(backups, 1):
            size = backup.stat().st_size / 1024 / 1024
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{i:<6} {backup.name:<40} {size:>8.2f} MB  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        return 0

    backup_file = None

    if args.latest:
        backups = list_backups()
        if backups:
            backup_file = backups[0]
            print(f"ð ä½¿ç¨ææ°å¤ä? {backup_file.name}")
        else:
            print("â?æ²¡ææ¾å°å¤ä½æä¶")
            return 1

    elif args.file:
        backup_file = Path(args.file)
        if not backup_file.exists():
            backup_dir = Path("data/backups")
            backup_file = backup_dir / args.file

            if not backup_file.exists():
                print(f"â?å¤ä½æä¶ä¸å­å? {args.file}")
                return 1

    else:
        print("è¯·æå®æå¤æå?")
        print("  --latest    ä½¿ç¨ææ°å¤ä?")
        print("  --file FILE æå®å¤ä½æä¶")
        print("  --list      ååºææå¤ä?")
        return 1

    print(f"\nåå¤äå¤ä½æå¤? {backup_file}")
    print(f"å¤ä½æ¶é': {datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"')
    print(f"æä¶å¤å°: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")

    if not args.force:
        confirm = input("\nç¡®è®¤æå¤? (y/N): ")
        if confirm.lower() != 'y':
            print("â?å·²åæ¶æå¤?")
            return 1

    success = restore_backup(backup_file, force=args.force)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

"""
    parser = argparse.ArgumentParser(description="æ°æ®åºå¤ä½æå¤å·¥å?")
    parser.add_argument("--list", action="store_true", help="ååºææå¯ç¨å¤ä?")
    parser.add_argument("--latest", action="store_true", help="ä½¿ç¨ææ°å¤ä½æå¤?")
    parser.add_argument("--file", type=str, help="æå®å¤ä½æä¶è·¯å¾")
    parser.add_argument("--force", action="store_true", help="åºå¶è¦çç°ææ°æ®åº?")

    args = parser.parse_args()

    print("=" * 60)
    print("ð æ°æ®åºå¤ä½æå¤å·¥å?")
    print("=" * 60)

    if args.list:
        backups = list_backups()

        if not backups:
            print("â?æ²¡ææ¾å°å¤ä½æä¶")
            return 1

        print(f"\næ¾å° {len(backups)} ä¸ªå¤ä½æä?\n")
        print(f"{'åºå·':<6} {'æä¶å?:<40} {'å¤å°':<12} {'æ¶é''}")
        print("-" * 80)

        for i, backup in enumerate(backups, 1):
            size = backup.stat().st_size / 1024 / 1024
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{i:<6} {backup.name:<40} {size:>8.2f} MB  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        return 0

    backup_file = None

    if args.latest:
        backups = list_backups()
        if backups:
            backup_file = backups[0]
            print(f"ð ä½¿ç¨ææ°å¤ä? {backup_file.name}")
        else:
            print("â?æ²¡ææ¾å°å¤ä½æä¶")
            return 1

    elif args.file:
        backup_file = Path(args.file)
        if not backup_file.exists():
            backup_dir = Path("data/backups")
            backup_file = backup_dir / args.file

            if not backup_file.exists():
                print(f"â?å¤ä½æä¶ä¸å­å? {args.file}")
                return 1

    else:
        print("è¯·æå®æå¤æå?")
        print("  --latest    ä½¿ç¨ææ°å¤ä?")
        print("  --file FILE æå®å¤ä½æä¶")
        print("  --list      ååºææå¤ä?")
        return 1

    print(f"\nåå¤äå¤ä½æå¤? {backup_file}")
    print(f"å¤ä½æ¶é': {datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"')
    print(f"æä¶å¤å°: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")

    if not args.force:
        confirm = input("\nç¡®è®¤æå¤? (y/N): ")
        if confirm.lower() != 'y':
            print("â?å·²åæ¶æå¤?")
            return 1

    success = restore_backup(backup_file, force=args.force)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
