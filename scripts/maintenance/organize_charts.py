#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ¸çåå²å¾è¡¨æä¶
å°?reports/charts/ ä¸­çæå¾è¡¨ææ¥æéæ°ççå°å¯åºæ¥æç®å½ä¸
"""

import re
import shutil
from pathlib import Path
from datetime import datetime

def parse_date_from_filename(filename: str) -> str:
    """äæä¶åä¸­è£ææ¥æ?""
    # åéæ å: 20260312 æ?2026-03-12
    patterns = [
        r'(\d{4})(\d{2})(\d{2})',  # 20260312
        r'(\d{4})-(\d{2})-(\d{2})',  # 2026-03-12
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month}-{day}"

    return None

def organize_charts(dry_run: bool = True):
    """
    æ'çå¾è¡¨æä¶'

    Args:
        dry_run: å¦æä¸ºTrueïåªæ¾ç¤ºå°è¦æè¡çæä½ïä¸å®éçå¨æä?    """"
    # è·åé¡ç®æ ç®å½ïèæ¬å?scripts/ å­ç®å½ä¸ï?    script_dir = Path(__file__).parent
    reports_dir = script_dir.parent / "reports"
    old_charts_dir = reports_dir / "charts"

    if not old_charts_dir.exists():
        print("charts ç®å½ä¸å­å¨ïæ éæ¸ç")
        return

    # çè®¡
    moved_count = 0
    skipped_count = 0
    error_count = 0

    # éåææå¾è¡¨æä?    for file_path in old_charts_dir.iterdir():
        if file_path.is_dir():
            continue

        filename = file_path.name
        date_str = parse_date_from_filename(filename)

        if not date_str:
            print(f"  [è·³è¿] æ æ³è£ææ¥æ: {filename}")
            skipped_count += 1
            continue

        # ç®æ ç®å½
        target_dir = reports_dir / date_str / "charts"
        target_path = target_dir / filename

        if target_path.exists():
            print(f"  [è·³è¿] ç®æ å·²å­å? {date_str}/{filename}")
            skipped_count += 1
            continue

        if dry_run:
            print(f"  [å°çå¨] {filename} -> {date_str}/charts/")
            moved_count += 1
        else:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(target_path))
                print(f"  [å·²çå¨] {filename} -> {date_str}/charts/")
                moved_count += 1
            except Exception as e:
                print(f"  [éè¯¯] çå¨å¤±è'¥ {filename}: {e}"')
                error_count += 1

    print()
    print("=" * 50)
    print(f"çè®¡: çå¨ {moved_count} ä¸? è·³è¿ {skipped_count} ä¸? éè¯¯ {error_count} ä¸?")

    if dry_run:
        print()
        print("è¿æ¯éèæ¨¡åïæªå®éçå¨æä¶ã?")
        print("è¦æè¡å®éçå¨ïè¯·è¿è¡? python scripts/organize_charts.py --execute")

def clean_empty_charts_dir():
    """æ¸çç©ºçæ?charts ç®å½"""
    script_dir = Path(__file__).parent
    reports_dir = script_dir.parent / "reports"
    old_charts_dir = reports_dir / "charts"

    if old_charts_dir.exists() and not any(old_charts_dir.iterdir()):
        old_charts_dir.rmdir()
        print("å·²å é¤ç©ºç?charts ç®å½")
    elif old_charts_dir.exists():
        remaining = list(old_charts_dir.iterdir())
        print(f"charts ç®å½äæ {len(remaining)} ä¸ªæä¶ïä¿çç®å½")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="æ'çåå²å¾è¡¨æä¶"')
    parser.add_argument("--execute", action="store_true", 
                        help="æè¡å®éçå¨æä½ïéè®¤åªéèï?")
    parser.add_argument("--clean-empty", action="store_true",
                        help="æ¸çç©ºçæ?charts ç®å½")

    args = parser.parse_args()

    print("=" * 50)
    print("åå²å¾è¡¨æ'çå·¥å·"')
    print("=" * 50)
    print()

    if args.clean_empty:
        clean_empty_charts_dir()
    else:
        organize_charts(dry_run=not args.execute)

        if args.execute:
            clean_empty_charts_dir()

if __name__ == "__main__":
    main()
