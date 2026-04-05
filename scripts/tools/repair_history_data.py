#!/usr/bin/env python3
"""
历史数据修复脚本

功能：
1. 校验 5W1H、评分等字段是否存在（NULL检查）
2. 对未通过校验的数据标记为 force_stored
3. 下次 Task1 运行时会自动修复这些数据
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from pathlib import Path


def is_empty_value(value):
    """检查字段是否为空（None 或空字符串）"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def validate_record(news):
    """验证单条新闻记录 - 检查必要字段是否为NULL"""
    issues = []

    w5h1_fields = ['who', 'what', 'when_time', 'where_place', 'why', 'how']
    for field in w5h1_fields:
        if news.get(field) is None:
            issues.append(f'缺失: {field}')

    required_scores = ['final_score', 'influence_score', 'value_score', 'source_score', 'heat_score']
    for field in required_scores:
        if news.get(field) is None:
            issues.append(f'缺失: {field}')

    return issues


def repair_database(db_path, dry_run=False):
    """修复数据库"""
    print(f"数据库: {db_path}")
    print(f"模式: {'模拟' if dry_run else '执行'}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, combined_processing_status, validation_status
        FROM news
        WHERE combined_processing_status IS NULL
           OR who IS NULL
           OR what IS NULL
           OR when_time IS NULL
           OR where_place IS NULL
           OR why IS NULL
           OR how IS NULL
    ''')
    records = cursor.fetchall()

    print(f"\n需要检查的记录: {len(records)} 条")

    stats = {
        'total': len(records),
        'need_repair': 0,
        'already_passed': 0,
        'repaired': 0,
    }

    # 第一步：标记需要修复的 NULL 数据
    for row_id, title, status, validation in records:
        cursor.execute('SELECT * FROM news WHERE id = ?', (row_id,))
        news = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

        issues = validate_record(news)

        if issues:
            stats['need_repair'] += 1
            if stats['need_repair'] <= 10:
                print(f"\n  需要修复 [{row_id[:8]}]: {title[:40]}...")
                for issue in issues:
                    print(f"    - {issue}")

            if not dry_run:
                cursor.execute('''
                    UPDATE news
                    SET combined_processing_status = 'force_stored',
                        validation_status = 'failed'
                    WHERE id = ?
                ''', (row_id,))
                stats['repaired'] += 1
        else:
            stats['already_passed'] += 1
            if status != 'passed':
                if not dry_run:
                    cursor.execute('''
                        UPDATE news
                        SET combined_processing_status = 'passed',
                            validation_status = 'passed'
                        WHERE id = ?
                    ''', (row_id,))

    # 第二步：清除误标（之前标记为 force_stored 但现在验证通过的）
    if not dry_run:
        cursor.execute('''
            UPDATE news
            SET combined_processing_status = 'passed',
                validation_status = 'passed'
            WHERE combined_processing_status = 'force_stored'
              AND who IS NOT NULL AND what IS NOT NULL AND when_time IS NOT NULL
              AND where_place IS NOT NULL AND why IS NOT NULL AND how IS NOT NULL
        ''')
        fixed_wrong_mark = cursor.rowcount
        print(f"\n  清除误标: {fixed_wrong_mark} 条")
        stats['fixed_wrong_mark'] = fixed_wrong_mark

    if stats['need_repair'] > 10:
        print(f"\n  ... 还有 {stats['need_repair'] - 10} 条类似问题")

    conn.commit()
    conn.close()

    print(f"\n统计:")
    print(f"  总数: {stats['total']}")
    print(f"  需要修复: {stats['need_repair']}")
    print(f"  已通过: {stats['already_passed']}")
    print(f"  实际修复: {stats['repaired']}")
    if 'fixed_wrong_mark' in stats:
        print(f"  清除误标: {stats['fixed_wrong_mark']}")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description='历史数据修复脚本')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际修改')
    parser.add_argument('--db', default='data/news.db', help='数据库路径')

    args = parser.parse_args()

    db_path = Path(__file__).parent.parent.parent / args.db
    if not db_path.exists():
        print(f"错误: 数据库不存在 {db_path}")
        return 1

    print("=" * 60)
    print("历史数据修复脚本")
    print("=" * 60)

    stats = repair_database(db_path, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("模拟运行完成，使用 --dry-run 确认后可执行实际修复")
    else:
        print("修复完成")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())