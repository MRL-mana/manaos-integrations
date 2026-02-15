# ManaOS統合システム - セットアップガイド

## 現在の状態

✅ **完了している設定:**
- 依存関係のインストール
- 統合APIサーバーの起動（ポート9500）
- .envファイル読み込み機能
- LangChain統合（Ollama接続済み）
- LangGraph統合
- Obsidian統合（Vaultパス設定済み）

## 利用可能な統合システム

### ✅ 利用可能

1. **LangChain統合**
   - Ollamaサーバーに接続済み
   - モデル: qwen3:30b（環境変数で変更可能）
   - エンドポイント: `POST /api/langchain/chat`

2. **LangGraph統合**
   - LangGraphワークフロー実行
   - エンドポイント: `POST /api/langgraph/run`

3. **Obsidian統合**
   - Vaultパス: `C:/Users/mana4/Documents/Obsidian Vault`
   - エンドポイント: `POST /api/obsidian/create`

### ⚠️ 設定が必要

4. **ComfyUI統合**
   - ComfyUIサーバーを起動（ポート8188）
   - エンドポイント: `POST /api/comfyui/generate`

5. **Google Drive統合**
   - `credentials.json`を配置
   - Google Cloud Consoleで認証情報を取得
   - エンドポイント: `POST /api/google_drive/upload`

6. **CivitAI統合**
   - `.env`ファイルに`CIVITAI_API_KEY`を設定
   - エンドポイント: `GET /api/civitai/search`

7. **Mem0統合**
   - `.env`ファイルに`OPENAI_API_KEY`を設定
   - エンドポイント: `POST /api/mem0/add`

## 環境変数設定

`.env`ファイルを編集して、必要な設定を行ってください：

```env
# Obsidian統合（設定済み）
OBSIDIAN_VAULT_PATH=C:/Users/mana4/Documents/Obsidian Vault

# CivitAI統合
# CIVITAI_API_KEY=your_api_key_here

# OpenAI API (Mem0統合用)
# OPENAI_API_KEY=your_openai_api_key_here

# ComfyUI統合（デフォルト）
COMFYUI_URL=http://127.0.0.1:8188

# Ollama統合（設定済み）
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:30b

# Google Drive統合
GOOGLE_DRIVE_CREDENTIALS=credentials.json
GOOGLE_DRIVE_TOKEN=token.json

# ManaOS統合APIサーバー
MANAOS_INTEGRATION_PORT=9500
MANAOS_INTEGRATION_HOST=0.0.0.0
```

## APIエンドポイント

### ヘルスチェック
```bash
GET http://127.0.0.1:9510/health
```

### 統合システム状態
```bash
GET http://127.0.0.1:9510/api/integrations/status
```

### LangChainチャット
```bash
POST http://127.0.0.1:9510/api/langchain/chat
Content-Type: application/json

{
  "message": "こんにちは",
  "system_prompt": "あなたは親切なアシスタントです。"
}
```

### Obsidianノート作成
```bash
POST http://127.0.0.1:9510/api/obsidian/create
Content-Type: application/json

{
  "title": "テストノート",
  "content": "これはテストです。",
  "tags": ["test", "manaos"],
  "folder": "Notes"
}
```

## 起動方法

### 統合APIサーバーの起動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py
```

### 状態確認

```powershell
python check_integrations.py
```

## トラブルシューティング

### LangChain統合が利用不可の場合
- Ollamaが起動しているか確認: `Get-Process ollama`
- OllamaのURLが正しいか確認: `http://127.0.0.1:11434`

### Obsidian統合が利用不可の場合
- Vaultパスが存在するか確認
- 環境変数`OBSIDIAN_VAULT_PATH`が設定されているか確認

### サーバーが起動しない場合
- ポート9500が使用されていないか確認
- 依存関係がインストールされているか確認: `pip install -r requirements.txt`



















