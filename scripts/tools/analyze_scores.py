#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分体系数据分析脚本"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "data" / "news.db"
if not db_path.exists():
    print(f"数据库不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('=== 评分字段统计 ===')
cur.execute('''
SELECT 
    COUNT(*) as total,
    AVG(source_score) as avg_source,
    MIN(source_score) as min_source,
    MAX(source_score) as max_source,
    AVG(influence_score) as avg_influence,
    MIN(influence_score) as min_influence,
    MAX(influence_score) as max_influence,
    AVG(value_score) as avg_value,
    MIN(value_score) as min_value,
    MAX(value_score) as max_value,
    AVG(heat_score) as avg_heat,
    MIN(heat_score) as min_heat,
    MAX(heat_score) as max_heat,
    AVG(final_score) as avg_final,
    MIN(final_score) as min_final,
    MAX(final_score) as max_final
FROM news
''')
row = cur.fetchone()
print(f"总记录数: {row['total']}")
print(f"source_score: avg={row['avg_source']:.3f}, min={row['min_source']}, max={row['max_source']}")
print(f"influence_score: avg={row['avg_influence']:.3f}, min={row['min_influence']}, max={row['max_influence']}")
print(f"value_score: avg={row['avg_value']:.3f}, min={row['min_value']}, max={row['max_value']}")
print(f"heat_score: avg={row['avg_heat']:.3f}, min={row['min_heat']}, max={row['max_heat']}")
print(f"final_score: avg={row['avg_final']:.3f}, min={row['min_final']}, max={row['max_final']}")

print()
print('=== source_score 分布 ===')
cur.execute('SELECT source_score, COUNT(*) as cnt FROM news GROUP BY source_score ORDER BY cnt DESC LIMIT 10')
for row in cur.fetchall():
    print(f"  {row['source_score']}: {row['cnt']}条")

print()
print('=== heat_score 分布 ===')
cur.execute('SELECT heat_score, COUNT(*) as cnt FROM news GROUP BY heat_score ORDER BY heat_score')
for row in cur.fetchall():
    print(f"  {row['heat_score']}: {row['cnt']}条")

conn.close()
