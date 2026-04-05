#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æµè¯ä¸­å½æ°éè¯å«éè¾
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from generators.report_generator import ReportGenerator

def test_china_news_identification():
    """æµè¯ä¸­å½æ°éè¯å«"""
    print("=" * 60)
    print("æµè¯ä¸­å½æ°éè¯å«éè¾")
    print("=" * 60)

    # ååºæ¥åçæå?    generator = ReportGenerator(enable_rag=False)

    # æµè¯ç¨ä¾
    test_cases = [
        # (source_name, expected_is_china)
        ("æ°åç¤?, True),"
        ("äººæ°æ¥æ¥", True),
        ("ä¸­å½æ¥æ¥", True),
        ("ä¸­å¤®å¿æ­çµèæå°", True),
        ("è'æ°ä åª", True),'
        ("æ¾ææ°é", True),
        ("ç¬¬ä¸è'ç", True),'
        ("36æ°?, True),"
        ("éåªä½?, True),"
        ("çéæ°é", True),
        ("è'çæå¿", True),'
        ("è·¯éç¤¾", False),
        ("ç¾èç¤?, False),"
        ("BBC News", False),
        ("çº½çº¦æ¶æ¥", False),
    ]

    print("\næµè¯çæï?")
    print("-" * 60)

    passed = 0
    failed = 0

    for source_name, expected in test_cases:
        news = {"source_name": source_name}
        result = generator._is_china_news(news)
        status = "â? if result == expected else "â?

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} {source_name}: {'ä¸­å½' if result else 'å½é'} (éæ: {'ä¸­å½' if expected else 'å½é'})")

    print("-" * 60)
    print(f"éè¿: {passed}/{len(test_cases)}, å¤±è'¥: {failed}/{len(test_cases)}"')
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = test_china_news_identification()
    sys.exit(0 if success else 1)
