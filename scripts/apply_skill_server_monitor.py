#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サーバー監視・復旧処理スクリプト
YAML形式のサーバー監視設定を読み込み、サービス状態確認・自動再起動を実行
"""

import os
import sys
import json
import yaml
import requests
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_server_monitor_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def check_service(port: int) -> Dict[str, Any]:
    """サービス状態をチェック"""
    try:
        response = requests.get(
            f"http://localhost:{port}/health",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "running",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "details": data
            }
        else:
            return {
                "status": "unhealthy",
                "response_time_ms": None,
                "error": f"HTTP {response.status_code}"
            }
    except requests.exceptions.ConnectionError:
        return {
            "status": "stopped",
            "response_time_ms": None,
            "error": "Connection refused"
        }
    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "response_time_ms": None,
            "error": "Request timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time_ms": None,
            "error": str(e)
        }


def restart_service(service_name: str, script: str) -> Dict[str, Any]:
    """サービスを再起動"""
    script_path = project_root / script
    
    if not script_path.exists():
        return {
            "success": False,
            "error": f"スクリプトが見つかりません: {script}"
        }
    
    try:
        # 既存プロセスを停止（簡易実装）
        _stop_service_process(script)
        
        # 少し待機
        time.sleep(2)
        
        # 新しいプロセスを起動
        process = subprocess.Popen(
            ["python", str(script_path)],
            cwd=str(script_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 起動確認のため少し待機
        time.sleep(3)
        
        return {
            "success": True,
            "pid": process.pid,
            "message": f"{service_name} を再起動しました"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _stop_service_process(script: str):
    """サービスプロセスを停止（簡易実装）"""
    try:
        import platform
        if platform.system() == "Windows":
            # Windows: taskkillでPythonプロセスを停止（簡易実装）
            # 実際の運用では、より精密なプロセス管理が必要
            subprocess.run(
                ["taskkill", "/F", "/IM", "python.exe", "/FI", f"WINDOWTITLE eq {script}"],
                capture_output=True,
                timeout=5
            )
    except Exception:
        pass  # エラーを無視（プロセスが見つからない場合は問題ない）


def send_slack_notification(action: str, result: Dict[str, Any], service_name: str = "") -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "check": "サービス状態確認",
            "restart": "サービス再起動",
            "check_and_restart": "サービス状態確認・自動再起動"
        }
        action_name = action_names.get(action, action)
        
        message = f"🔍 *サーバー監視: {action_name}*\n\n"
        
        if service_name:
            message += f"サービス: {service_name}\n\n"
        
        if action == "check" or action == "check_and_restart":
            status = result.get("status", {})
            if isinstance(status, dict):
                status_str = status.get("status", "unknown")
                message += f"状態: {status_str}\n"
                if status.get("error"):
                    message += f"エラー: {status.get('error')}\n"
            else:
                message += f"状態: {status}\n"
        
        if action == "restart" or action == "check_and_restart":
            restart_result = result.get("restart_result")
            if restart_result:
                if restart_result.get("success"):
                    message += f"\n✅ 再起動成功: {restart_result.get('message', '')}\n"
                else:
                    message += f"\n❌ 再起動失敗: {restart_result.get('error', '')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Server Monitor",
            "icon_emoji": ":computer:"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")
    
    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False
    
    # バリデーション
    if data.get("kind") != "server_monitor":
        print("⚠️  kindが'server_monitor'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    service_name = data.get("service_name", "")
    
    try:
        if action == "check":
            port = data.get("port")
            if not port:
                result = {"success": False, "error": "portが指定されていません"}
            else:
                status = check_service(port)
                result = {"success": True, "status": status}
                # チェック結果をYAMLに追記
                data["status"] = status
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        
        elif action == "restart":
            script = data.get("script")
            if not script:
                result = {"success": False, "error": "scriptが指定されていません"}
            else:
                restart_result = restart_service(service_name, script)
                result = {"success": True, "restart_result": restart_result}
                # 再起動結果をYAMLに追記
                data["restart_result"] = restart_result
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        
        elif action == "check_and_restart":
            port = data.get("port")
            script = data.get("script")
            if not port or not script:
                result = {"success": False, "error": "portとscriptが指定されていません"}
            else:
                status = check_service(port)
                result = {"success": True, "status": status}
                
                # 停止していた場合、自動再起動
                auto_restart = data.get("auto_restart", True)
                if auto_restart and status.get("status") in ["stopped", "error"]:
                    print(f"⚠️  サービスが停止しています。再起動します...")
                    restart_result = restart_service(service_name, script)
                    result["restart_result"] = restart_result
                    # 再起動結果をYAMLに追記
                    data["restart_result"] = restart_result
                
                # チェック結果をYAMLに追記
                data["status"] = status
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        else:
            result = {"success": False, "error": f"不明なアクション: {action}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result, service_name)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_server_monitor.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)
    
    yaml_files = [Path(f) for f in sys.argv[1:]]
    
    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue
        
        if process_yaml_file(yaml_file):
            success_count += 1
    
    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")
    
    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
