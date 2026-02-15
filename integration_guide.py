#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 ManaOS 新システム統合ガイド
新しく実装したシステムを既存コードに統合するためのヘルパー
"""

from pathlib import Path
from manaos_logger import get_logger

logger = get_logger(__name__)


def integrate_security_to_flask_app(app):
    """
    Flaskアプリにセキュリティ機能を統合
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    try:
        from manaos_security import SecurityConfig, require_api_key, rate_limit
        
        security_config = SecurityConfig()
        security_config.apply_security(app)
        
        logger.info("✅ セキュリティ機能を統合しました")
    except Exception as e:
        logger.error(f"セキュリティ統合エラー: {e}")


def integrate_gpu_manager():
    """
    GPUリソース管理を統合
    
    Returns:
        GPUResourceManagerインスタンス
    """
    try:
        from gpu_resource_manager import get_gpu_manager
        
        manager = get_gpu_manager(max_concurrent=2)
        logger.info("✅ GPUリソース管理を統合しました")
        return manager
    except Exception as e:
        logger.error(f"GPU管理統合エラー: {e}")
        return None


def integrate_cache():
    """
    キャッシュシステムを統合
    
    Returns:
        IntelligentCacheインスタンス
    """
    try:
        from intelligent_cache import get_cache
        
        cache = get_cache(max_size=1000, default_ttl=3600)
        logger.info("✅ キャッシュシステムを統合しました")
        return cache
    except Exception as e:
        logger.error(f"キャッシュ統合エラー: {e}")
        return None


def integrate_backup_system():
    """
    バックアップシステムを統合
    
    Returns:
        AutoBackupSystemインスタンス
    """
    try:
        from auto_backup_system import get_backup_system
        
        backup_system = get_backup_system()
        logger.info("✅ バックアップシステムを統合しました")
        return backup_system
    except Exception as e:
        logger.error(f"バックアップ統合エラー: {e}")
        return None


def integrate_metrics_collector():
    """
    メトリクス収集システムを統合
    
    Returns:
        MetricsCollectorインスタンス
    """
    try:
        from metrics_collector import get_metrics_collector
        
        collector = get_metrics_collector()
        logger.info("✅ メトリクス収集システムを統合しました")
        return collector
    except Exception as e:
        logger.error(f"メトリクス統合エラー: {e}")
        return None


def integrate_config_validator():
    """
    設定検証システムを統合
    
    Returns:
        ConfigValidatorEnhancedインスタンス
    """
    try:
        from config_validator_enhanced import get_config_validator
        
        validator = get_config_validator()
        logger.info("✅ 設定検証システムを統合しました")
        return validator
    except Exception as e:
        logger.error(f"設定検証統合エラー: {e}")
        return None


def integrate_all_systems(app=None):
    """
    すべての新システムを統合
    
    Args:
        app: Flaskアプリケーションインスタンス（オプション）
        
    Returns:
        統合されたシステムの辞書
    """
    systems = {}
    
    # セキュリティ
    if app:
        integrate_security_to_flask_app(app)
        systems['security'] = True
    
    # GPU管理
    systems['gpu_manager'] = integrate_gpu_manager()
    
    # キャッシュ
    systems['cache'] = integrate_cache()
    
    # バックアップ
    systems['backup'] = integrate_backup_system()
    
    # メトリクス
    systems['metrics'] = integrate_metrics_collector()
    
    # 設定検証
    systems['config_validator'] = integrate_config_validator()
    
    logger.info("✅ すべての新システムを統合しました")
    return systems

