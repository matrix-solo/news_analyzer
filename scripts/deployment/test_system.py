#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ç³çåè½æµè¯èæ¬

æµè¯ç³çå¨æ²¡æç¥è¯åºçæåµä¸æ¯å¦è½æ­£å¸¸è¿è¡?""""

import sys
import os
import logging
from pathlib import Path

# æ·å é¡ç®æ ç®å½å° Python è·¯å¾
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage.database import NewsDatabase
from generators.report_generator import ReportGenerator

# éç½®æ¥å¿
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("TestSystem")

def test_system():
    """æµè¯ç³çåè½"""
    logger.info("=" * 60)
    logger.info("ð ååç³çåè½æµè¯?")
    logger.info("=" * 60)

    try:
        # 1. æµè¯æ°æ®åºè¿æ?        logger.info("æµè¯æ°æ®åºè¿æ?..")
        db = NewsDatabase()
        stats = db.get_stats()
        logger.info(f"â?æ°æ®åºè¿æ¥æåïå?{stats.get('total_news', 0)} æ¡æ°é?")

        # 2. æµè¯æ¥åçæå¨ååå
        logger.info("æµè¯æ¥åçæå?..")
        generator = ReportGenerator(enable_rag=False)
        logger.info("â?æ¥åçæå¨åååæå")

        # 3. æµè¯è·åæ°é
        logger.info("æµè¯è·åæ°é...")
        recent_news = db.get_recent_news(hours=24)
        logger.info(f"â?è·åå?{len(recent_news)} æ¡æè¿?4å°æ¶çæ°é?")

        # 4. æµè¯ç®è¦æ¥åçæ?        if recent_news:
            logger.info("æµè¯çæç®è¦æ¥å?..")
            report_path = generator.generate_brief_report(recent_news)
            if report_path:
                logger.info(f"â?ç®è¦æ¥åçææå? {report_path}")
            else:
                logger.warning("â ï¸  ç®è¦æ¥åçæå¤±è'?"')
        else:
            logger.warning("â ï¸  æ²¡ææè¿?4å°æ¶çæ°éïè·³è¿æ¥åçææµè¯")

        # 5. æµè¯ç³çèªæ£
        logger.info("æµè¯ç³çèªæ£...")
        os.system("python scripts/system_check.py")

        logger.info("=" * 60)
        logger.info("ð ç³çåè½æµè¯å®æ")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"æµè¯è¿ç¨ä¸­åçéè¯? {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """ä¸å½æ?""
    success = test_system()
    if success:
        print("\nâ?ç³çåè½æµè¯æåï?")
        print("\nç³çç¶æ?")
        print("- æ°æ®åº? æ­£å¸¸")
        print("- æ¥åçæ: æ­£å¸¸")
        print("- æ ¸å¿åè½: æ­£å¸¸")
        print("\nç¥è¯åºç¶æ?")
        print("- ç¥è¯åº? å¯éçä¶ïå½åæªå®è£?")
        print("- å½±å: RAGåè½ä¸å¯ç¨ïä½ä¸å½±åæ ¸å¿åè½")
        print("- åºè®®: å¦éå¯ç¨RAGåè½ïè¯·å®è£ chromadb å?sentence-transformers")
        return 0
    else:
        print("\nâ?ç³çåè½æµè¯å¤±è'¥"')
        return 1

if __name__ == "__main__":
    sys.exit(main())

"""
    success = test_system()
    if success:
        print("\nâ?ç³çåè½æµè¯æåï?")
        print("\nç³çç¶æ?")
        print("- æ°æ®åº? æ­£å¸¸")
        print("- æ¥åçæ: æ­£å¸¸")
        print("- æ ¸å¿åè½: æ­£å¸¸")
        print("\nç¥è¯åºç¶æ?")
        print("- ç¥è¯åº? å¯éçä¶ïå½åæªå®è£?")
        print("- å½±å: RAGåè½ä¸å¯ç¨ïä½ä¸å½±åæ ¸å¿åè½")
        print("- åºè®®: å¦éå¯ç¨RAGåè½ïè¯·å®è£ chromadb å?sentence-transformers")
        return 0
    else:
        print("\nâ?ç³çåè½æµè¯å¤±è'¥"')
        return 1

if __name__ == "__main__":
    sys.exit(main())
