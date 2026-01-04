# ComfyUI インストール手順（母艦用）

## 🎯 目標

母艦（新PC）にComfyUIをインストールして起動する。

---

## 🚀 クイックスタート

### 1行でインストール＆起動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\install_comfyui.ps1
.\start_comfyui_local.ps1
```

---

## 📋 詳細手順

### ステップ1: インストール確認

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\check_comfyui_installation.ps1
```

**結果:**
- ✅ ComfyUIがインストール済み → ステップ2へ
- ❌ ComfyUIが見つからない → ステップ1-2へ

---

### ステップ1-2: ComfyUIをインストール

```powershell
.\install_comfyui.ps1
```

**オプション:**
```powershell
# CPUのみの場合
.\install_comfyui.ps1 -CPUOnly

# カスタムパスにインストール
.\install_comfyui.ps1 -InstallPath "D:\ComfyUI"
```

**インストール内容:**
- GitからComfyUIをクローン（C:\ComfyUI）
- PyTorchをインストール（GPU対応）
- 依存関係をインストール

**所要時間:** 約5-10分（ネットワーク速度による）

---

### ステップ2: ComfyUIを起動

```powershell
.\start_comfyui_local.ps1
```

**または手動で:**
```powershell
cd C:\ComfyUI
python main.py --port 8188
```

**起動確認:**
- ブラウザで `http://localhost:8188` にアクセス
- ComfyUIのUIが表示されればOK

---

### ステップ3: 統合APIサーバーと連携

```powershell
# 統合APIサーバーを起動
python unified_api_server.py

# 別ターミナルでテスト
python test_comfyui_civitai.py
```

---

## 🔧 トラブルシューティング

### Pythonが見つからない

```powershell
# Pythonをインストール
# https://www.python.org/downloads/
```

### Gitが見つからない

```powershell
# Gitをインストール
# https://git-scm.com/download/win
```

### ポート8188が使用中

```powershell
# 使用中のプロセスを確認
netstat -ano | findstr :8188

# タスクマネージャーで該当プロセスを終了
```

### GPUが認識されない

```powershell
# NVIDIAドライバーをインストール
# https://www.nvidia.com/Download/index.aspx

# GPU確認
nvidia-smi
```

### メモリ不足

```powershell
# 低VRAMモードで起動
cd C:\ComfyUI
python main.py --port 8188 --lowvram

# またはCPUモード
python main.py --port 8188 --cpu
```

---

## 📝 次のステップ

ComfyUIが起動したら:

1. ✅ 統合APIサーバーで動作確認
2. ✅ 画像生成テスト
3. ✅ CivitAIと連携してモデル検索・ダウンロード
4. ✅ Google Driveに自動保存（設定済みの場合）

---

## 🔗 関連ファイル

- `install_comfyui.ps1` - 自動インストールスクリプト
- `start_comfyui_local.ps1` - 起動スクリプト
- `check_comfyui_installation.ps1` - インストール確認スクリプト
- `COMFYUI_LOCAL_SETUP.md` - 詳細セットアップガイド


















