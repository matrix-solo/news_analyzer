#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璁槄鑰呯鐞嗘ā鍧?绠$悊鐢ㄦ埛閭璁槄
"""

import logging
import sqlite3
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class Subscriber:
    """璁槄鑰呮暟鎹ā鍨?""
    email: str
    created_at: str
    is_active: bool = True
    subscription_type: str = "free"
    expires_at: Optional[str] = None
    metadata: Optional[Dict] = None

class SubscriberManager:
    """璁槄鑰呯鐞嗗櫒"""

    def __init__(self, db_path: str = None):
        self.logger = logging.getLogger("SubscriberManager")
        base_path = Path(__file__).parent.parent
        self.db_path = Path(db_path) if db_path else base_path / "data" / "subscribers.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
    """鍒濆鍖栨暟鎹簱"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(''''
                CREATE TABLE IF NOT EXISTS subscribers (
                    email TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    subscription_type TEXT DEFAULT 'free',
                    expires_at TEXT,
                    metadata TEXT
                )
            ''')
            conn.commit()
        self.logger.info(f"璁槄鑰呮暟鎹簱鍒濆鍖栧畬鎴? {self.db_path}")

    def add_subscriber(
        self,
        email: str,
        subscription_type: str = "free",
        expires_at: str = None,
        metadata: Dict = None
    ) -> bool:
        """
        娣诲姞璁槄鑰?        
        Args:
            email: 閭鍦板潃
            subscription_type: 璁槄绫诲瀷 (free/premium)
            expires_at: 杩囨湡鏃堕棿
            metadata: 鍏冩暟鎹?        
        Returns:
            鏄惁鎴愬姛
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(''''
                    INSERT OR REPLACE INTO subscribers 
                    (email, created_at, is_active, subscription_type, expires_at, metadata)
                    VALUES (?, ?, 1, ?, ?, ?)
                ''', (
                    email,
                    datetime.now().isoformat(),
                    subscription_type,
                    expires_at,
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
            self.logger.info(f"娣诲姞璁槄鑰? {self._mask_email(email)}")
            return True
        except Exception as e:
            self.logger.error(f"娣诲姞璁槄鑰呭け璐? {e}")
            return False

    def remove_subscriber(self, email: str) -> bool:
        """
        绉婚櫎璁槄鑰?        
        Args:
            email: 閭鍦板潃

        Returns:
            鏄惁鎴愬姛
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE subscribers SET is_active = 0 WHERE email = ?',
                    (email,)
                )
                conn.commit()
            self.logger.info(f"绉婚櫎璁槄鑰? {self._mask_email(email)}")
            return True
        except Exception as e:
            self.logger.error(f"绉婚櫎璁槄鑰呭け璐? {e}")
            return False

    def get_subscriber(self, email: str) -> Optional[Subscriber]:
        """
        鑾峰彇璁槄鑰呬俊鎭?        
        Args:
            email: 閭鍦板潃

        Returns:
            璁槄鑰呬俊鎭?        """"
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    'SELECT * FROM subscribers WHERE email = ?',
                    (email,)
                )
                row = cursor.fetchone()
                if row:
                    return Subscriber(
                        email=row['email'],
                        created_at=row['created_at'],
                        is_active=bool(row['is_active']),
                        subscription_type=row['subscription_type'],
                        expires_at=row['expires_at'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    )
            return None
        except Exception as e:
            self.logger.error(f"鑾峰彇璁槄鑰呭け璐? {e}")
            return None

    def get_active_subscribers(self, subscription_type: str = None) -> List[Subscriber]:
        """
        鑾峰彇娲昏穬璁槄鑰呭垪琛?        
        Args:
            subscription_type: 璁槄绫诲瀷杩囨护锛堝彲閫夛級

        Returns:
            璁槄鑰呭垪琛?        """"
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if subscription_type:
                    cursor = conn.execute(
                        'SELECT * FROM subscribers WHERE is_active = 1 AND subscription_type = ?',
                        (subscription_type,)
                    )
                else:
                    cursor = conn.execute(
                        'SELECT * FROM subscribers WHERE is_active = 1'
                    )

                subscribers = []
                for row in cursor.fetchall():
                    subscribers.append(Subscriber(
                        email=row['email'],
                        created_at=row['created_at'],
                        is_active=bool(row['is_active']),
                        subscription_type=row['subscription_type'],
                        expires_at=row['expires_at'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else None
                    ))
                return subscribers
        except Exception as e:
            self.logger.error(f"鑾峰彇璁槄鑰呭垪琛ㄥけ璐? {e}")
            return []

    def get_subscriber_count(self) -> Dict[str, int]:
        """
        鑾峰彇璁槄鑰呯粺璁?        
        Returns:
            缁熻淇℃伅
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT subscription_type, COUNT(*) FROM subscribers WHERE is_active = 1 GROUP BY subscription_type'
                )
                stats = {'total': 0, 'free': 0, 'premium': 0}
                for row in cursor.fetchall():
                    stats[row[0]] = row[1]
                    stats['total'] += row[1]
                return stats
        except Exception as e:
            self.logger.error(f"鑾峰彇缁熻澶辫触: {e}")
            return {'total': 0, 'free': 0, 'premium': 0}

    def upgrade_to_premium(self, email: str, expires_at: str) -> bool:
        """
        鍗囩骇涓轰粯璐硅闃?        
        Args:
            email: 閭鍦板潃
            expires_at: 杩囨湡鏃堕棿

        Returns:
            鏄惁鎴愬姛
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(''''
                    UPDATE subscribers 
                    SET subscription_type = 'premium', expires_at = ?, is_active = 1
                    WHERE email = ?
                ''', (expires_at, email))
                conn.commit()
            self.logger.info(f"鍗囩骇璁槄: {self._mask_email(email)} -> premium")
            return True
        except Exception as e:
            self.logger.error(f"鍗囩骇璁槄澶辫触: {e}")
            return False

    def _mask_email(self, email: str) -> str:
    """鑴辨晱閭"""
        if not email or '@' not in email:
            return email
        parts = email.split('@')
        name = parts[0]
        if len(name) <= 2:
            return '*' * len(name) + '@' + parts[1]
        return name[0] + '***' + name[-1] + '@' + parts[1]
