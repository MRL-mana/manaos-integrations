"""
n8nワークフローをWebhook URL経由で直接実行するスクリプト
"""
import requests
import json
import sys
from datetime import datetime

# Webhook URL（先ほど取得したもの）
WEBHOOK_URL = "http://localhost:5679/webhook/comfyui-generated"

def execute_webhook(payload=None):
    """Webhookを実行"""
    try:
        if payload is None:
            payload = {
                "prompt_id": "test-execution",
                "prompt": "test prompt",
                "negative_prompt": "test negative prompt",
                "width": 512,
                "height": 512,
                "steps": 20,
                "cfg_scale": 7.0,
                "seed": -1,
                "status": "generated",
                "timestamp": datetime.now().isoformat()
            }
        
        print("=" * 60)
        print("Webhook実行")
        print("=" * 60)
        print(f"Webhook URL: {WEBHOOK_URL}")
        print()
        print("送信ペイロード:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()
        
        # 非同期実行のため、タイムアウトを短くしてリクエストを送信
        try:
            response = requests.post(
                WEBHOOK_URL,
                json=payload,
                timeout=5  # 短いタイムアウトでリクエストを送信
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print("[OK] ワークフローが正常に実行されました")
                try:
                    result = response.json()
                    print("レスポンス:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except (ValueError, json.JSONDecodeError):
                    print(f"レスポンス: {response.text[:500]}")
                return True
            else:
                print(f"[NG] ワークフロー実行エラー: {response.status_code}")
                print(f"レスポンス: {response.text[:500]}")
                return False
        except requests.exceptions.Timeout:
            # タイムアウトは正常（ワークフローが非同期で実行中）
            print(f"[OK] リクエストを送信しました（タイムアウトは正常です）")
            print(f"     ワークフローはバックグラウンドで実行中です")
            print(f"     n8nのWeb UI (http://localhost:5679) で実行状況を確認してください")
            return True
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    payload = None
    if len(sys.argv) > 1:
        try:
            payload = json.loads(sys.argv[1])
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[警告] ペイロードの解析に失敗しました: {e}。デフォルトを使用します。")
    
    success = execute_webhook(payload)
    sys.exit(0 if success else 1)

