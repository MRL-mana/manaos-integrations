# ManaOS人格設定

## 現在の状況

**質問**: 「人格もここと同じ？」

**回答**: 現在、ManaOSのLLMルーティングにはCursorと同じ人格設定は**まだ適用されていません**が、**人格設定機能を追加しました**。

## 実装内容

### ✅ 追加した機能

1. **人格設定ファイル（persona_config.yaml）**
   - システムプロンプトを設定可能
   - Cursorでの会話と同じ人格を設定可能

2. **LLMルーティングへの統合**
   - `chat`メソッドでシステムプロンプトを自動追加
   - 人格設定ファイルから自動読み込み

### 📝 人格設定ファイル

`manaos_integrations/persona_config.yaml`に以下の設定を追加しました：

```yaml
persona:
  system_prompt: |
    あなたはManaOS統合システムのアシスタントです。
    親切で、技術的で、実用的なサポートを提供します。
    ユーザーの質問に対して正確で詳細な回答を心がけます。
    コードや技術的な説明には具体的な例を含めます。
```

## 使い方

### サーバー再起動が必要

人格設定を有効化するには、統合APIサーバーを再起動してください：

```powershell
# サーバーを停止（Ctrl+C）
# サーバーを再起動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python start_server_simple.py
```

### 人格設定のカスタマイズ

`persona_config.yaml`を編集して、Cursorと同じ人格設定にできます：

```yaml
persona:
  system_prompt: |
    # Cursorと同じ人格設定をここに記述
    あなたは...
```

## 動作確認

サーバー再起動後、以下のコマンドで人格設定が適用されているか確認できます：

```bash
curl -X POST http://localhost:9500/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "こんにちは！"}],
    "task_type": "conversation"
  }'
```

## 次のステップ

1. **サーバーを再起動**して人格設定を有効化
2. **persona_config.yamlを編集**してCursorと同じ人格設定に調整
3. **テスト**して人格が正しく適用されているか確認

## 注意事項

- 人格設定は`chat`メソッド（`/api/llm/chat`エンドポイント）でのみ適用されます
- `route`メソッド（`/api/llm/route`エンドポイント）には適用されません
- システムプロンプトは会話の先頭に自動的に追加されます



