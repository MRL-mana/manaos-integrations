"""Slack LLM統合テスト"""
import requests
from slack_llm_integration import app, LLM_CLIENT

print("=" * 60)
print("Slack LLM統合テスト")
print("=" * 60)

# LLMクライアント確認
print(f"\n[確認] LLMクライアント: {'利用可能' if LLM_CLIENT else '利用不可'}")

if not LLM_CLIENT:
    print("❌ LLMクライアントが利用できません")
    exit(1)

# テスト1: APIエンドポイントテスト
print("\n[テスト1] APIエンドポイントテスト")
try:
    response = requests.post(
        "http://localhost:5115/api/slack/llm/chat",
        json={
            "text": "こんにちは！短く挨拶してください。",
            "channel": "#test",
            "auto_reply": False
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功！")
        print(f"   レスポンス: {result.get('response', '')[:100]}...")
        print(f"   モデル: {result.get('model')}")
        print(f"   レイテンシ: {result.get('latency_ms', 0):.2f}ms")
        print(f"   キャッシュ: {'✅' if result.get('cached') else '❌'}")
    else:
        print(f"❌ エラー: HTTP {response.status_code}")
        print(f"   レスポンス: {response.text}")
except requests.exceptions.ConnectionError:
    print("⚠️ サーバーが起動していません")
    print("   起動方法: python slack_llm_integration.py")
except Exception as e:
    print(f"❌ エラー: {e}")

# テスト2: メッセージ解析テスト
print("\n[テスト2] メッセージ解析テスト")
from slack_llm_integration import parse_slack_message

test_messages = [
    "こんにちは",
    "heavy 美しい風景を描写してください",
    "コード生成してください",
    "reasoning この問題を分析してください"
]

for msg in test_messages:
    parsed = parse_slack_message(msg)
    print(f"  入力: {msg}")
    print(f"    モデル: {parsed['model'].value}")
    print(f"    タスクタイプ: {parsed['task_type'].value}")

print("\n" + "=" * 60)
print("テスト完了！")
print("=" * 60)
print("\n次のステップ:")
print("  1. python slack_llm_integration.py  # サーバー起動")
print("  2. Slack App設定（SLACK_LLM_GUIDE.md参照）")
print("  3. /llm コマンドまたはBotメンションで使用")






















