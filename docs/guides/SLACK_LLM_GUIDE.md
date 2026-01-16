# 🎙️ Slack × 常時起動LLM統合ガイド

**Slackから直接LLMを使えるようにする**

---

## 🚀 使い方

### 1. Slack Slash Command（/llm）

Slackで `/llm` コマンドを使用:

```
/llm こんにちは！
```

**レスポンス**: チャンネルにLLM応答が表示されます

### 2. Botメンション

Botをメンション:

```
@ManaOS こんにちは！
```

**レスポンス**: スレッドにLLM応答が返信されます

### 3. Webhook経由

```python
import requests

response = requests.post(
    "http://localhost:5115/api/slack/llm/chat",
    json={
        "text": "こんにちは！",
        "channel": "#general",
        "auto_reply": True
    }
)

print(response.json())
```

---

## 🔧 セットアップ

### 1. Slack LLM統合サーバー起動

```bash
python slack_llm_integration.py
```

デフォルトポート: **5115**

### 2. Slack App設定

#### 方法A: Slash Commands

1. **Slack App作成**: https://api.slack.com/apps
2. **Slash Commands追加**:
   - Command: `/llm`
   - Request URL: `http://your-server:5115/api/slack/command`
   - Description: "常時起動LLMとチャット"

#### 方法B: Botメンション

1. **Event Subscriptions有効化**
2. **Subscribe to bot events**:
   - `app_mention`
   - `message.im` (DM)
3. **Request URL**: `http://your-server:5115/api/slack/events`

#### 方法C: Incoming Webhooks

1. **Incoming Webhooks有効化**
2. **Webhook URL設定**: `http://your-server:5115/api/slack/webhook`

---

## 📝 環境変数設定

```bash
# Slack Webhook URL（返信用）
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"

# Slack LLM統合サーバーポート
export SLACK_LLM_PORT=5115
```

---

## 🎯 機能

### 自動モデル選択

メッセージ内容から自動的にモデルを選択:

- `heavy` または `高品質` → `ModelType.HEAVY`
- `medium` または `中型` → `ModelType.MEDIUM`
- `reasoning` または `推論` → `ModelType.REASONING`
- デフォルト → `ModelType.LIGHT`

### 自動タスクタイプ判定

- `コード` または `code` → `TaskType.AUTOMATION`
- `推論` または `分析` → `TaskType.REASONING`
- `生成` または `generate` → `TaskType.GENERATION`
- デフォルト → `TaskType.CONVERSATION`

### 自動統合機能

- ✅ Obsidian自動保存
- ✅ Mem0自動保存
- ✅ 統合結果の返却

---

## 📊 使用例

### 基本的なチャット

```
/llm こんにちは！
```

### 高品質生成

```
/llm heavy 美しい風景を描写してください
```

### コード生成

```
/llm Pythonでクイックソートを実装してください
```

### 推論・分析

```
/llm reasoning この問題を分析してください
```

---

## 🔗 APIエンドポイント

### POST /api/slack/llm/chat

```json
{
  "text": "こんにちは！",
  "channel": "#general",
  "auto_reply": true
}
```

### POST /api/slack/command

Slack Slash Command形式

### POST /api/slack/events

Slack Events API形式

### POST /api/slack/webhook

汎用Webhook形式

---

## 🎉 これでSlackから直接LLMを使えます！

**使い方**:
1. `/llm 質問` - Slash Command
2. `@ManaOS 質問` - Botメンション
3. Webhook経由 - API呼び出し

**全ての統合機能が自動的に動作します！** 🔥






















