"""
manaOS拡張フェーズ 起動スクリプト
統合APIサーバーを起動し、全機能を利用可能にする
"""

import sys
import os
from pathlib import Path
import logging
import io

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))


def check_dependencies():
    """依存関係をチェック"""
    print("=" * 60)
    print("依存関係チェック")
    print("=" * 60)
    
    missing = []
    
    # 必須モジュール
    required_modules = [
        ("flask", "Flask"),
        ("flask_cors", "Flask-CORS"),
        ("yaml", "PyYAML"),
        ("requests", "requests")
    ]
    
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
            print(f"[OK] {package_name}")
        except ImportError:
            print(f"[NG] {package_name} (未インストール)")
            missing.append(package_name)
    
    if missing:
        print(f"\n[WARN] 未インストールのパッケージ: {', '.join(missing)}")
        print("インストール: pip install " + " ".join(missing))
        return False
    
    return True


def check_services():
    """外部サービスの状態をチェック"""
    print("\n" + "=" * 60)
    print("外部サービスチェック")
    print("=" * 60)
    
    services = {
        "Ollama": "http://localhost:11434",
        "n8n": "http://localhost:5678"
    }
    
    import requests
    
    for service_name, url in services.items():
        try:
            response = requests.get(f"{url}/api/tags" if "ollama" in url.lower() else url, timeout=2)
            if response.status_code in [200, 204]:
                print(f"[OK] {service_name} - 起動中")
            else:
                print(f"[WARN] {service_name} - 応答異常 ({response.status_code})")
        except Exception as e:
            print(f"[NG] {service_name} - 未起動 ({str(e)[:50]})")


def check_config():
    """設定ファイルをチェック"""
    print("\n" + "=" * 60)
    print("設定ファイルチェック")
    print("=" * 60)
    
    config_files = {
        "LLMルーティング": Path(__file__).parent / "llm_routing_config.yaml",
        "通知ハブ": Path(__file__).parent / "notification_hub_config.yaml"
    }
    
    for config_name, config_path in config_files.items():
        if config_path.exists():
            print(f"[OK] {config_name} - {config_path.name}")
        else:
            print(f"[WARN] {config_name} - 見つかりません ({config_path.name})")
    
    # 環境変数チェック
    env_vars = {
        "OBSIDIAN_VAULT_PATH": "Obsidian Vaultパス",
        "OLLAMA_URL": "Ollama URL"
    }
    
    print("\n環境変数:")
    for env_var, description in env_vars.items():
        value = os.getenv(env_var)
        if value:
            print(f"[OK] {description} - 設定済み")
        else:
            print(f"[WARN] {description} - 未設定")


def start_server():
    """統合APIサーバーを起動"""
    print("\n" + "=" * 60)
    print("統合APIサーバー起動")
    print("=" * 60)
    
    try:
        from unified_api_server import app, initialize_integrations
        
        # 統合システムを初期化
        initialize_integrations()
        
        # ポートとホストを取得
        port = int(os.getenv("MANAOS_INTEGRATION_PORT", 9500))
        host = os.getenv("MANAOS_INTEGRATION_HOST", "0.0.0.0")
        
        print(f"\nサーバー起動: http://{host}:{port}")
        print("\n利用可能なエンドポイント:")
        print("  【拡張フェーズ API】")
        print("  POST /api/llm/route - LLMルーティング")
        print("  POST /api/memory/store - 記憶への保存")
        print("  GET  /api/memory/recall - 記憶からの検索")
        print("  POST /api/notification/send - 通知送信")
        print("  POST /api/secretary/morning - 朝のルーチン")
        print("  POST /api/secretary/noon - 昼のルーチン")
        print("  POST /api/secretary/evening - 夜のルーチン")
        print("  POST /api/image/stock - 画像をストック")
        print("  GET  /api/image/search - 画像検索")
        print("  GET  /api/image/statistics - 画像統計情報")
        print("\nサーバーを起動します...")
        print("=" * 60)
        
        app.run(host=host, port=port, debug=True)
    
    except KeyboardInterrupt:
        print("\n\nサーバーを停止しました")
    except Exception as e:
        logger.error(f"サーバー起動エラー: {e}")
        import traceback
        traceback.print_exc()


def main():
    """メイン関数"""
    print("=" * 60)
    print("manaOS拡張フェーズ 起動スクリプト")
    print("=" * 60)
    
    # 依存関係チェック
    if not check_dependencies():
        print("\n⚠️  依存関係が不足しています。インストールしてください。")
        return
    
    # 外部サービスチェック
    check_services()
    
    # 設定ファイルチェック
    check_config()
    
    # サーバー起動
    start_server()


if __name__ == "__main__":
    main()

