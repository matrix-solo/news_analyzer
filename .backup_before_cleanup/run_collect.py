#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浠诲姟1 涓撶敤鍏ュ彛锛氭柊闂婚噰闆?鈫?AI 鏍￠獙 鈫?瀛樺叆寰呭垎鏋愭睜
鐢ㄤ簬 GitHub Actions 姣?2 灏忔椂鎵ц
"""

import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 鍔犺浇鐜鍙橀噺
project_root = Path(__file__).parent
load_dotenv(project_root / '.env')

sys.path.insert(0, str(project_root))

from core.config.loader import get_current_date, PROJECT_ROOT

(Path(PROJECT_ROOT) / "logs").mkdir(parents=True, exist_ok=True)
(Path(PROJECT_ROOT) / "data").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(PROJECT_ROOT) / "logs" / f"collect_{get_current_date()}.log",
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger("Collect")

def main():
    from task1_collector import Task1NewsCollector

    logger.info("=" * 60)
    logger.info("馃摗 浠诲姟1锛氭柊闂婚噰闆嗭紙姣?灏忔椂锛?")
    logger.info("=" * 60)

    collector = Task1NewsCollector()
    result = collector.run(max_per_source=10)
    return 0 if result.get("success") else 1

if __name__ == "__main__":
    sys.exit(main())
