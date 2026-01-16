# 🔥 Tool Server起動手順 - レミ先輩仕様

**確実に動く手動ツール3つ + OpenAPI仕様対応**

---

## ✅ 現在の状態確認

```
✅ OpenWebUI: 起動中 (ポート3001)
✅ Ollama: 起動中 (ポート11434)
❌ ComfyUI: 停止中 (ポート8188) ← 画像生成には必要
✅ Tool Server: 未起動 (ポート9503) ← これから起動
```

---

## 🚀 Tool Serverを起動する

### 方法1: Docker Composeで起動（推奨）

```powershell
# Tool Serverをビルド＆起動
docker-compose -f docker-compose.always-ready-llm.yml up -d tool-server

# ログを確認
docker logs -f tool-server
```

### 方法2: 直接起動（テスト用）

```powershell
cd tool_server
pip install -r requirements.txt
python main.py
```

---

## ✅ 動作確認

### 1. ヘルスチェック

```powershell
curl http://localhost:9503/health
```

**期待される結果**:
```json
{
  "status": "healthy",
  "service": "manaOS Tool Server",
  "timestamp": "2026-01-10T..."
}
```

### 2. サービス状態確認（Docker）

```powershell
$body = @{
    service_type = "docker"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:9503/api/tools/service_status" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**期待される結果**: OpenWebUI、Ollamaなどのコンテナ状態が返る

### 3. エラー検知（Docker logs）

```powershell
$body = @{
    log_type = "docker"
    service_name = "open-webui"
    lines = 50
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:9503/api/tools/check_errors" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**期待される結果**: エラーログが検出されれば返る

### 4. 画像生成（ComfyUIが起動している場合）

```powershell
$body = @{
    prompt = "美しい風景"
    width = 512
    height = 512
    steps = 20
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:9503/api/tools/generate_image" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**期待される結果**: `prompt_id`が返る（ComfyUIが起動している場合）

---

## 📋 OpenWebUIでの設定

### ステップ1: External Toolsに追加

1. **OpenWebUIにアクセス**: `http://localhost:3001`
2. **設定画面を開く**: 右上の⚙️アイコンをクリック
3. **「External Tools」タブ**を選択
4. **「Add Tool」**をクリック
5. 以下の情報を入力：

   ```
   Name: manaOS Tool Server
   URL: http://host.docker.internal:9503
   OpenAPI Spec: ON
   OpenAPI Spec URL: http://host.docker.internal:9503/openapi.json
   ```

6. **「Save」**をクリック

### ステップ2: ツールの確認

OpenWebUIのチャット画面で、使用可能なツールが認識されているか確認：

- `service_status` - サービス状態確認
- `check_errors` - エラー検知
- `generate_image` - 画像生成

---

## 🔥 レミ先輩の正解アーキテクチャ

```
┌─────────────────┐
│   OpenWebUI     │ ← 入口（チャットUI）
│  (ポート3001)   │   ローカルLLM（Ollama）
└────────┬────────┘
         │ Function Calling
         │ "dockerコンテナの状態を確認して"
         ↓
┌─────────────────┐
│  Tool Server    │ ← 実行（母艦の操作）
│  (FastAPI)      │   実行ログ: logs/tool_server.log
│  (ポート9503)   │   危険コマンド: 禁止リスト
└────────┬────────┘
         │
         ├─→ Docker API (docker ps, docker logs)
         ├─→ systemd (journalctl) [Linux only]
         └─→ ComfyUI API (画像生成)
```

---

## ⚠️ 重要なポイント

### ✅ やるべき

- **Tool Serverを分離**: FastAPIで独立したサーバー
- **実行ログを必ず残す**: `logs/tool_server.log`
- **危険コマンドは禁止リスト**: sudo、rm -rf など
- **OpenAPI仕様対応**: OpenWebUIの公式機能で使用

### ❌ やっちゃダメ

- OpenWebUIを魔改造する
- LLMにsudoで全部やらせる
- 1ファイルに全部書く神スクリプト
- "動いたからヨシ"で監査ログ無し

---

## 📊 実行ログの確認

```powershell
# リアルタイムログ
docker logs -f tool-server

# ファイルログ（もしあれば）
tail -f logs/tool_server.log
```

---

## 🎯 次のステップ

1. ✅ Tool Serverを起動
2. ✅ 動作確認（手動実行）
3. ⏳ OpenWebUIでExternal Tools設定
4. ⏳ LLMがツールを使う（Function Calling）

---

**レミ先輩**: まずは手動実行で確実に動かせ。自律型AIは後でいい🔥
