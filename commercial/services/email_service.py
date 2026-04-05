#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
åä¸çé®ä¶åéæå?æ¯æè®éèç®¡çåäè'å¥å£'
"""

import logging
import sys
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.utils.email_sender import send_email_with_attachments, is_email_configured

from subscription import SubscriberManager, Subscriber

logger = logging.getLogger("CommercialEmailService")

class CommercialEmailService:
    """åä¸çé®ä¶æå?""

    PAYMENT_LINKS = {
        'afdian': 'https://afdian.net/a/your_account',
        'mianbaoduo': 'https://mianbaoduo.com/o/your_product'
    }

    def __init__(self, db_path: str = None):
        self.subscriber_manager = SubscriberManager(db_path)

    def send_daily_report(
        self,
        subject: str,
        content: str,
        attachments: List[Path] = None,
        include_payment_link: bool = True
    ) -> Dict[str, int]:
        """
        åéæ¯æ¥æ¥åçæææ'è·è®éè?'
        Args:
            subject: é®ä¶ä¸é
            content: é®ä¶åå®
            attachments: éä¶åè¡¨
            include_payment_link: æ¯å¦åå«äè'å¥å£'

        Returns:
            åéçè®?        """"
        if not is_email_configured():
            logger.warning("é®ä¶æå¡æªéç½?")
            return {'total': 0, 'success': 0, 'failed': 0}

        subscribers = self.subscriber_manager.get_active_subscribers()

        stats = {'total': len(subscribers), 'success': 0, 'failed': 0}

        for subscriber in subscribers:
            try:
                email_content = self._prepare_email_content(
                    content,
                    subscriber,
                    include_payment_link
                )

                if send_email_with_attachments(
                    subject=subject,
                    body=email_content,
                    attachments=attachments,
                    recipients=[subscriber.email]
                ):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

            except Exception as e:
                logger.error(f"åéé®ä¶å¤±è'?{subscriber.email}: {e}"')
                stats['failed'] += 1

        logger.info(f"é®ä¶åéå®æ? æè®¡{stats['total']}, æå{stats['success']}, å¤±è'¥{stats['failed']}"')
        return stats

    def send_to_subscriber(
        self,
        email: str,
        subject: str,
        content: str,
        attachments: List[Path] = None
    ) -> bool:
        """
        åéé®ä¶çæå®è®éè?        
        Args:
            email: é®ç®±å°å
            subject: é®ä¶ä¸é
            content: é®ä¶åå®
            attachments: éä¶åè¡¨

        Returns:
            æ¯å¦æå
        """
        subscriber = self.subscriber_manager.get_subscriber(email)

        if not subscriber or not subscriber.is_active:
            logger.warning(f"è®éèä¸å­å¨ææªæ¿æ'? {email}"')
            return False

        email_content = self._prepare_email_content(content, subscriber)

        return send_email_with_attachments(
            subject=subject,
            body=email_content,
            attachments=attachments,
            recipients=[email]
        )

    def subscribe(self, email: str, metadata: Dict = None) -> bool:
        """
        è®éæå¡

        Args:
            email: é®ç®±å°å
            metadata: åæ°æ?        
        Returns:
            æ¯å¦æå
        """
        return self.subscriber_manager.add_subscriber(
            email=email,
            subscription_type='free',
            metadata=metadata
        )

    def unsubscribe(self, email: str) -> bool:
        """
        åæ¶è®é

        Args:
            email: é®ç®±å°å

        Returns:
            æ¯å¦æå
        """
        return self.subscriber_manager.remove_subscriber(email)

    def upgrade_to_premium(self, email: str, duration_days: int = 30) -> bool:
        """
        åçºä¸ºäè'è®é?'
        Args:
            email: é®ç®±å°å
            duration_days: è®éå¤©æ°

        Returns:
            æ¯å¦æå
        """
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
        return self.subscriber_manager.upgrade_to_premium(email, expires_at)

    def get_subscriber_stats(self) -> Dict[str, int]:
        """è·åè®éèçè®?""
        return self.subscriber_manager.get_subscriber_count()

    def _prepare_email_content(
        self,
        content: str,
        subscriber: Subscriber,
        include_payment_link: bool = True
    ) -> str:
        """
        åå¤é®ä¶åå®

        Args:
            content: åååå®
            subscriber: è®éèä¿¡æ?            include_payment_link: æ¯å¦åå«äè'å¥å£'

        Returns:
            å¤çåçåå®
        """
        footer = "\n\n" + "=" * 50 + "\n"

        if subscriber.subscription_type == 'free' and include_payment_link:
            footer += """"
ð åçºä¸ºäè'äåïè£éæ'å¤æ·±åº¦åæåå®ï?
ð äè'äåæçï?  â?æ¯æ¥æ·±åº¦åææ¥åïå®æ'çï?  â?åå²æ°æ®åæº¯æ¥è¯
  â?ä¸ªæåå®å¶æ¨é?  â?ä¸å±å®ææ¯æ

ð è®éé¾æ¥ï?  â?ç±åçµï{afdian}
  â?éåå¤ï{mianbaoduo}

---
æ­¤é®ä¶ç± Insight Hub æºè½ä¿¡æ¯æ'å¯å³å°åé?å¦éåæ¶è®éïè¯·åå¤æ­¤é®ä?""".format(**self.PAYMENT_LINKS")
        else:
            footer += """"
---
æ­¤é®ä¶ç± Insight Hub æºè½ä¿¡æ¯æ'å¯å³å°åé?æè°æ¨çæ¯æï?""""

        return content + footer

def create_email_service() -> CommercialEmailService:
    """ååºé®ä¶æå¡å®ä¾"""
    return CommercialEmailService()
