#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChartDataService（第一阶段：最小可用聚合层）

目标：
- 把“给报告用的统计 SQL/聚合逻辑”从 report_generator.py 中抽出来
- 输出稳定的数据结构，便于后续接入图表渲染（图片/HTML/PDF）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.storage.database import NewsDatabase


@dataclass
class DailyMetric:
    date: str
    count: int
    avg_score: float


class ChartDataService:
    def __init__(self, db: Optional[NewsDatabase] = None):
        self.db = db or NewsDatabase()

    def get_domain_daily_metrics(self, domain: str, days: int = 30) -> List[DailyMetric]:
        """
        返回指定领域在近 N 天的每日数量与平均分。
        注意：以 news.pub_date 的日期部分聚合。
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    substr(pub_date, 1, 10) AS d,
                    COUNT(*) AS c,
                    AVG(COALESCE(score, 0)) AS avg_score
                FROM news
                WHERE domain = ?
                  AND pub_date >= datetime('now', ?)
                GROUP BY d
                ORDER BY d ASC
                """,
                (domain, f"-{days} days"),
            )
            rows = cur.fetchall()
            return [
                DailyMetric(
                    date=row["d"] or "",
                    count=int(row["c"] or 0),
                    avg_score=float(row["avg_score"] or 0.0),
                )
                for row in rows
            ]

    def get_domain_kpis(self, domain: str, days: int = 30) -> Dict[str, float]:
        """
        返回领域 KPI（用于报告总览面板的小指标）。
        """
        metrics = self.get_domain_daily_metrics(domain, days=days)
        if not metrics:
            return {"days": float(days), "total_count": 0.0, "avg_daily_count": 0.0, "avg_score": 0.0}

        total_count = sum(m.count for m in metrics)
        avg_daily = total_count / max(len(metrics), 1)
        # 平均分用“按天平均分的加权平均”（按当日新闻数加权）
        denom = sum(m.count for m in metrics) or 1
        avg_score = sum(m.avg_score * m.count for m in metrics) / denom
        return {
            "days": float(days),
            "total_count": float(total_count),
            "avg_daily_count": round(avg_daily, 2),
            "avg_score": round(avg_score, 2),
        }

