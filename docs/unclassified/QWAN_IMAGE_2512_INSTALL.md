# Qwan-image-2512 インストールガイド

## 📋 概要

Qwan-image-2512モデルをComfyUIにインストールするためのガイドです。

## 🚀 自動インストール

### 方法1: Pythonスクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python install_qwan_image_2512.py
```

このスクリプトは以下を自動実行します：
1. ComfyUIのインストール場所を検索
2. CivitAIでモデルを検索
3. モデルをダウンロード
4. ComfyUIのcheckpointsフォルダに配置

### 方法2: PowerShellスクリプトを使用

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\install_qwan_image_2512.ps1
```

## 🔍 手動インストール

自動インストールが失敗した場合、以下の手順で手動インストールできます。

### ステップ1: CivitAIでモデルを検索

1. https://civitai.com にアクセス
2. 「Qwan-image-2512」で検索
3. モデルページを開く

### ステップ2: モデルIDを取得

モデルページのURLからIDを取得します：
- 例: `https://civitai.com/models/12345` → IDは `12345`

### ステップ3: モデルをダウンロード

1. モデルページで「Download」ボタンをクリック
2. `.safetensors`ファイルをダウンロード

### ステップ4: ComfyUIに配置

ダウンロードしたファイルを以下のフォルダに配置：

```
C:\ComfyUI\models\checkpoints\
```

### ステップ5: ComfyUIを再起動

ComfyUIを再起動すると、新しいモデルが認識されます。

## 📝 確認方法

ComfyUIを起動後、`CheckpointLoaderSimple`ノードでモデルを選択できることを確認してください。

## ⚠️ トラブルシューティング

### モデルが見つからない

- CivitAIで正確なモデル名を確認してください
- モデル名が異なる可能性があります（例: "Qwan Image 2512"、"Qwan-Image-2512"など）

### ダウンロードが失敗する

- インターネット接続を確認してください
- CivitAI APIキーを設定すると、より確実にダウンロードできます：
  ```powershell
  $env:CIVITAI_API_KEY = "your_api_key_here"
  ```

### ComfyUIが見つからない

以下のパスを確認してください：
- `C:\ComfyUI`
- `%USERPROFILE%\ComfyUI`
- `%USERPROFILE%\Desktop\ComfyUI`
- `D:\ComfyUI`
- `E:\ComfyUI`

## 📚 関連ファイル

- `install_qwan_image_2512.py` - Pythonインストールスクリプト
- `install_qwan_image_2512.ps1` - PowerShellインストールスクリプト
- `civitai_integration.py` - CivitAI統合モジュール




