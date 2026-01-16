# ComfyUI 母艦（新PC）起動ガイド

## 🎯 目標

新PC（母艦）でComfyUIを起動して、ManaOS統合APIサーバーから画像生成できるようにする。

---

## 📋 前提条件

- ✅ Python 3.8以上がインストールされている
- ✅ GPU（NVIDIA）があると高速（CPUでも動作可能）
- ⚠️ ComfyUIがインストールされているか確認が必要

---

## 🔍 ComfyUIインストール確認

### 方法1: 確認スクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\check_comfyui_installation.ps1
```

このスクリプトが以下を確認します:
- ComfyUIのインストール場所
- Python環境
- GPU環境
- PyTorchのインストール状況

### 方法2: 手動で確認

```powershell
# Cドライブ直下
Get-ChildItem -Path "C:\" -Filter "*ComfyUI*" -Directory

# ユーザーディレクトリ
Get-ChildItem -Path "$env:USERPROFILE" -Filter "*ComfyUI*" -Directory

# Dドライブ
Get-ChildItem -Path "D:\" -Filter "*ComfyUI*" -Directory

# Desktop
Get-ChildItem -Path "$env:USERPROFILE\Desktop" -Filter "*ComfyUI*" -Directory
```

---

## 🚀 ComfyUI起動方法

### ケース1: ComfyUIが既にインストールされている場合

#### 方法A: 起動スクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_comfyui_local.ps1
```

スクリプトが自動的にComfyUIを検索して起動します。

#### 方法B: 手動で起動

```powershell
# ComfyUIディレクトリに移動
cd C:\path\to\ComfyUI
# または
cd D:\ComfyUI

# ComfyUIサーバーを起動（ポート8188）
python main.py --port 8188

# CPUモードで起動（GPUがない場合）
python main.py --port 8188 --cpu

# 低VRAMモードで起動（GPUメモリが少ない場合）
python main.py --port 8188 --lowvram
```

### ケース2: ComfyUIがインストールされていない場合

#### 方法A: 自動インストールスクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\install_comfyui.ps1
```

このスクリプトが以下を自動実行します:
- GitからComfyUIをクローン
- PyTorchをインストール（GPU対応）
- 依存関係をインストール
- インストール完了後、起動方法を表示

**オプション:**
```powershell
# CPUのみの場合
.\install_comfyui.ps1 -CPUOnly

# カスタムパスにインストール
.\install_comfyui.ps1 -InstallPath "D:\ComfyUI"

# 依存関係をスキップ（後で手動インストール）
.\install_comfyui.ps1 -SkipDependencies
```

#### 方法B: 手動でインストール

```powershell
# インストール先ディレクトリを決める（例: C:\ComfyUI）
cd C:\

# ComfyUIをクローン
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 依存関係をインストール
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# ComfyUIを起動
python main.py --port 8188
```

#### 方法C: ポータブル版を使用

1. [ComfyUIのリリースページ](https://github.com/comfyanonymous/ComfyUI/releases)からダウンロード
2. 解凍して任意の場所に配置
3. `main.py`を実行

---

## ✅ 起動確認

### 1. ブラウザで確認

```
http://localhost:8188
```

ComfyUIのUIが表示されればOK。

### 2. APIで確認

```powershell
# システム統計を取得
Invoke-RestMethod -Uri "http://localhost:8188/system_stats" -Method GET
```

### 3. 統合APIサーバーから確認

```powershell
# 統合APIサーバーを起動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py

# 別ターミナルでテスト
python test_comfyui_civitai.py
```

---

## 🔧 トラブルシューティング

### ポート8188が使用中

```powershell
# ポート使用状況確認
netstat -ano | findstr :8188

# 使用中のプロセスを終了（必要に応じて）
# タスクマネージャーで該当プロセスを終了
```

### GPUが認識されない

```powershell
# CUDA確認
python -c "import torch; print(torch.cuda.is_available())"

# GPU情報確認
nvidia-smi
```

### 依存関係エラー

```powershell
# requirements.txtから再インストール
cd C:\path\to\ComfyUI
pip install -r requirements.txt --upgrade
```

### メモリ不足

```powershell
# CPUモードで起動（GPUメモリ不足の場合）
python main.py --port 8188 --cpu

# または低メモリモード
python main.py --port 8188 --lowvram
```

---

## 🎯 統合APIサーバーとの連携

### 環境変数の設定

統合APIサーバーは自動的に`localhost:8188`に接続します。

もし別のポートやリモートサーバーを使用する場合：

```powershell
# 環境変数を設定
$env:COMFYUI_URL = "http://localhost:8188"
# またはリモートの場合
$env:COMFYUI_URL = "http://163.44.120.49:8188"
```

### 統合APIサーバー起動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py
```

### 画像生成テスト

```powershell
# PowerShellでテスト
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

---

## 📝 自動起動設定（オプション）

### タスクスケジューラーで自動起動

```powershell
# タスクスケジューラーでComfyUIを自動起動する設定
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\ComfyUI\main.py --port 8188" -WorkingDirectory "C:\path\to\ComfyUI"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "ComfyUI" -Action $action -Trigger $trigger -Description "ComfyUI Server"
```

---

## 🔗 関連ファイル

- `test_comfyui_civitai.py` - ComfyUI統合テスト
- `test_api_endpoints.py` - APIエンドポイントテスト
- `unified_api_server.py` - 統合APIサーバー

---

## 💡 ヒント

1. **GPU使用**: NVIDIA GPUがある場合、自動的にGPUを使用します
2. **CPU使用**: GPUがない場合でもCPUで動作します（遅い）
3. **モデル配置**: `ComfyUI/models/checkpoints/`にモデルを配置
4. **カスタムノード**: `ComfyUI/custom_nodes/`にカスタムノードを配置

