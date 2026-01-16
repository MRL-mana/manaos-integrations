# LTX-2モデルとGemmaモデルのインストールガイド

## 概要

LTX-2動画生成機能を使用するには、以下のモデルが必要です：

1. **LTX-2 19B Distilledモデル** (約40GB)
2. **Gemma 3-12B IT Text Encoderモデル**

## 自動インストール（推奨）

### Pythonスクリプトを使用

```powershell
# バックグラウンドで実行（推奨）
python download_ltx2_models.py
```

このスクリプトは以下を自動的に実行します：
- ComfyUIパスの確認
- 必要なディレクトリの作成
- LTX-2モデルのダウンロード
- Gemmaモデルのダウンロード

### PowerShellスクリプトを使用

```powershell
.\download_ltx2_models.ps1
```

## 手動インストール

### 1. LTX-2モデルのダウンロード

1. **Hugging Faceからダウンロード**
   - URL: https://huggingface.co/Lightricks/LTX-2
   - ファイル: `ltx-2-19b-distilled.safetensors` (約40GB)

2. **配置場所**
   - `C:\ComfyUI\models\checkpoints\ltx-2-19b-distilled.safetensors`
   - または `C:\ComfyUI\models\checkpoints\LTX-Video\ltx-2-19b-distilled.safetensors`

### 2. Gemma 3 Text Encoderモデルのダウンロード

1. **Hugging Faceからダウンロード**
   - URL: https://huggingface.co/google/gemma-3-12b-it
   - または: https://huggingface.co/chenly124/gemma-3-12b-it-qat-q4_0-unquantized

2. **配置場所**
   - `C:\ComfyUI\models\text_encoders\gemma-3-12b-it-qat-q4_0-unquantized\`

## インストール後の確認

### 1. モデルファイルの確認

```powershell
# LTX-2モデル
Get-ChildItem "C:\ComfyUI\models\checkpoints" -Filter "*ltx-2-19b-distilled*.safetensors"

# Gemmaモデル
Get-ChildItem "C:\ComfyUI\models\text_encoders" -Recurse -Filter "*gemma*3*12b*"
```

### 2. ComfyUIの再起動

モデルを認識させるために、ComfyUIを再起動してください。

### 3. 動作確認

```powershell
python generate_mana_mufufu_ltx2_video.py
```

## トラブルシューティング

### モデルが見つからない

- モデルファイルが正しいパスに配置されているか確認
- ComfyUIを再起動してモデルを再読み込み
- ファイル名が正確か確認（大文字小文字に注意）

### ダウンロードが失敗する

- インターネット接続を確認
- Hugging Face CLIをインストール: `pip install huggingface_hub[cli]`
- 手動でダウンロードして配置

### ディスク容量不足

- LTX-2モデルは約40GB、Gemmaモデルも数GB必要
- 十分な空き容量があるか確認

## 次のステップ

モデルのインストールが完了したら：

1. ComfyUIを再起動
2. `ltx2_video_integration.py`のモデル名を更新
3. 動画生成を試す: `python generate_mana_mufufu_ltx2_video.py`
