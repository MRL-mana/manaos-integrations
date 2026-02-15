# OllamaとManaOS記憶システムの統合

OllamaのチャットとManaOSの統一記憶システム（UnifiedMemory）を自動連携する機能が実装されました。

## 機能

### ✅ 実装済み機能

1. **自動会話保存**
   - Ollamaのチャットが自動的にObsidianに保存されます
   - セッションを超えて会話履歴が保持されます

2. **過去の会話履歴の読み込み**
   - チャット開始時に過去の会話履歴を自動的に読み込みます
   - コンテキストとして過去の会話を活用できます

3. **記憶システムとの統合**
   - 統一記憶システム（UnifiedMemory）と完全統合
   - Obsidianを母艦として会話履歴を管理

## 使い方

### API経由で使用

#### 基本的なチャット（自動保存）

```python
import requests

response = requests.post(
    "http://127.0.0.1:9405/api/llm/chat",
    json={
        "messages": [
            {"role": "user", "content": "こんにちは、私はマナです。"}
        ],
        "auto_save": True,  # 自動保存を有効化
        "load_history": False  # 過去の会話を読み込まない
    }
)

result = response.json()
print(result["response"])
```

#### 過去の会話履歴を読み込んでチャット

```python
response = requests.post(
    "http://127.0.0.1:9405/api/llm/chat",
    json={
        "messages": [
            {"role": "user", "content": "私の名前を覚えていますか？"}
        ],
        "auto_save": True,
        "load_history": True  # 過去の会話を読み込む
    }
)
```

#### Pythonコードから直接使用

```python
from manaos_integrations.llm_routing import LLMRouter

router = LLMRouter()

# チャット（自動保存）
result = router.chat(
    messages=[
        {"role": "user", "content": "こんにちは"}
    ],
    model="qwen2.5:7b",  # オプション
    user_id="mana",
    load_history=True,
    auto_save=True
)

print(result["response"])
```

## 設定

### 設定ファイル: `llm_routing_config.yaml`

```yaml
ollama_url: "http://127.0.0.1:11434"
routing:
  conversation:
    primary: "qwen2.5:7b"
    fallback: ["llama3.2:3b"]
memory:
  enabled: true
  auto_save: true
  load_history: true
```

## 動作確認

テストスクリプトを実行:

```bash
python manaos_integrations/test_ollama_memory_integration.py
```

## 注意事項

1. **Obsidian Vaultの設定**
   - 環境変数`OBSIDIAN_VAULT_PATH`を設定するか、デフォルトパスを使用
   - デフォルト: `C:/Users/mana4/Documents/Obsidian Vault`

2. **Ollamaの起動**
   - Ollamaサーバーが起動している必要があります
   - デフォルトURL: `http://127.0.0.1:11434`

3. **記憶システムの初期化**
   - 統一記憶システムが利用できない場合、自動保存は無効化されます
   - エラーログを確認してください

## トラブルシューティング

### 会話が保存されない

1. Obsidian Vaultのパスを確認
2. 統一記憶システムが初期化されているか確認
3. ログを確認: `logger.info`で保存状況を確認

### 過去の会話が読み込まれない

1. `load_history=True`が設定されているか確認
2. 記憶システムに過去の会話が保存されているか確認
3. `scope`パラメータを調整（"today", "week", "month", "all"）

## 今後の拡張予定

- [ ] ストリーミング対応
- [ ] 会話の要約機能
- [ ] 記憶の自動整理機能
- [ ] 複数ユーザー対応の強化



