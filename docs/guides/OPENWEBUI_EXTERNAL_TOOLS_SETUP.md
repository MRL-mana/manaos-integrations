# 🔥 OpenWebUI External Tools設定ガイド（レミ先輩仕様）

**Tool ServerをOpenWebUIに統合する手順**

---

## ✅ 前提条件

- ✅ Tool Serverがホストから起動中（`http://localhost:9503`）
- ✅ OpenWebUIが起動中（`http://localhost:3001`）
- ✅ OpenAPI仕様が利用可能（`http://localhost:9503/openapi.json`）

---

## 🚀 設定手順（5ステップ）

### Step 1: OpenWebUIにアクセス

```
http://localhost:3001
```

### Step 2: 設定画面を開く

1. 右上の**⚙️アイコン**をクリック
2. 左メニューから**「External Tools」**タブを選択

### Step 3: Tool Serverを追加

1. **「Add Tool」**ボタンをクリック
2. 以下の情報を入力：

   ```
   Name: manaOS Tool Server
   URL: http://localhost:9503
   OpenAPI Spec: ON（チェックを入れる）
   OpenAPI Spec URL: http://localhost:9503/openapi.json
   ```

3. **「Save」**をクリック

### Step 4: ツールの確認

設定後、以下が利用可能になります：

- `service_status` - docker/systemdの死活確認
- `check_errors` - ログ要約・エラー検知
- `generate_image` - ComfyUI画像生成

### Step 5: チャットで動作確認

OpenWebUIのチャット画面で、以下のようなメッセージを送信：

```
dockerコンテナの状態を確認して
```

**期待される動作**:
- LLMが`service_status`ツールを呼び出す
- Dockerコンテナの状態が返る

---

## 🎯 動作確認コマンド

```powershell
# Tool Serverの状態確認
curl http://localhost:9503/health

# サービス状態確認
$body = @{service_type = "docker"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:9503/api/tools/service_status" `
    -Method POST -Body $body -ContentType "application/json"

# OpenAPI仕様の確認
curl http://localhost:9503/openapi.json
```

---

## 💡 トラブルシューティング

### Tool Serverに接続できない

1. Tool Serverが起動しているか確認
   ```powershell
   Get-NetTCPConnection -LocalPort 9503 -ErrorAction SilentlyContinue
   ```

2. Tool Serverを再起動
   ```powershell
   .\START_TOOL_SERVER_HOST.ps1
   ```

### OpenAPI仕様が取得できない

1. Tool Serverが正常に起動しているか確認
   ```powershell
   curl http://localhost:9503/health
   ```

2. OpenAPI仕様のURLを確認
   ```
   http://localhost:9503/openapi.json
   ```

### LLMがツールを呼び出さない

1. **Toolsを有効化**: チャット画面でToolsをONにする
2. **モデルの確認**: tool calling対応モデルを使用しているか確認
3. **システムプロンプト**: 「困ったら必ずツールを使う」システムプロンプトを設定

---

## 🔥 レミ先輩のアドバイス

### ✅ やるべき

1. **手動実行で確実に動かせ**: まずは手動でツールを呼び出して動作確認 ✅
2. **OpenAPI仕様を確認**: ツールが正しく登録されているか確認 ✅
3. **ログを確認**: Tool Serverのログを確認してエラーがないか確認 ✅

### ❌ やっちゃダメ

- OpenWebUIを魔改造する ❌
- ツールが動かないのにLLMに全部やらせようとする ❌
- "動いたからヨシ"で動作確認をしない ❌

---

**レミ先輩**: まずは手動実行で確実に動かせ。自律型AIは後でいい🔥
