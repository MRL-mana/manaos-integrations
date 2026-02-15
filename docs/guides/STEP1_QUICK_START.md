# STEP1: ComfyUI & CivitAI クイックスタート

レミ提案の**STEP1（今日〜明日）**を実装するためのガイド。

---

## 🎯 目標

**「画像生成がAPI経由で出る」状態を作る**

- ✅ ComfyUI起動
- ✅ CivitAI API設定
- ✅ 統合APIサーバー経由で画像生成

---

## 📋 前提条件

- ✅ 統合APIサーバーが実装済み
- ✅ ComfyUI統合モジュールが実装済み
- ✅ CivitAI統合モジュールが実装済み
- ✅ CivitAI APIキーが取得済み

---

## 🚀 手順

### 1. 環境変数の確認

```powershell
# manaos_integrationsディレクトリに移動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations

# 環境変数の確認（vaultから自動読み込み）
python test_comfyui_civitai.py
```

**期待される結果:**
- ✅ CivitAI: 利用可能
- ❌ ComfyUI: 利用不可（まだ起動していない）

---

### 2. ComfyUIサーバーの起動

#### 母艦（新PC）で起動する場合（推奨）

**ComfyUIがインストールされていない場合:**
```powershell
# 自動インストール
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\install_comfyui.ps1
```

**ComfyUIがインストール済みの場合:**
```powershell
# 起動スクリプトを使用（自動検索）
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_comfyui_local.ps1

# または手動で起動
cd C:\ComfyUI
python main.py --port 8188
```

#### このはサーバー側で起動する場合

```bash
# このはサーバーにSSH接続
ssh konoha
# または
ssh root@100.93.120.33

# ComfyUIディレクトリに移動
cd /root/ComfyUI

# ComfyUIサーバーを起動（ポート8188）
python main.py --port 8188

# バックグラウンドで起動する場合
nohup python main.py --port 8188 > /root/logs/comfyui.log 2>&1 &
```

**確認:**
- ブラウザで `http://127.0.0.1:8188` にアクセス
- ComfyUIのUIが表示されればOK

---

### 3. 統合APIサーバーの起動

```powershell
# manaos_integrationsディレクトリに移動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations

# 統合APIサーバーを起動
python unified_api_server.py
```

**期待される出力:**
```
ManaOS統合APIサーバーを起動中...
ComfyUI統合を初期化しました
CivitAI統合を初期化しました
サーバー起動: http://0.0.0.0:9502
```

---

### 4. 動作確認

#### 方法1: テストスクリプトを使用

```powershell
# 別のターミナルで実行
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python test_comfyui_civitai.py
```

#### 方法2: APIエンドポイントを直接テスト

```powershell
# CivitAI検索テスト
Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/civitai/search?query=realistic&limit=3" -Method GET

# ComfyUI画像生成テスト
$body = @{
    prompt = "a beautiful landscape, mountains, sunset, highly detailed"
    width = 512
    height = 512
    steps = 20
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/comfyui/generate" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

#### 方法3: 統合テストスクリプトを使用

```powershell
# 統合APIサーバーが起動している状態で実行
python test_api_endpoints.py
```

---

## ✅ 成功の確認

以下のすべてが✅になれば成功:

1. ✅ CivitAI検索が動作する
   ```powershell
   # レスポンスにモデルリストが返ってくる
   ```

2. ✅ ComfyUI画像生成が開始される
   ```powershell
   # レスポンスにprompt_idが返ってくる
   # ComfyUIのUIで生成状況を確認できる
   ```

3. ✅ 統合APIサーバーの状態確認
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:9502/api/integrations/status" -Method GET
   # comfyui.available = true
   # civitai.available = true
   ```

---

## 🔧 トラブルシューティング

### ComfyUIが起動しない

1. **ポート8188が使用中**
   ```bash
   # このはサーバー側
   netstat -tlnp | grep 8188
   # または
   lsof -i :8188
   ```

2. **依存関係が不足**
   ```bash
   cd /root/ComfyUI
   pip install -r requirements.txt
   ```

### CivitAI APIキーが無効

1. **環境変数の確認**
   ```powershell
   $env:CIVITAI_API_KEY
   ```

2. **vaultファイルの確認**
   ```powershell
   Get-Content ..\temp_migration\vault_envs\civitai_api.env
   ```

### 統合APIサーバーから接続できない

1. **ComfyUI URLの確認**
   ```powershell
   # このはサーバー側の場合
   $env:COMFYUI_URL = "http://163.44.120.49:8188"
   ```

2. **ネットワーク接続の確認**
   ```powershell
   Test-NetConnection -ComputerName 163.44.120.49 -Port 8188
   ```

---

## 📝 次のステップ（STEP2）

STEP1が完了したら:

1. ✅ Google Drive認証
2. ✅ n8nで自動化ワークフロー構築
3. ✅ 生成 → 保存 → Obsidian記録 → Slack通知

---

## 🔗 関連ファイル

- `test_comfyui_civitai.py` - ComfyUI & CivitAI統合テスト
- `test_api_endpoints.py` - APIエンドポイントテスト
- `COMFYUI_SETUP.md` - ComfyUI詳細セットアップガイド
- `unified_api_server.py` - 統合APIサーバー


