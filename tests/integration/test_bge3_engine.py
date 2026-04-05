# -*- coding: utf-8 -*-
"""

BGE-M3历史关联引擎测试脚本

"""

import sys

import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3

import time

from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'news.db')

def load_news_from_db(limit=100):

    """从数据库加载新闻"""

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute('''

        SELECT id, title, translated_title, summary, content,

               domain, pub_date, who, what, where_place, tags, score

        FROM news 

        WHERE score > 0

        ORDER BY pub_date DESC

        LIMIT 

    ''', (limit,))

    news_list = []

    for row in cursor.fetchall():

        news = dict(row)

        news['news_id'] = news['id']

        news['final_score'] = news['score']

        news_list.append(news)

    conn.close()

    return news_list

def test_bge3_engine():

    """测试BGE-M3引擎"""

    print("="*60)

    print("BGE-M3历史关联引擎测试")

    print("="*60)

    # 检查依

    print("\n检查依..")

    try:

        from sentence_transformers import SentenceTransformer

        print("sentence-transformers 已安")

    except ImportError:

        print("sentence-transformers 未安")

        print("  请运 pip install sentence-transformers")

        return

    try:

        import faiss

        print("faiss 已安")

    except ImportError:

        print("faiss 未安")

        print("  请运 pip install faiss-cpu")

        return

    # 加载新闻

    print("\n加载新闻数据...")

    news_list = load_news_from_db(limit=100)

    print(f"加载{len(news_list)} 条新")

    if len(news_list) < 10:

        print("新闻数量不足,跳过测")

        return

    # 初始化引

    print("\n初始化BGE-M3引擎...")

    from core.processor.history_relation_engine_bge3 import BGE3HistoryRelationEngine

    start_time = time.time()

    try:

        engine = BGE3HistoryRelationEngine(news_list)

        init_time = time.time() - start_time

        print(f"引擎初始化完成,耗时: {init_time:.2f}")

    except Exception as e:

        print(f"引擎初始化失 {e}")

        return

    # 测试查询

    print("\n测试查询...")

    test_news = news_list[0]

    print(f"测试新闻: {test_news.get('translated_title') or test_news.get('title', '')[:50]}...")

    start_time = time.time()

    try:

        results = engine.find_related_news(test_news, top_k=5, threshold=0.35)

        query_time = time.time() - start_time

        print(f"\n查询完成,耗时: {query_time:.3f}")

        print(f"找到 {len(results)} 条相关新")

        if results:

            print("\n相关新闻列表:")

            for i, r in enumerate(results, 1):

                print(f"  {i}. [{r.pub_date}] {r.title[:40]}...")

                print(f"     综合得分: {r.related_score:.3f} (语义:{r.semantic_score:.3f}, 时间:{r.time_score:.3f})")

                print(f"     时间类型: {r.time_type}")

                if r.matched_entities:

                    print(f"     匹配实体: {', '.join(r.matched_entities[:3])}")

        else:

            print("\n未找到相关新闻(可能需要降低阈值)")

    except Exception as e:

        print(f"查询失败: {e}")

        import traceback

        traceback.print_exc()

    # 测试不同阈

    print("\n测试不同阈值效..")

    for threshold in [0.25, 0.35, 0.45, 0.55]:

        results = engine.find_related_news(test_news, top_k=5, threshold=threshold)

        print(f"  阈{threshold}: 找到 {len(results)} 条相关新")

if __name__ == '__main__':

    test_bge3_engine()
