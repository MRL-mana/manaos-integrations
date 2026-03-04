"""統一設定ローダー - すべての設定を一元管理

このモジュールは manaos_integration_config.json と _paths.py を統合し、
Single Source of Truth (SSOT) として機能します。

使用例:
    from config_loader import get_config, get_port
    
    port = get_port('unified_api')  # 9502
    config = get_config()  # 全設定を取得
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# 設定ファイルのパス
_CONFIG_FILE = Path(__file__).parent / "manaos_integration_config.json"
_config_cache: Optional[Dict[str, Any]] = None


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """設定ファイルを読み込み（キャッシュ機能付き）
    
    Args:
        force_reload: Trueの場合、キャッシュを無視して再読み込み
        
    Returns:
        設定辞書
    """
    global _config_cache
    
    if _config_cache is None or force_reload:
        with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
            _config_cache = json.load(f)
    
    return _config_cache


def get_config() -> Dict[str, Any]:
    """全設定を取得
    
    Returns:
        全設定辞書
    """
    return load_config()


def get_port(service_name: str, category: str = 'integration_services') -> int:
    """サービスのポート番号を取得
    
    Args:
        service_name: サービス名 (例: 'unified_api', 'mrl_memory')
        category: カテゴリ (デフォルト: 'integration_services')
                  'manaos_services', 'mcp_services', 'integration_services' のいずれか
    
    Returns:
        ポート番号
        
    Raises:
        KeyError: サービスが見つからない場合
        
    例:
        >>> get_port('unified_api')
        9502
        >>> get_port('mrl_memory', 'manaos_services')
        5105
    """
    config = load_config()
    
    # カテゴリを検索
    if category in config and service_name in config[category]:
        return config[category][service_name]['port']
    
    # すべてのカテゴリから検索
    for cat in ['manaos_services', 'mcp_services', 'integration_services']:
        if cat in config and service_name in config[cat]:
            return config[cat][service_name]['port']
    
    raise KeyError(f"Service '{service_name}' not found in any category")


def get_service_info(service_name: str) -> Dict[str, Any]:
    """サービスの詳細情報を取得
    
    Args:
        service_name: サービス名
        
    Returns:
        サービス情報辞書 (port, name, description)
    """
    config = load_config()
    
    for category in ['manaos_services', 'mcp_services', 'integration_services']:
        if category in config and service_name in config[category]:
            return config[category][service_name]
    
    raise KeyError(f"Service '{service_name}' not found")


def get_all_services() -> Dict[str, Dict[str, Any]]:
    """すべてのサービスをフラットな辞書として取得
    
    Returns:
        サービス名 -> サービス情報 の辞書
    """
    config = load_config()
    all_services = {}
    
    for category in ['manaos_services', 'mcp_services', 'integration_services']:
        if category in config:
            all_services.update(config[category])
    
    return all_services


def get_service_url(service_name: str, host: str = '127.0.0.1', protocol: str = 'http') -> str:
    """サービスのURLを生成
    
    Args:
        service_name: サービス名
        host: ホスト名またはIPアドレス (デフォルト: '127.0.0.1')
        protocol: プロトコル (デフォルト: 'http')
        
    Returns:
        完全なURL
        
    例:
        >>> get_service_url('unified_api')
        'http://127.0.0.1:9502'
    """
    port = get_port(service_name)
    return f"{protocol}://{host}:{port}"


def check_port_conflicts() -> Dict[int, list]:
    """ポート番号の衝突をチェック
    
    Returns:
        ポート番号 -> [サービス名リスト] の辞書（衝突のみ）
    """
    config = load_config()
    port_map: Dict[int, list] = {}
    
    for category in ['manaos_services', 'mcp_services', 'integration_services']:
        if category not in config:
            continue
            
        for service_name, service_info in config[category].items():
            port = service_info['port']
            if port not in port_map:
                port_map[port] = []
            port_map[port].append(service_name)
    
    # 衝突のみを返す
    return {port: services for port, services in port_map.items() if len(services) > 1}


if __name__ == "__main__":
    # テスト実行
    print("=== 設定ローダーテスト ===\n")
    
    print("1. Unified APIポート:")
    print(f"   {get_port('unified_api')}")
    
    print("\n2. MRL Memoryポート:")
    print(f"   {get_port('mrl_memory', 'manaos_services')}")
    
    print("\n3. Unified API URL:")
    print(f"   {get_service_url('unified_api')}")
    
    print("\n4. ポート衝突チェック:")
    conflicts = check_port_conflicts()
    if conflicts:
        for port, services in conflicts.items():
            print(f"   ⚠️  ポート {port}: {', '.join(services)}")
    else:
        print("   ✅ 衝突なし")
    
    print("\n5. 全サービス数:")
    print(f"   {len(get_all_services())} サービス")
