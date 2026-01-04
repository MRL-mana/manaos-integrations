# n8nワークフロー設計: 生成→保存→記録→通知

## 🎯 目標

**「生成 → 保存 → Obsidian記録 → Slack通知」が1本通る自動化ループ**

---

## 📋 ワークフロー概要

```
画像生成リクエスト
    ↓
ComfyUIで画像生成
    ↓
生成完了通知
    ↓
Google Driveに保存
    ↓
Obsidianに記録
    ↓
Slack通知
```

---

## 🔧 実装方法

### 方法1: n8n Webhook経由（推奨）

#### 統合APIサーバー側

画像生成完了時にn8nのWebhookを呼び出す:

```python
# unified_api_server.pyに追加
@app.route("/api/comfyui/generate", methods=["POST"])
def comfyui_generate():
    # ... 既存の画像生成処理 ...
    
    # 生成完了後、n8nに通知
    if prompt_id:
        # n8n Webhookを呼び出し
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_webhook_url:
            requests.post(n8n_webhook_url, json={
                "prompt_id": prompt_id,
                "prompt": prompt,
                "status": "generated"
            })
    
    return jsonify({"prompt_id": prompt_id, "status": "success"})
```

#### n8nワークフロー

1. **Webhookトリガー**
   - エンドポイント: `/webhook/comfyui-generated`
   - メソッド: POST

2. **Google Drive: ファイルアップロード**
   - アクション: Upload File
   - ファイルパス: ComfyUIの出力ディレクトリから取得
   - フォルダID: 設定済みのフォルダ

3. **Obsidian: ノート作成**
   - アクション: Create Note
   - タイトル: 画像生成日時
   - 内容: プロンプト、パラメータ、Google Driveリンク

4. **Slack: 通知送信**
   - アクション: Send Message
   - チャンネル: 設定済みのチャンネル
   - メッセージ: 生成完了通知 + リンク

---

### 方法2: 統合APIサーバー内で直接実行

統合APIサーバー内で直接処理する方法:

```python
# unified_api_server.pyに追加
@app.route("/api/comfyui/generate-and-save", methods=["POST"])
def comfyui_generate_and_save():
    # 1. ComfyUIで画像生成
    # 2. Google Driveに保存
    # 3. Obsidianに記録
    # 4. Slack通知
    
    # すべての処理を統合
    pass
```

---

## 🚀 実装手順

### ステップ1: n8nのセットアップ

1. **n8nのインストール確認**
   ```bash
   # このはサーバー側で確認
   ssh konoha "systemctl status n8n"
   ```

2. **n8n Webhook URLの取得**
   - n8nのワークフローでWebhookノードを作成
   - Webhook URLを取得
   - 環境変数に設定: `N8N_WEBHOOK_URL`

### ステップ2: 統合APIサーバーの拡張

1. **n8n連携機能の追加**
   ```python
   # unified_api_server.pyに追加
   N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
   ```

2. **画像生成完了時の通知**
   - ComfyUIの画像生成完了を検知
   - n8n Webhookを呼び出し

### ステップ3: n8nワークフローの作成

1. **Webhookトリガーの設定**
2. **Google Driveノードの設定**
3. **Obsidianノードの設定**
4. **Slackノードの設定**

---

## 📝 詳細設計

### データフロー

```json
{
  "prompt_id": "12345",
  "prompt": "a beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "width": 512,
  "height": 512,
  "steps": 20,
  "cfg_scale": 7.0,
  "seed": 42,
  "image_path": "/path/to/generated/image.png",
  "generated_at": "2025-01-28T12:00:00Z"
}
```

### Google Drive保存

- **フォルダ構造**: `ManaOS/Generated/2025/01/28/`
- **ファイル名**: `{prompt_id}_{timestamp}.png`
- **メタデータ**: JSON形式で保存

### Obsidian記録

- **ファイル名**: `画像生成_{timestamp}.md`
- **内容**:
  ```markdown
  # 画像生成: {prompt}
  
  - 生成日時: {generated_at}
  - プロンプト: {prompt}
  - ネガティブプロンプト: {negative_prompt}
  - パラメータ: width={width}, height={height}, steps={steps}
  - Google Drive: [リンク]
  ```

### Slack通知

- **チャンネル**: `#manaos-notifications`
- **メッセージ**:
  ```
  🎨 画像生成完了
  
  プロンプト: {prompt}
  Google Drive: [リンク]
  Obsidian: [リンク]
  ```

---

## 🔗 関連ファイル

- `workflow_automation.py` - ワークフロー自動化モジュール
- `unified_api_server.py` - 統合APIサーバー
- `google_drive_integration.py` - Google Drive統合
- `obsidian_integration.py` - Obsidian統合
- `notification_system.py` - 通知システム

---

## 💡 次のステップ

1. ✅ n8nのセットアップ確認
2. ✅ 統合APIサーバーの拡張
3. ✅ n8nワークフローの作成
4. ✅ 動作確認

---

**進捗:** 設計完了、実装準備中


















