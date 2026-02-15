"""n8n APIキーの形式を確認するスクリプト"""
import requests
import json
import os
import sys

base_url = os.getenv("N8N_BASE_URL", "http://127.0.0.1:5679")
api_key = os.getenv("N8N_API_KEY")

if not api_key or not api_key.strip():
    print("[NG] N8N_API_KEY が未設定です（このスクリプトはキーの形式確認用です）")
    print("     例: $env:N8N_API_KEY = \"your_n8n_api_key_here\"")
    sys.exit(2)

print("APIキーの形式を確認中...")
print("API Key: (redacted)")
print()

# JWTトークンをデコードしてみる
try:
    import base64
    parts = api_key.split('.')
    if len(parts) == 3:
        # ペイロードをデコード
        payload = parts[1]
        # Base64URLデコード
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        print("JWT Payload:")
        print(json.dumps(payload_data, indent=2, ensure_ascii=False))
        print()
except Exception as e:
    print(f"JWTデコードエラー: {e}")
    print()

# 異なる認証方法を試す
print("異なる認証方法を試します...")
print()

# 方法1: X-N8N-API-KEY ヘッダー
print("1. X-N8N-API-KEY ヘッダー:")
try:
    response = requests.get(
        f'{base_url}/api/v1/workflows',
        headers={'X-N8N-API-KEY': api_key},
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   [OK] 認証成功")
    else:
        print(f"   [NG] {response.text[:100]}")
except Exception as e:
    print(f"   [NG] {e}")

# 方法2: Authorization Bearer
print()
print("2. Authorization Bearer:")
try:
    response = requests.get(
        f'{base_url}/api/v1/workflows',
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   [OK] 認証成功")
    else:
        print(f"   [NG] {response.text[:100]}")
except Exception as e:
    print(f"   [NG] {e}")

# 方法3: クエリパラメータ
print()
print("3. クエリパラメータ:")
try:
    response = requests.get(
        f'{base_url}/api/v1/workflows?api_key={api_key}',
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   [OK] 認証成功")
    else:
        print(f"   [NG] {response.text[:100]}")
except Exception as e:
    print(f"   [NG] {e}")

# 方法4: Cookie
print()
print("4. Cookie:")
try:
    response = requests.get(
        f'{base_url}/api/v1/workflows',
        cookies={'n8n-api-key': api_key},
        timeout=5
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   [OK] 認証成功")
    else:
        print(f"   [NG] {response.text[:100]}")
except Exception as e:
    print(f"   [NG] {e}")















