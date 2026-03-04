#!/usr/bin/env python3
"""Remi Control API経由でサービスを起動するスクリプト"""
import requests
import time


def start_service_via_api(service_name):
    """Remi Control API経由でサービスを起動（restart）"""
    try:
        headers = {"X-Auth-Token": "manaos-secret-token-please-change"}
        response = requests.post(
            f"http://localhost:9404/remi/restart/{service_name}",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return True, data.get('message', 'OK')
        else:
            return False, response.text[:200]
    except Exception as e:
        return False, str(e)


def get_services_status():
    """サービス状態を取得"""
    try:
        headers = {"X-Auth-Token": "manaos-secret-token-please-change"}
        response = requests.get(
            "http://localhost:9404/remi/status",
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
    print("🚀 Remi Control API経由でサービスを起動")
    print("="*60)
    print()

    # 起動対象のサービス
    services = ["n8n", "sd-webui", "mana-intent", "manaos-command-hub"]

    # 現在の状態を確認
    print("📊 現在のサービス状態:")
    current_status = get_services_status()
    for name in services:
        status = current_status.get(name, {})
        active = status.get('active', False)
        status_str = status.get('status', 'unknown')
        icon = "✅" if active else "❌"
        print(f"   {icon} {name}: {status_str}")
    print()

    # サービスを起動
    print("🚀 サービスを起動します...")
    print()

    results = []
    for service_name in services:
        status = current_status.get(service_name, {})
        active = status.get('active', False)

        if active:
            print(f"✅ {service_name}: 既に起動中")
            results.append((service_name, True, "already active"))
        else:
            print(f"📡 {service_name} を起動中...", end=" ")
            success, message = start_service_via_api(service_name)
            if success:
                print(f"✅ OK")
                results.append((service_name, True, message))
            else:
                print(f"❌ 失敗")
                print(f"   エラー: {message[:100]}")
                results.append((service_name, False, message))
            time.sleep(2)  # 次のサービス起動前に少し待つ

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
    time.sleep(3)
    final_status = get_services_status()
    for name in services:
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

