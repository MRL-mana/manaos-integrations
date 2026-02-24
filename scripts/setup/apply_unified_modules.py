#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 統一モジュール適用スクリプト
主要サービスに統一モジュールを適用
"""

import os
import sys
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

logger = get_logger(__name__)

# 適用対象サービス
TARGET_SERVICES = [
    "manaos_integration_orchestrator.py",
    "unified_api_server.py",  # 既に適用済み
]

def apply_unified_modules_to_file(file_path: Path):
    """ファイルに統一モジュールを適用"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 既に適用されているか確認
        if 'from manaos_error_handler import' in content and 'from manaos_logger import' in content:
            logger.info(f"✅ {file_path.name}: 既に統一モジュールが適用されています")
            return True
        
        # 適用が必要な場合の処理（ここでは確認のみ）
        logger.info(f"⚠️ {file_path.name}: 統一モジュールの適用が必要です")
        return False
        
    except Exception as e:
        logger.error(f"❌ {file_path.name}: エラー - {e}")
        return False


def main():
    """メイン処理"""
    logger.info("=" * 70)
    logger.info("統一モジュール適用スクリプト")
    logger.info("=" * 70)
    
    base_dir = Path(__file__).parent
    results = {}
    
    for service_file in TARGET_SERVICES:
        file_path = base_dir / service_file
        if file_path.exists():
            results[service_file] = apply_unified_modules_to_file(file_path)
        else:
            logger.warning(f"⚠️ {service_file}: ファイルが見つかりません")
            results[service_file] = False
    
    # 結果サマリー
    logger.info("")
    logger.info("=" * 70)
    logger.info("適用結果サマリー")
    logger.info("=" * 70)
    
    applied = sum(1 for v in results.values() if v)
    total = len(results)
    
    for service_file, applied_status in results.items():
        status = "✅ 適用済み" if applied_status else "⚠️ 適用が必要"
        logger.info(f"  {service_file}: {status}")
    
    logger.info("")
    logger.info(f"適用済み: {applied}/{total}")
    
    if applied == total:
        logger.info("✅ すべてのサービスに統一モジュールが適用されています")
    else:
        logger.info(f"⚠️ {total - applied}個のサービスに統一モジュールの適用が必要です")


if __name__ == "__main__":
    main()








