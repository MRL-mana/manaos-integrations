#!/usr/bin/env python3
"""停止中のサービスを起動するスクリプト"""
import subprocess
import sys
import time
import requests
from pathlib import Path


def start_service(service_name):
    """サービスを起動"""
    try:
        result = subprocess.run(
            ["systemctl", "start", service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def check_service_status(service_name):
    """サービスの状態を確認"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except:
        return "unknown"


def wait_for_service(service_name, max_wait=30):
    """サービスの起動を待つ"""
    for i in range(max_wait):
        status = check_service_status(service_name)
        if status == "active":
            return True
        time.sleep(1)
    return False


def get_services_status():
    """Remi Control APIからサービス状態を取得"""
    try:
        headers = {"X-Auth-Token": "manaos-secret-token-please-change"}
        response = requests.get(
            "http://127.0.0.1:9404/remi/status",
            headers=headers,
            timeout=3
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('services', {})
    except:
        pass
    return {}


def main():
    print("="*60)
    print("🚀 マナOS サービス起動")
    print("="*60)
    print()

    # 起動対象のサービス
    services_to_start = [
        "n8n",
        "sd-webui",
        "mana-intent",
        "manaos-command-hub"
    ]

    # 現在の状態を確認
    print("📊 現在のサービス状態:")
    current_status = get_services_status()
    for name in services_to_start:
        status = current_status.get(name, {})
        active = status.get('active', False)
        status_str = status.get('status', 'unknown')
        icon = "✅" if active else "❌"
        print(f"   {icon} {name}: {status_str}")
    print()

    # 停止中のサービスを起動
    print("🚀 停止中のサービスを起動します...")
    print()

    results = []
    for service_name in services_to_start:
        status = check_service_status(service_name)
        if status == "active":
            print(f"✅ {service_name}: 既に起動中")
            results.append((service_name, True, "already active"))
        else:
            print(f"📡 {service_name} を起動中...", end=" ")
            success, error = start_service(service_name)
            if success:
                print("起動コマンド実行")
                # 起動を待つ
                if wait_for_service(service_name):
                    print(f"   ✅ {service_name}: 起動完了")
                    results.append((service_name, True, "started"))
                else:
                    print(f"   ⚠️  {service_name}: 起動中（タイムアウト）")
                    results.append((service_name, False, "timeout"))
            else:
                print(f"   ❌ {service_name}: 起動失敗")
                if error:
                    print(f"      エラー: {error[:100]}")
                results.append((service_name, False, error or "unknown error"))

    print()
    print("="*60)
    print("📊 起動結果:")
    print("="*60)

    for name, success, message in results:
        icon = "✅" if success else "❌"
        print(f"   {icon} {name}: {message}")

    print()
    print("="*60)

    # 最終状態を確認
    print("\n📊 最終状態確認:")
    time.sleep(2)
    final_status = get_services_status()
    for name in services_to_start:
        status = final_status.get(name, {})
        active = status.get('active', False)
        status_str = status.get('status', 'unknown')
        icon = "✅" if active else "❌"
        print(f"   {icon} {name}: {status_str}")

    print()
    print("="*60)
    print("✅ 起動処理完了")
    print("="*60)


if __name__ == "__main__":
    main()

