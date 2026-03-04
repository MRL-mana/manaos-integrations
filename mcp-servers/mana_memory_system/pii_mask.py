#!/usr/bin/env python3
"""
PII（個人情報）マスク機能
機密情報の自動マスク

機能:
- 個人情報の自動検出・マスク
- Obsidian書き出し時の自動マスク
- タグ/ラベル付与
"""

import re
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PII検出パターン
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b\d{2,4}-\d{2,4}-\d{4}\b|\b\d{10,11}\b',
    'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
}


class PIIMasker:
    """PIIマスカー"""

    def __init__(self):
        self.masked_count = 0

    def detect_pii(self, content: str) -> List[Dict]:
        """PIIを検出"""
        detected = []

        for pii_type, pattern in PII_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                detected.append({
                    'type': pii_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })

        return detected

    def mask_content(self, content: str, mask_char: str = '*') -> tuple[str, List[Dict]]:
        """コンテンツをマスク"""
        detected = self.detect_pii(content)
        masked_content = content
        masks_applied = []

        # 後ろからマスク（インデックスがずれないように）
        for pii in sorted(detected, key=lambda x: x['start'], reverse=True):
            original = pii['value']
            masked = mask_char * len(original)
            masked_content = (
                masked_content[:pii['start']] +
                f"[REDACTED:{pii['type']}]" +
                masked_content[pii['end']:]
            )
            masks_applied.append({
                'type': pii['type'],
                'original_length': len(original),
                'position': pii['start']
            })

        if masks_applied:
            self.masked_count += len(masks_applied)
            logger.info(f"PIIマスク適用: {len(masks_applied)}件")

        return masked_content, masks_applied

    def should_mask(self, content: str, tags: Optional[List[str]] = None) -> bool:
        """マスクが必要か判定"""
        # タグに機密情報タグがある場合
        if tags:
            sensitive_tags = ['pii', 'sensitive', 'confidential', 'private', 'mufufu']
            if any(tag in tags for tag in sensitive_tags):
                return True

        # PIIが検出された場合
        detected = self.detect_pii(content)
        return len(detected) > 0

    def add_sensitive_tag(self, tags: List[str]) -> List[str]:
        """機密情報タグを追加"""
        if 'sensitive' not in tags:
            tags.append('sensitive')
        if 'pii' not in tags:
            tags.append('pii')
        return tags


def mask_memory_for_obsidian(content: str, importance: int,
                            category: Optional[str] = None) -> tuple[str, bool]:
    """Obsidian用に記憶をマスク"""
    masker = PIIMasker()

    # 重要度9以上または機密カテゴリの場合は自動マスク
    should_mask = importance >= 9 or category in ['sensitive', 'private', 'mufufu']

    if should_mask or masker.should_mask(content):
        masked_content, masks = masker.mask_content(content)
        return masked_content, True

    return content, False


if __name__ == '__main__':
    # テスト
    masker = PIIMasker()

    test_content = "連絡先: test@example.com, 電話: 090-1234-5678"
    detected = masker.detect_pii(test_content)
    print(f"検出: {len(detected)}件")
    for pii in detected:
        print(f"  {pii['type']}: {pii['value']}")

    masked, masks = masker.mask_content(test_content)
    print(f"マスク後: {masked}")








