#!/usr/bin/env python3
"""
Trinity v2.1 ヘルスチェック

全モジュールの動作状況を確認

実行: python3 health_check.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import requests


def check_database():
    """データベース確認"""
    try:
        from core.db_manager import DatabaseManager
        db = DatabaseManager()
        tasks = db.get_tasks(limit=1)
        db.close()
        return {'status': 'OK', 'message': 'データベース接続正常'}
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def check_cache():
    """キャッシュ確認"""
    try:
        from core.cache_manager import cache
        if cache.is_connected:
            stats = cache.get_stats()
            return {'status': 'OK', 'message': f"Redis接続正常（キー数: {stats.get('total_keys', 0)})"}
        else:
            return {'status': 'WARNING', 'message': 'Redis未接続（キャッシュ無効）'}
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def check_runpod():
    """RunPod統合確認"""
    try:
        from integrations.runpod_integration import runpod_manager
        if runpod_manager:
            stats = runpod_manager.get_queue_stats()
            return {'status': 'OK', 'message': f"RunPod接続正常（キュー: {stats.get('queue_size', 0)})"}
        else:
            return {'status': 'WARNING', 'message': 'RunPod未設定'}
    except Exception as e:
        return {'status': 'WARNING', 'message': str(e)}


def check_ollama():
    """Ollama確認"""
    try:
        from ai.ollama_integration import ollama_client
        if ollama_client:
            models = ollama_client.list_models()
            return {'status': 'OK', 'message': f"Ollama接続正常（{len(models)}モデル）"}
        else:
            return {'status': 'WARNING', 'message': 'Ollama未起動'}
    except Exception as e:
        return {'status': 'WARNING', 'message': str(e)}


def check_rag():
    """RAG確認"""
    try:
        from ai.rag_enhanced import rag
        if rag:
            stats = rag.get_stats()
            return {'status': 'OK', 'message': f"RAG正常（{stats.get('document_count', 0)}ドキュメント）"}
        else:
            return {'status': 'WARNING', 'message': 'RAG未初期化'}
    except Exception as e:
        return {'status': 'WARNING', 'message': str(e)}


def check_prometheus():
    """Prometheus確認"""
    try:
        response = requests.get('http://127.0.0.1:9091/metrics', timeout=5)
        if response.status_code == 200:
            return {'status': 'OK', 'message': 'Prometheus Exporter稼働中'}
        else:
            return {'status': 'WARNING', 'message': f'応答異常 (status={response.status_code})'}
    except Exception as e:
        return {'status': 'WARNING', 'message': 'Prometheus未起動'}


def check_disk_space():
    """ディスク容量確認"""
    try:
        import shutil
        usage = shutil.disk_usage('/')
        percent = (usage.used / usage.total) * 100
        free_gb = usage.free / 1024**3
        
        if percent > 95:
            return {'status': 'CRITICAL', 'message': f'ディスク使用率 {percent:.1f}% （空き: {free_gb:.1f}GB）'}
        elif percent > 90:
            return {'status': 'WARNING', 'message': f'ディスク使用率 {percent:.1f}% （空き: {free_gb:.1f}GB）'}
        else:
            return {'status': 'OK', 'message': f'ディスク使用率 {percent:.1f}% （空き: {free_gb:.1f}GB）'}
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def main():
    """メインヘルスチェック"""
    print("\n" + "🏥"*30)
    print(f"Trinity v2.1 ヘルスチェック")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🏥"*30 + "\n")
    
    checks = [
        ('Database', check_database),
        ('Cache (Redis)', check_cache),
        ('RunPod', check_runpod),
        ('Ollama', check_ollama),
        ('RAG', check_rag),
        ('Prometheus', check_prometheus),
        ('Disk Space', check_disk_space)
    ]
    
    results = []
    
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
        
        # 表示
        emoji = {
            'OK': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }.get(result['status'], '❓')
        
        print(f"{emoji} {name:20s} [{result['status']:8s}] {result['message']}")
    
    # サマリ
    ok_count = sum(1 for _, r in results if r['status'] == 'OK')
    warning_count = sum(1 for _, r in results if r['status'] == 'WARNING')
    error_count = sum(1 for _, r in results if r['status'] in ['ERROR', 'CRITICAL'])
    
    print("\n" + "="*60)
    print(f"📊 サマリ: OK={ok_count}, WARNING={warning_count}, ERROR={error_count}")
    
    if error_count == 0 and warning_count <= 2:
        print("✅ システム正常稼働中")
        exit_code = 0
    elif error_count > 0:
        print("🚨 Critical エラー検出")
        exit_code = 2
    else:
        print("⚠️  一部機能に問題あり")
        exit_code = 1
    
    print("="*60 + "\n")
    
    return exit_code


if __name__ == '__main__':
    exit(main())

