# 🔗 常時起動LLM統合拡張ガイド

**Obsidian、Slack、Google Drive、n8nなどと完全統合**

---

## 📦 統合機能一覧

### ✅ 実装済み統合

1. **Obsidian統合**
   - LLM会話履歴を自動保存
   - フォルダ・タグ自動設定
   - Markdown形式で保存

2. **Slack通知統合**
   - LLM応答を自動通知
   - チャンネル指定可能
   - メタデータ付き通知

3. **Google Drive統合**
   - LLM結果をJSON形式で保存
   - タイムスタンプ付きファイル名
   - 自動バックアップ

4. **Mem0統合**
   - 会話をメモリに保存
   - 後で検索・参照可能
   - メタデータ付き

5. **n8nワークフロー統合**
   - Webhook経由でLLM呼び出し
   - 自動保存・通知ワークフロー
   - カスタマイズ可能

---

## 🚀 使い方

### 基本的な統合チャット

```python
from always_ready_llm_integrated import IntegratedLLMClient, ModelType, TaskType

# クライアント初期化（Obsidian自動保存有効）
client = IntegratedLLMClient(
    auto_save_obsidian=True,
    auto_notify_slack=False,
    auto_save_memory=True
)

# チャット実行
response = client.chat(
    "こんにちは！",
    ModelType.LIGHT,
    TaskType.CONVERSATION
)

print(response.response)
print(response.integration_results)
```

### Obsidian自動保存

```python
client = IntegratedLLMClient(
    auto_save_obsidian=True,
    obsidian_folder="LLM"  # 保存フォルダ
)

response = client.chat("質問", ModelType.LIGHT)
# 自動的にObsidianに保存されます
```

### Slack通知

```python
client = IntegratedLLMClient(
    auto_notify_slack=True,
    slack_channel="#llm-notifications"  # チャンネル指定
)

response = client.chat("重要な質問", ModelType.LIGHT)
# 自動的にSlackに通知されます
```

### Google Drive保存

```python
client = IntegratedLLMClient(
    auto_save_drive=True
)

response = client.chat("長文生成", ModelType.HEAVY)
# 自動的にGoogle Driveに保存されます
```

### 全統合機能使用

```python
client = IntegratedLLMClient(
    auto_save_obsidian=True,
    auto_notify_slack=True,
    auto_save_drive=True,
    auto_save_memory=True,
    obsidian_folder="LLM/FullIntegration",
    slack_channel="#llm-notifications"
)

response = client.chat("質問", ModelType.MEDIUM)
# 全ての統合機能が自動実行されます
```

---

## 🔧 設定

### Obsidian設定

```bash
# 環境変数設定
export OBSIDIAN_VAULT_PATH="C:/Users/mana4/Documents/Obsidian Vault"
```

### Slack設定

```bash
# 環境変数設定
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"
```

### Google Drive設定

1. Google Cloud Consoleで認証情報取得
2. `credentials.json`を配置
3. 初回実行時に認証

### Mem0設定

```bash
# 環境変数設定
export OPENAI_API_KEY="your_openai_api_key"
```

---

## 📊 n8nワークフロー統合

### ワークフローインポート

1. n8n UI (`http://127.0.0.1:5678`) にアクセス
2. ワークフロー → インポート
3. `n8n_workflows/llm_integrated_workflow.json` を選択
4. ワークフローを有効化

### Webhook呼び出し

```python
import requests

response = requests.post(
    "http://127.0.0.1:5678/webhook/llm-chat-integrated",
    json={
        "message": "こんにちは！",
        "model": "llama3.2:3b",
        "save_to_obsidian": True,
        "notify_slack": False
    }
)

print(response.json())
```

---

## 📝 使用例

詳細な使用例は `examples/integrated_llm_examples.py` を参照してください。

```bash
python examples/integrated_llm_examples.py
```

---

## 🎯 統合結果の確認

```python
response = client.chat("質問", ModelType.LIGHT)

# 統合結果を確認
for service, result in response.integration_results.items():
    if result.get("success"):
        print(f"✅ {service}: 成功")
        if "note_path" in result:
            print(f"   ノート: {result['note_path']}")
        if "file_id" in result:
            print(f"   ファイルID: {result['file_id']}")
        if "memory_id" in result:
            print(f"   メモリID: {result['memory_id']}")
    else:
        print(f"❌ {service}: 失敗 - {result.get('error', 'Unknown')}")
```

---

## 🔗 関連ファイル

- `always_ready_llm_integrated.py` - 統合拡張版クライアント
- `n8n_workflows/llm_integrated_workflow.json` - n8nワークフロー
- `examples/integrated_llm_examples.py` - 使用例集

---

**これで常時起動LLMが完全に統合されました！🔥**






















