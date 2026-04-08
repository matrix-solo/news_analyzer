#!/usr/bin/env python3
"""
重复新闻检查脚本
用于监控数据库中的重复情况
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

def get_db_path():
    """获取数据库路径"""
    project_root = Path(__file__).parent.parent
    return project_root / "data" / "news.db"

def check_duplicates():
    """检查重复新闻统计"""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print(f"[重复新闻检查报告] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. 总体统计
    print("\n[总体统计]")
    cursor.execute("SELECT COUNT(*) as total FROM news")
    total_news = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM processed_news")
    total_processed = cursor.fetchone()['total']

    # 获取raw_news统计
    cursor.execute("SELECT COUNT(*) as total FROM raw_news WHERE processed = 0")
    unprocessed_raw = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM raw_news WHERE processed = 0")
    unprocessed_raw = cursor.fetchone()['total']

    print(f"  - news表总记录数: {total_news}")
    print(f"  - processed_news表记录数: {total_processed}")
    print(f"  - raw_news未处理: {unprocessed_raw}")

    if total_news != total_processed:
        print(f"  [警告] news表与processed_news表数量不一致！")
        print(f"     差值: {abs(total_news - total_processed)}")

    # 2. 24小时内新闻统计
    print("\n[日期统计] 最近24小时新闻统计:")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT title) as unique_titles,
            COUNT(DISTINCT link) as unique_links
        FROM news
        WHERE pub_date >= datetime('now', '-24 hours')
    """)
    row = cursor.fetchone()
    print(f"  - 总记录数: {row['total']}")
    print(f"  - 唯一标题数: {row['unique_titles']}")
    print(f"  - 唯一链接数: {row['unique_links']}")

    if row['total'] != row['unique_titles']:
        duplicate_rate = (row['total'] - row['unique_titles']) / row['total'] * 100
        print(f"  [警告]  标题重复率: {duplicate_rate:.1f}%")

    # 3. 查找具体重复项
    print("\n[详情检查] 最近24小时重复新闻详情:")
    cursor.execute("""
        SELECT
            title,
            link,
            COUNT(*) as count,
            MIN(pub_date) as first_seen,
            MAX(pub_date) as last_seen
        FROM news
        WHERE pub_date >= datetime('now', '-24 hours')
        GROUP BY title, link
        HAVING COUNT(*) > 1
        ORDER BY count DESC, first_seen DESC
        LIMIT 10
    """)

    duplicates = cursor.fetchall()
    if duplicates:
        print(f"  发现 {len(duplicates)} 组重复新闻:")
        for row in duplicates:
            print(f"  - [{row['count']}次] {row['title'][:50]}...")
            print(f"    首次: {row['first_seen']}, 最后: {row['last_seen']}")
    else:
        print("  [OK] 未发现重复新闻")

    # 4. 检查processed_news遗漏
    print("\n[详情检查] processed_news表遗漏检查:")
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM news n
        LEFT JOIN processed_news p ON n.id = p.news_id
        WHERE p.news_id IS NULL
    """)
    missing_count = cursor.fetchone()['count']
    if missing_count > 0:
        print(f"  [警告]  发现 {missing_count} 条新闻在news表但不在processed_news表")
        print(f"     这可能导致这些新闻被重复采集！")
    else:
        print("  [OK] news表与processed_news表数据一致")

    # 5. 今日任务运行统计
    print("\n[统计] 今日采集统计:")
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT
            source_name,
            COUNT(*) as count,
            MIN(pub_date) as earliest,
            MAX(pub_date) as latest
        FROM news
        WHERE DATE(pub_date) = DATE('now')
        GROUP BY source_name
        ORDER BY count DESC
    """)

    sources = cursor.fetchall()
    if sources:
        for row in sources:
            print(f"  - {row['source_name']}: {row['count']}条")
    else:
        print("  今日暂无采集记录")

    conn.close()

    print("\n" + "=" * 70)
    print("[OK] 检查完成")
    print("=" * 70)

    # 返回码：0=正常, 1=有问题
    return 1 if (missing_count > 0 or len(duplicates) > 0) else 0

if __name__ == "__main__":
    sys.exit(check_duplicates())
