#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIææè¯æ£æµæ¨¡å?ä½¿ç¨AIè¯­äçè£è¿è¡åèæ£æµïä½ä¸ºèåæ£æµçååº
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.processor.ai_processor import AIProcessor, get_ai_processor

@dataclass
class AISensitiveCheckResult:
    """AIææè¯æ£æµçæ?""
    is_compliant: bool
    risk_level: str
    risk_categories: List[str]
    risk_description: str
    suggested_action: str
    confidence: float

class AISensitiveChecker:
    """AIææè¯æ£æµå¨ - ä½¿ç¨è¯­äçè£å¤æ­åå®åèæ?""

    def __init__(self, ai_processor: AIProcessor = None):
        self.logger = logging.getLogger("AISensitiveChecker")
        self.ai = ai_processor or get_ai_processor()

    def check_compliance(
        self,
        title: str,
        content: str,
        purpose: str = "FILTER"
    ) -> AISensitiveCheckResult:
        """
        æ£æµåå®åèæ?        
        Args:
            title: æ°éæ é
            content: æ°éåå®
            purpose: AIç¨é?        
        Returns:
            AISensitiveCheckResult: æ£æµçæ?        """"
        full_text = f"æ éï{title}\n\nåå®ï{content}"

        if len(full_text) > 3000:
            full_text = full_text[:3000] + "..."

        prompt = f"""ä½ æ¯ä¸ä¸ªåå®åèå®¡æ ¸ä¸å®¶ãè¯·åæä¥ä¸æ°éåå®æ¯å¦ç¬¦åä¸­å½æ³å¾æ³èåå³å°èèã?"
ãå¾å®¡æ ¸åå®ã?{full_text}

ãå®¡æ ¸æ åã?è¯·ää¥ä¸ç'åº¦å¤æ­åå®æ¯å¦å­å¨é£é©ï?'
1. æ¿æ²ææé£é© - æ¶åéå¯äººç°å·ãè'éä¿¡æ¯ãåå²ææäºä¶ãåè£æ'å¨ç­
2. æ'åææé£é?- æ'åæææ'å¨ãæç«¯ä¸äç­'
3. è²æä½ä¿é£é© - è²æåå®ãä½ä¿ä¿¡æ¯ç­
4. èµåè¯éªé£é© - èµåãè¯éªãéæ³éèµç­
5. èåä¿¡æ¯é£é© - è°£è¨ãèåæ°éç­
6. ä¾µæè¿èé£é© - ä¾µç¯éçãç¥è¯äºæç­

ãè¾åºè¦æ±ã?è¯·ä¥JSONæ åè¿åå®¡æ ¸çæï?{{
    "is_compliant": trueæfalse,
    "risk_level": "é«å±"æ?ä¸­å±"æ?ä½å±"æ?å®å¨","
    "risk_categories": ["é£é©ç±å«1", "é£é©ç±å«2"]æ[]ï?    "risk_description": "é£é©æè¿°ïå¦ææ²¡æé£é©åå¡?æ é£é?",
    "suggested_action": "reject(æç)"æ?review(éå®¡æ ¸)"æ?pass(éè¿)",
    "confidence": 0.0å?.0äé'çç½®ä¿¡åº¦'
}}

ãéè¦ååã?- åªæå®å¨ç¬¦åæ³å¾æ³èåå³å°èèçåå®æè½æ è®°ä¸ºis_compliant=true
- å¯äºä¸ç¡®å®çåå®ïåºå¾åäºæ è®°ä¸ºéå®¡æ ¸
- confidenceè¡¨ç¤ºå®¡æ ¸çæçç½®ä¿¡åº¦ïä½äº?.8æ¶åºåºè®®äººå·¥å®¡æ ¸""""

        try:
            provider = self.ai.get_provider(purpose)
            if not provider:
                self.logger.warning("AIæä¾åä¸å¯ç¨ïè·³è¿AIåèæ£æµ?")
                return AISensitiveCheckResult(
                    is_compliant=True,
                    risk_level="å®å¨",
                    risk_categories=[],
                    risk_description="AIæå¡ä¸å¯ç¨ïéè®¤éè¿",
                    suggested_action="pass",
                    confidence=0.0
                )

            response = provider.chat([
                {"role": "user", "content": prompt}
            ], temperature=0.3)

            result = self.ai._parse_json_response(response)

            return AISensitiveCheckResult(
                is_compliant=result.get('is_compliant', True),
                risk_level=result.get('risk_level', 'å®å¨'),
                risk_categories=result.get('risk_categories', []),
                risk_description=result.get('risk_description', ''),
                suggested_action=result.get('suggested_action', 'pass'),
                confidence=result.get('confidence', 0.5)
            )

        except Exception as e:
            self.logger.error(f"AIåèæ£æµå¤±è'? {e}"')
            return AISensitiveCheckResult(
                is_compliant=True,
                risk_level="å®å¨",
                risk_categories=[],
                risk_description=f"æ£æµå¤±è'? {str(e)}",'
                suggested_action="pass",
                confidence=0.0
            )

    def check_batch(
        self,
        news_list: List[Dict[str, Any]],
        purpose: str = "FILTER"
    ) -> List[AISensitiveCheckResult]:
        """
        æéæ£æµåå®åèæ?        
        Args:
            news_list: æ°éåè¡¨ïæ¯æ¡åå«titleåcontent
            purpose: AIç¨é?        
        Returns:
            List[AISensitiveCheckResult]: æ£æµçæåè¡?        """"
        results = []
        for news in news_list:
            title = news.get('title', '')
            content = news.get('content', '')
            result = self.check_compliance(title, content, purpose)
            results.append(result)

        return results

def create_checker() -> AISensitiveChecker:
    """ååºAIææè¯æ£æµå¨å®ä¾"""
    return AISensitiveChecker()
