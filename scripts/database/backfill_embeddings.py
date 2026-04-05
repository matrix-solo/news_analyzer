#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
åéåå¡«èæ¬
ä¸ºæ°æ®åºä¸­ç°æçæ°éè®¡ç®å¶ä¿å­BGE-M3åé

ä½¿ç¨ææ³:
    python scripts/database/backfill_embeddings.py [--batch-size 100] [--days 90]
"""

import os
import sys
import argparse
import time

# è®¾ç½®HuggingFaceéå
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='åéåå¡«èæ¬')
    parser.add_argument('--batch-size', type=int, default=100, help='æ¯æå¤ççæ°éæ°é?')
    parser.add_argument('--days', type=int, default=90, help='å¤çæè¿Nå¤©çæ°é')
    parser.add_argument('--force', action='store_true', help='åºå¶éæ°è®¡ç®ææåé?')
    args = parser.parse_args()

    print("="*60)
    print("BGE-M3 åéåå¡«èæ¬")
    print("="*60)
    print(f"åæ°: batch_size={args.batch_size}, days={args.days}, force={args.force}")

    # å¯å¥ä¾èµ
    from core.storage.database import get_db
    from sentence_transformers import SentenceTransformer

    # å è½½æ¨¡å
    print("\nå è½½BGE-M3æ¨¡å...")
    model = SentenceTransformer('BAAI/bge-m3')
    print("æ¨¡åå è½½å®æ")

    db = get_db()

    # è·åçè®¡ä¿¡æ¯
    stats = db.get_embedding_stats()
    print(f"\nå½ååéçè®¡:")
    print(f"  ææ°éæ°: {stats['total_news']}")
    print(f"  æåé? {stats['with_embedding']}")
    print(f"  æ åé? {stats['without_embedding']}")
    print(f"  è¦çç? {stats['coverage']:.1%}")

    # è·åéè¦å¤ççæ°é
    if args.force:
        print(f"\nåºå¶æ¨¡åïéæ°è®¡ç®æè¿?{args.days} å¤©çæææ°éåé?..")
        news_list = db.get_history_news(days=args.days)
    else:
        print(f"\nè·åæè¿?{args.days} å¤©æ åéçæ°é?..")
        news_list = db.get_news_without_embeddings(days=args.days, limit=10000)

    if not news_list:
        print("\næ²¡æéè¦å¤ççæ°é")
        return

    print(f"éè¦å¤ç?{len(news_list)} æ¡æ°é?")

    # éå¤çå½æ?    def preprocess(news):
        parts = []
        title = news.get('translated_title') or news.get('title', '')
        if title:
            parts.append(title)
        summary = news.get('summary', '')
        if summary:
            parts.append(summary[:300])
        for field in ['who', 'what', 'where_place']:
            value = news.get(field, '')
            if value:
                parts.append(str(value))
        return ' '.join(parts)

    # æéå¤ç
    total_processed = 0
    total_saved = 0
    batch_size = args.batch_size

    start_time = time.time()

    for i in range(0, len(news_list), batch_size):
        batch = news_list[i:i+batch_size]

        # éå¤çææ?        texts = [preprocess(news) for news in batch]

        # çç 
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        # åå¤ä¿å­æ°æ®
        embeddings_data = []
        for j, news in enumerate(batch):
            news_id = news.get('id') or news.get('news_id')
            if news_id and j < len(embeddings):
                embeddings_data.append({
                    'news_id': news_id,
                    'embedding': embeddings[j].astype(np.float32).tobytes()
                })

        # ä¿å­å°æ°æ®åº
        saved = db.save_embeddings_batch(embeddings_data)

        total_processed += len(batch)
        total_saved += saved

        elapsed = time.time() - start_time
        speed = total_processed / elapsed if elapsed > 0 else 0
        eta = (len(news_list) - total_processed) / speed if speed > 0 else 0

        print(f"è¿åº¦: {total_processed}/{len(news_list)} ({total_processed/len(news_list)*100:.1f}%), "
              f"å·²ä¿å­? {total_saved}, éåº¦: {speed:.1f}æ?ç? éè®¡å©ä½: {eta/60:.1f}åé")

    # æççè®?    stats = db.get_embedding_stats()
    print(f"\nå¤çå®æ!")
    print(f"  å¤çæ°é: {total_processed}")
    print(f"  æåä¿å­: {total_saved}")
    print(f"  æèæ¶: {time.time() - start_time:.1f}ç?")
    print(f"\næçåéçè®?")
    print(f"  ææ°éæ°: {stats['total_news']}")
    print(f"  æåé? {stats['with_embedding']}")
    print(f"  è¦çç? {stats['coverage']:.1%}")

if __name__ == '__main__':
    main()
