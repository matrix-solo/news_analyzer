#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ç®åçç¥è¯åºåååèæ¬

åè½ï?1. åååç¥è¯åºå­å¨çæ
2. ç'åç°ææ°éæ°æ®'
3. éªè¯åååçæ?""""

import sys
import os
import logging
from pathlib import Path

# æ·å é¡ç®æ ç®å½å° Python è·¯å¾
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase

try:
    from knowledge import ChromaKnowledgeBase, EmbeddingService, KnowledgePipeline
    from extensions.knowledge.chunking import HybridChunkingStrategy
    KNOWLEDGE_AVAILABLE = True
except ImportError as e:
    KNOWLEDGE_AVAILABLE = False
    print(f"ç¥è¯åºæ¨¡åä¸å¯ç¨: {e}")
    sys.exit(1)

# éç½®æ¥å¿
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("InitKnowledge")

def init_knowledge():
    """åååç¥è¯åº"""
    logger.info("=" * 60)
    logger.info("ð åååååç¥è¯åº?")
    logger.info("=" * 60)

    try:
        # 1. åååæ°æ®åºè¿æ¥
        logger.info("åååæ°æ®åºè¿æ¥...")
        db = NewsDatabase()

        # 2. åååç¥è¯åºçä¶
        logger.info("åååç¥è¯åºçä¶...")

        # 2.1 ChromaDB å­å¨
        knowledge_base = ChromaKnowledgeBase(
            persist_dir=str(project_root / "data" / "knowledge_base" / "chroma"),
            collection_name="news_articles"
        )

        # 2.2 åéåæå?        embedding_service = EmbeddingService()

        # 2.3 ææ¬ååç­ç¥
        chunking_strategy = HybridChunkingStrategy()

        # 2.4 ç¥è¯å¤çç®¡é
        pipeline = KnowledgePipeline(
            knowledge_base=knowledge_base,
            embedding_service=embedding_service,
            chunking_strategy=chunking_strategy,
            db_connection=db.get_connection()
        )

        # 3. æéç'åæ°é
        logger.info("ååæéç'åæ°é?.."')
        indexed_count = pipeline.index_news()
        logger.info(f"â?æéç'åå®æïå±ç'å {indexed_count} æ¡æ°é?")

        # 4. éªè¯åååçæ?        logger.info("éªè¯ç¥è¯åºç¶æ?..")
        stats = pipeline.get_stats()

        logger.info("ç¥è¯åºçè®?")
        logger.info(f"  ææ¡£æ°é: {stats.get('count', 0)}")
        logger.info(f"  ç'åæ°éæ? {stats.get('indexed_news_count', 0)}"')
        logger.info(f"  å­å¨è·¯å¾: {stats.get('persist_dir', '')}")
        logger.info(f"  éååç°: {stats.get('name', '')}")

        # 5. æµè¯æç'åè½
        logger.info("æµè¯æç'åè½..."')
        test_query = "äººå·¥æºè½åå±"
        results = knowledge_base.search(test_query, top_k=3)

        if results:
            logger.info(f"â?æç'æµè¯æåïæ¾å?{len(results)} ä¸ªçæ?"')
            for i, result in enumerate(results, 1):
                title = result.document.metadata.get('title', 'æ æ é?')
                logger.info(f"  {i}. {title} (ç¸äåº? {result.score:.2f})")
        else:
            logger.warning("â ï¸  æç'æµè¯æªæ¾å°çæïå¯è½éè¦æ'å¤æ°æ?")

        # 6. æ¸çè¿æ¥
        db.close()

        logger.info("=" * 60)
        logger.info("ð ç¥è¯åºåååå®æ")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"åååè¿ç¨ä¸­åçéè¯¯: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """ä¸å½æ?""
    if not KNOWLEDGE_AVAILABLE:
        print("â?ç¥è¯åºæ¨¡åä¸å¯ç¨ïè¯·ç¡®ä¿å·²å®è£?chromadb å?sentence-transformers")
        print("è¯·è¿è¡? pip install chromadb sentence-transformers --user")
        return 1

    success = init_knowledge()
    if success:
        print("\nâ?ç¥è¯åºåååæåï?")
        return 0
    else:
        print("\nâ?ç¥è¯åºåååå¤±è'¥"')
        return 1

if __name__ == "__main__":
    sys.exit(main())

"""
    if not KNOWLEDGE_AVAILABLE:
        print("â?ç¥è¯åºæ¨¡åä¸å¯ç¨ïè¯·ç¡®ä¿å·²å®è£?chromadb å?sentence-transformers")
        print("è¯·è¿è¡? pip install chromadb sentence-transformers --user")
        return 1

    success = init_knowledge()
    if success:
        print("\nâ?ç¥è¯åºåååæåï?")
        return 0
    else:
        print("\nâ?ç¥è¯åºåååå¤±è'¥"')
        return 1

if __name__ == "__main__":
    sys.exit(main())
