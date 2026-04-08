#!/usr/bin/env python3
"""
缓存健康检查脚本
用于验证GitHub Actions环境中数据库持久化的正确性

使用方式:
    python scripts/cache_health_check.py

返回码:
    0 - 健康
    1 - 存在问题
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime


def get_db_path():
    """获取数据库路径"""
    project_root = Path(__file__).parent.parent
    return project_root / "data" / "news.db"


def check_database_exists():
    """检查数据库文件是否存在"""
    db_path = get_db_path()
    if not db_path.exists():
        print("[FAIL] 数据库文件不存在")
        return False, 0

    size_mb = db_path.stat().st_size / 1024 / 1024
    print(f"[OK] 数据库文件存在: {size_mb:.1f}MB")
    return True, size_mb


def check_table_consistency(conn):
    """检查表数据一致性"""
    cursor = conn.cursor()
    issues = []

    # 检查1: news 表 vs processed_news 表
    cursor.execute("SELECT COUNT(*) FROM news")
    news_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM processed_news")
    processed_count = cursor.fetchone()[0]

    if news_count != processed_count:
        diff = abs(news_count - processed_count)
        issues.append(f"news({news_count}) vs processed_news({processed_count}) 不一致, 差值={diff}")
    else:
        print(f"[OK] 表一致性: news={news_count}, processed_news={processed_count}")

    # 检查2: 大量未处理raw_news
    cursor.execute("SELECT COUNT(*) FROM raw_news WHERE processed = 0")
    unprocessed_raw = cursor.fetchone()[0]

    if unprocessed_raw > 100:
        issues.append(f"未处理raw_news过多: {unprocessed_raw}条")
    else:
        print(f"[OK] 未处理raw_news: {unprocessed_raw}条")

    # 检查3: 最近24小时新闻量异常
    cursor.execute("""
        SELECT COUNT(*) FROM news
        WHERE pub_date >= datetime('now', '-24 hours')
    """)
    recent_count = cursor.fetchone()[0]

    if recent_count > 500:  # 正常每天100-300条
        issues.append(f"24小时内新闻量异常: {recent_count}条")
    else:
        print(f"[OK] 24小时新闻量: {recent_count}条")

    return issues


def check_duplicate_news(conn):
    """检查重复新闻"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, link, COUNT(*) as cnt
        FROM news
        WHERE pub_date >= datetime('now', '-7 days')
        GROUP BY title, link
        HAVING cnt > 1
        ORDER BY cnt DESC
        LIMIT 5
    """)

    duplicates = cursor.fetchall()
    if duplicates:
        print(f"[WARN] 发现 {len(duplicates)} 组重复新闻:")
        for row in duplicates:
            print(f"  - [{row[2]}次] {row[0][:40]}...")
        return True
    else:
        print("[OK] 未发现重复新闻")
        return False


def check_indexes(conn):
    """检查关键索引是否存在"""
    cursor = conn.cursor()

    required_indexes = [
        'idx_pub_date',
        'idx_processed_at',
        'idx_raw_news_processed'
    ]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing = {row[0] for row in cursor.fetchall()}

    missing = set(required_indexes) - existing
    if missing:
        print(f"[FAIL] 缺失索引: {missing}")
        return False
    else:
        print(f"[OK] 关键索引检查通过")
        return True


def main():
    """主函数"""
    print("=" * 70)
    print(f"[缓存健康检查] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. 检查数据库文件
    exists, size = check_database_exists()
    if not exists:
        return 1

    # 2. 连接数据库
    try:
        conn = sqlite3.connect(str(get_db_path()))
    except sqlite3.Error as e:
        print(f"[FAIL] 数据库连接失败: {e}")
        return 1

    try:
        # 3. 检查表一致性
        print("\n[表一致性检查]")
        issues = check_table_consistency(conn)

        # 4. 检查重复新闻
        print("\n[重复新闻检查]")
        has_duplicates = check_duplicate_news(conn)

        # 5. 检查索引
        print("\n[索引检查]")
        indexes_ok = check_indexes(conn)

        # 汇总
        print("\n" + "=" * 70)
        if issues or has_duplicates or not indexes_ok:
            print("[FAIL] 健康检查未通过")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("[OK] 健康检查通过")
            print(f"  数据库大小: {size:.1f}MB")
            return 0

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
