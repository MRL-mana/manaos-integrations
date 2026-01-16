# ManaOS統合システム 最終セットアップガイド

**日付:** 2025-01-28  
**ステータス:** ほぼ完了、最終確認待ち

---

## ✅ 完了項目

### STEP1: ComfyUI & CivitAI統合 ✅ 100%完了
- ✅ ComfyUIインストール & 起動
- ✅ CivitAI API設定
- ✅ 統合APIサーバー実装

### STEP2: Google Drive認証 ✅ 100%完了
- ✅ 認証情報ファイルコピー完了
- ✅ token.json作成完了
- ✅ Google Drive統合利用可能

### STEP3: n8nワークフロー構築 ✅ 設計完了
- ✅ ワークフロー設計完了
- ✅ 統合APIサーバー拡張完了
- ⚠️ n8nワークフロー作成待ち

---

## 🚀 最終セットアップ手順

### ステップ1: 統合APIサーバーの起動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py
```

**確認:**
- ポート9500で起動
- エンドポイントが利用可能

---

### ステップ2: 完全統合テストの実行

```powershell
# 別ターミナルで実行
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python complete_integration_test.py
```

**期待される結果:**
- ✅ 統合APIサーバー: 正常
- ✅ ComfyUI: 利用可能
- ✅ CivitAI: 利用可能
- ✅ Google Drive: 利用可能

---

### ステップ3: n8nワークフローの作成

#### 3-1. n8nにアクセス

```
http://100.93.120.33:5678
```

#### 3-2. ワークフローをインポート

1. n8nの「Workflows」→「Import from File」
2. `n8n_workflow_template.json`を選択
3. 「Import」をクリック

#### 3-3. 認証情報を設定

- Google Drive API認証情報
- Obsidian API認証情報（必要に応じて）
- Slack API認証情報（必要に応じて）

#### 3-4. Webhook URLを取得

1. Webhookノードを開く
2. 「Listen for Test Event」をクリック
3. Webhook URLをコピー
   ```
   http://100.93.120.33:5678/webhook/comfyui-generated
   ```

#### 3-5. 環境変数に設定

```powershell
# 統合APIサーバー起動時に設定
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py
```

#### 3-6. ワークフローを有効化

1. n8nでワークフローを開く
2. 右上の「Active」スイッチをON
3. 「Save」をクリック

---

### ステップ4: 完全な自動化ループのテスト

```powershell
# 画像生成を実行
$body = @{
    prompt = "a beautiful landscape, mountains, sunset, highly detailed"
    width = 512
    height = 512
    steps = 20
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:9500/api/comfyui/generate" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**確認項目:**
1. ✅ ComfyUIで画像生成が開始される
2. ✅ n8nワークフローが実行される
3. ✅ Google Driveにファイルがアップロードされる
4. ✅ Obsidianにノートが作成される（設定済みの場合）
5. ✅ Slackに通知が送信される（設定済みの場合）

---

## 📊 現在の状態

| システム | 状態 | 備考 |
|---------|------|------|
| ComfyUI | ✅ 起動中 | ポート8188 |
| CivitAI | ✅ 利用可能 | APIキー設定済み |
| Google Drive | ✅ 利用可能 | 認証完了 |
| 統合APIサーバー | ⚠️ 起動待ち | ポート9500 |
| n8n | ✅ 起動中 | ポート5678（このはサーバー） |
| n8nワークフロー | ⚠️ 作成待ち | テンプレート準備済み |

---

## 🔧 トラブルシューティング

### 統合APIサーバーが起動しない

```powershell
# ポート9500が使用中か確認
netstat -ano | findstr :9500

# プロセスを終了して再起動
```

### ComfyUIが接続できない

```powershell
# ComfyUIが起動しているか確認
Get-Process python | Where-Object {$_.Path -like "*ComfyUI*"}

# または再起動
.\start_comfyui_local.ps1
```

### n8nに接続できない

- このはサーバー側でn8nが起動しているか確認
- ポート5678が開いているか確認
- ファイアウォール設定を確認

---

## 📝 次のステップ

1. ✅ 統合APIサーバーを起動
2. ✅ 完全統合テストを実行
3. ✅ n8nワークフローを作成
4. ✅ 自動化ループをテスト

---

## 💡 完成後の状態

**「生成 → 保存 → Obsidian記録 → Slack通知」が1本通る自動化ループ**

- 画像生成リクエスト → ComfyUIで生成
- 生成完了 → n8nワークフロー実行
- Google Driveに保存 → Obsidianに記録 → Slack通知

---

**進捗:** 95%完了、最終確認待ち


















