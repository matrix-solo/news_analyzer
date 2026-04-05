#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鏁版嵁搴?Schema 杩佺Щ鑴氭湰锛堝箓绛夊畨鍏級

鏈剼鏈鐜版湁 data/news.db 鍋氫互涓嬪彉鏇达細
  1. news 琛細琛ュ厖 source_reliability_score / extraction_method /
              raw_item_json / access_time 鍥涗釜鏂板瓧娈?
  2. 纭繚 entities / news_entities 涓ゅ紶琛ㄥ凡瀛樺湪锛堣嫢涓嶅瓨鍦ㄥ垯寤虹珛锛?

璁捐鍘熷垯锛?
  - 骞傜瓑锛氬娆℃墽琛屼笉鍑洪敊銆佷笉涓㈡暟鎹?
  - 瀹夊叏锛欰LTER TABLE ADD COLUMN 浠呭湪瀛楁涓嶅瓨鍦ㄦ椂鎵ц
  - 澶囦唤锛氳縼绉诲墠鑷姩澶囦唤鍘熷鏁版嵁搴?
"""

import sqlite3
import sys
import shutil
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migrate_schema")

def _get_existing_columns(conn: sqlite3.Connection, table: str):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}

def _add_column_if_missing(conn: sqlite3.Connection, table: str, col: str, col_def: str):
    existing = _get_existing_columns(conn, table)
    if col not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        logger.info(f"  + 娣诲姞瀛楁: {table}.{col}")
    else:
        logger.info(f"  ~ 瀛楁宸插瓨鍦ㄨ烦杩? {table}.{col}")

def _ensure_entities_tables(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            subtype TEXT,
            normalized_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name, type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type_norm ON entities(type, normalized_name)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            role TEXT,
            weight REAL DEFAULT 1.0,
            extra TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_entities_news_id ON news_entities(news_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_entities_entity_id ON news_entities(entity_id)")
    logger.info("  ~ entities / news_entities 琛ㄥ凡灏辩华")

def migrate(db_path: Path):
    if not db_path.exists():
        logger.warning(f"鏁版嵁搴撲笉瀛樺湪锛岃烦杩囪縼绉? {db_path}")
        return

    # ---- 杩佺Щ鍓嶅浠?----
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"news.db.pre_migrate_{ts}"
    shutil.copy2(db_path, backup_path)
    logger.info(f"澶囦唤瀹屾垚: {backup_path}")

    # ---- 鎵ц杩佺Щ ----
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        logger.info("--- 杩佺Щ news 琛ㄥ瓧娈?---")
        _add_column_if_missing(conn, "news", "source_reliability_score", "REAL")
        _add_column_if_missing(conn, "news", "extraction_method",        "TEXT DEFAULT 'unknown'")
        _add_column_if_missing(conn, "news", "raw_item_json",            "TEXT")
        _add_column_if_missing(conn, "news", "access_time",              "DATETIME")

        logger.info("--- 纭繚鐭ヨ瘑鍥捐氨棰勭暀琛?---")
        _ensure_entities_tables(conn)

        conn.commit()
        logger.info("杩佺Щ瀹屾垚 鉁?")
    except Exception as e:
        conn.rollback()
        logger.error(f"杩佺Щ澶辫触锛屽凡鍥炴粴: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    project_root = Path(__file__).parent
    db_path = project_root / "data" / "news.db"

    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])

    logger.info(f"鐩爣鏁版嵁搴? {db_path}")
    migrate(db_path)
