# 🔥 Tool Server (FastAPI) - レミ先輩仕様

**確実に動く手動ツール3つ + OpenAPI仕様対応**

---

## ✅ 実装済みツール

### 1. **docker/systemdの死活確認ツール**

```bash
POST /api/tools/service_status
{
  "service_type": "docker",  # or "systemd"
  "service_name": "open-webui"  # optional
}
```

**実行ログ**: `logs/tool_server.log`

---

### 2. **journalctl/docker logsを要約してエラー検知するツール**

```bash
POST /api/tools/check_errors
{
  "log_type": "docker",  # or "journalctl"
  "service_name": "open-webui",  # optional for journalctl
  "lines": 100
}
```

**実行ログ**: `logs/tool_server.log`

---

### 3. **ComfyUI APIを叩いて画像生成してファイルパスを返すツール**

```bash
POST /api/tools/generate_image
{
  "prompt": "美しい風景",
  "width": 512,
  "height": 512,
  "steps": 20,
  "negative_prompt": "blurry"  # optional
}
```

**実行ログ**: `logs/tool_server.log`

---

## 🚀 起動方法

### Docker Composeで起動

```powershell
docker-compose -f docker-compose.always-ready-llm.yml up -d tool-server
```

### 直接起動

```powershell
cd tool_server
pip install -r requirements.txt
python main.py
```

---

## 📋 OpenWebUIでの設定

1. OpenWebUIにアクセス: `http://localhost:3001`
2. 設定画面（右上の⚙️）→「External Tools」タブ
3. 「Add Tool」をクリック
4. 以下の情報を入力：

   ```
   Name: manaOS Tool Server
   URL: http://host.docker.internal:9503
   OpenAPI Spec: ON
   OpenAPI Spec URL: http://host.docker.internal:9503/openapi.json
   ```

5. 「Save」をクリック

---

## ✅ 動作確認

```powershell
# ヘルスチェック
curl http://localhost:9503/health

# サービス状態確認
curl -X POST http://localhost:9503/api/tools/service_status \
  -H "Content-Type: application/json" \
  -d '{"service_type": "docker"}'

# エラー検知
curl -X POST http://localhost:9503/api/tools/check_errors \
  -H "Content-Type: application/json" \
  -d '{"log_type": "docker", "service_name": "open-webui", "lines": 50}'

# 画像生成（ComfyUIが起動している場合）
curl -X POST http://localhost:9503/api/tools/generate_image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "美しい風景", "width": 512, "height": 512}'
```

---

## 🔥 レミ先輩の正解アーキテクチャ

```
┌─────────────────┐
│   OpenWebUI     │ ← 入口（チャットUI）
│  (ポート3001)   │
└────────┬────────┘
         │ Function Calling
         ↓
┌─────────────────┐
│  Tool Server    │ ← 実行（母艦の操作）
│  (FastAPI)      │    実行ログを必ず残す
│  (ポート9503)   │    危険コマンドは禁止リスト
└────────┬────────┘
         │
         ├─→ Docker API (docker.sock)
         ├─→ systemd (journalctl)
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

# ファイルログ
tail -f logs/tool_server.log
```

---

**レミ先輩**: まずは手動実行で確実に動かせ。自律型AIは後でいい🔥
