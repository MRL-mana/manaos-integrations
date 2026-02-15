# ローカルLLM会話（チャット）インターフェースガイド

## 💬 会話できる場所

### 1. 🧠 AI Model Hub（推奨・最簡単）

**アクセスURL:**
- ローカル: `http://127.0.0.1:5080`
- Tailscale: `http://100.93.120.33:5080`

**特徴:**
- ✅ **Web UI付き** - ブラウザで直接会話可能
- ✅ **モデル選択** - Qwen 3:4bを含む全モデルから選択可能
- ✅ **テンプレート機能** - コードレビュー、説明、デバッグなどのテンプレート
- ✅ **会話履歴** - マルチターン会話対応
- ✅ **プロンプト最適化統合済み**（Ollama統合API経由）

**起動方法:**
```bash
cd Systems/konoha_migration/manaos_unified_system/services
python ai_model_hub.py
```

**使い方:**
1. ブラウザで `http://127.0.0.1:5080` を開く
2. モデルを選択（Qwen 3:4b推奨）
3. チャットエリアにメッセージを入力
4. EnterキーまたはSendボタンで送信

---

### 2. 💬 AI Assistant Chatbot

**アクセスURL:**
- ローカル: `http://127.0.0.1:5074`
- Tailscale: `http://100.93.120.33:5074`

**特徴:**
- ✅ **シンプルなチャットUI**
- ✅ **Socket.IO対応** - リアルタイム通信
- ✅ **会話履歴管理**
- ✅ **Ollama統合**

**起動方法:**
```bash
cd Systems/konoha_migration/manaos_unified_system/services
python ai_assistant_chatbot.py
```

**使い方:**
1. ブラウザで `http://127.0.0.1:5074` を開く
2. チャットボックスにメッセージを入力
3. Enterキーで送信

---

### 3. 🌐 Unified Portal（統合ポータル）

**アクセスURL:**
- ローカル: `http://127.0.0.1:5000`
- Tailscale: `http://100.93.120.33:5000`

**特徴:**
- ✅ **全機能統合ポータル**
- ✅ **ローカルLLMセクション**あり
- ✅ **Ollama統合API**経由で会話可能

**起動方法:**
```bash
cd Systems/konoha_migration/manaos_unified_system/services
python unified_portal.py
```

**使い方:**
1. ブラウザで `http://127.0.0.1:5000` を開く
2. 「🤖 ローカルLLM」セクションを探す
3. チャット機能を使用

---

### 4. 🌐 Portal v2（最新版）

**アクセスURL:**
- ローカル: `http://127.0.0.1:5072`
- Tailscale: `http://100.93.120.33:5072`

**特徴:**
- ✅ **最新の統合ポータル**
- ✅ **Socket.IO対応**
- ✅ **リアルタイム更新**

**起動方法:**
```bash
cd Systems/konoha_migration/manaos_unified_system/services
python unified_portal_v2.py
```

---

### 5. 🔍 RAG API Server（質問応答システム）

**アクセスURL:**
- ローカル: `http://127.0.0.1:5057`
- Tailscale: `http://100.93.120.33:5057`

**特徴:**
- ✅ **RAG機能付き** - ドキュメント検索＋回答
- ✅ **API経由** - HTTP APIで会話可能
- ✅ **プロンプト最適化・キャッシュ・メトリクス統合済み**

**起動方法:**
```bash
cd Systems/konoha_migration/server_projects/projects/automation
python rag_api_server.py
```

**使い方（API経由）:**
```bash
curl -X POST http://127.0.0.1:5057/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "アルバイトと正社員の違いは？"}'
```

---

### 6. 📱 Telegram Bot（Slack Bot）

**特徴:**
- ✅ **Telegram/Slack経由で会話**
- ✅ **Ollama統合**
- ✅ **会話履歴管理**

**設定方法:**
- `slack_bot_integration.py` を起動
- Telegram/Slackでボットと会話

---

## 🎯 推奨順位

### 1位: AI Model Hub（`http://127.0.0.1:5080`）
**理由:**
- Web UIが充実
- モデル選択が簡単
- テンプレート機能あり
- 使いやすい

### 2位: Unified Portal（`http://127.0.0.1:5000`）
**理由:**
- 全機能が統合されている
- 他の機能も一緒に使える

### 3位: RAG API Server（`http://127.0.0.1:5057`）
**理由:**
- RAG機能付きで高精度
- プロンプト最適化・キャッシュ統合済み

---

## 🚀 すぐに会話を始める方法

### 方法1: AI Model Hubを使う（最も簡単）

```powershell
# 1. AI Model Hubを起動
cd Systems\konoha_migration\manaos_unified_system\services
python ai_model_hub.py

# 2. ブラウザで開く
Start-Process "http://127.0.0.1:5080"
```

### 方法2: Unified Portalを使う

```powershell
# 1. Unified Portalを起動
cd Systems\konoha_migration\manaos_unified_system\services
python unified_portal.py

# 2. ブラウザで開く
Start-Process "http://127.0.0.1:5000"
```

### 方法3: Pythonから直接使う

```python
from Systems.konoha_migration.server_projects.projects.automation.manaos_langchain_rag import ManaOSLangChainRAG

rag = ManaOSLangChainRAG()
result = rag.query("こんにちは、元気ですか？")
print(result['answer'])
```

### 方法4: API経由で使う

```bash
# Ollama統合API経由
curl -X POST http://127.0.0.1:5000/api/ollama/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:4b",
    "messages": [{"role": "user", "content": "こんにちは"}],
    "optimize": true
  }'
```

---

## 📊 各インターフェースの比較

| インターフェース | URL | Web UI | RAG機能 | プロンプト最適化 | キャッシュ |
|---|---|---|---|---|---|
| **AI Model Hub** | `:5080` | ✅ | ❌ | ✅ | ❌ |
| **AI Assistant** | `:5074` | ✅ | ❌ | ✅ | ❌ |
| **Unified Portal** | `:5000` | ✅ | ❌ | ✅ | ❌ |
| **RAG API Server** | `:5057` | ❌ | ✅ | ✅ | ✅ |

---

## 💡 使い分けの目安

### AI Model Hubを使う場合
- シンプルな会話をしたい
- モデルを切り替えたい
- テンプレートを使いたい

### RAG API Serverを使う場合
- ドキュメント検索付きの回答が欲しい
- 高精度な回答が必要
- API経由で使いたい

### Unified Portalを使う場合
- 他の機能も一緒に使いたい
- 統合されたインターフェースが欲しい

---

## 🔧 起動確認

### サービスが起動しているか確認

```powershell
# ポート5080（AI Model Hub）
Test-NetConnection -ComputerName localhost -Port 5080

# ポート5000（Unified Portal）
Test-NetConnection -ComputerName localhost -Port 5000

# ポート5057（RAG API Server）
Test-NetConnection -ComputerName localhost -Port 5057
```

### ブラウザで確認

```powershell
# AI Model Hubを開く
Start-Process "http://127.0.0.1:5080"

# Unified Portalを開く
Start-Process "http://127.0.0.1:5000"
```

---

## 📝 まとめ

**最も簡単に会話を始める方法:**
1. AI Model Hubを起動: `python ai_model_hub.py`
2. ブラウザで `http://127.0.0.1:5080` を開く
3. モデルを選択（Qwen 3:4b推奨）
4. チャット開始！

**RAG機能付きで会話したい場合:**
1. RAG API Serverを起動: `python rag_api_server.py`
2. API経由でクエリを送信
3. ドキュメント検索＋回答を取得



