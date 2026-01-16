# LTX-2 Gemmaモデルの完全セットアップ手順

## 現在の状況

✅ **LTX-2モデル**: インストール完了（40.36 GB）
❌ **Gemmaモデル**: `tokenizer.model`が不足（アクセス権限が必要）

## 問題

`google/gemma-3-12b-it`は**gatedリポジトリ**のため、アクセス権限が必要です。

## 解決手順

### ステップ1: Hugging Faceでアクセス申請

1. ブラウザで以下にアクセス:
   https://huggingface.co/google/gemma-3-12b-it

2. 「Request access」ボタンをクリック
3. アクセスが承認されるまで待つ（通常、すぐに承認されます）

### ステップ2: Hugging Face CLIで認証

```powershell
# Hugging Face CLIをインストール（まだの場合）
pip install huggingface_hub[cli]

# 認証
huggingface-cli login
```

認証トークンを入力します（Hugging Faceの設定ページから取得できます）

### ステップ3: Gemmaモデルをダウンロード

認証後、再度ダウンロードスクリプトを実行:

```powershell
python download_ltx2_models.py
```

### ステップ4: ダウンロード完了の確認

```powershell
python check_ltx2_models.py
```

以下のファイルが存在することを確認:
- `C:\ComfyUI\models\text_encoders\gemma-3-12b-it-qat-q4_0-unquantized\tokenizer.model`
- `C:\ComfyUI\models\text_encoders\gemma-3-12b-it-qat-q4_0-unquantized\model-*.safetensors`

### ステップ5: ComfyUIを再起動

モデルを認識させるために、ComfyUIを再起動してください。

### ステップ6: 動画生成を試行

```powershell
python generate_mana_mufufu_ltx2_video.py
```

## 手動ダウンロード（代替方法）

CLIが使えない場合は、ブラウザから手動でダウンロード:

1. https://huggingface.co/google/gemma-3-12b-it にアクセス
2. 必要なファイルをダウンロード:
   - `tokenizer.model`
   - `model-00001-of-00005.safetensors`
   - `model-00002-of-00005.safetensors`
   - `model-00003-of-00005.safetensors`
   - `model-00004-of-00005.safetensors`
   - `model-00005-of-00005.safetensors`
   - `preprocessor_config.json`
3. 以下のパスに配置:
   `C:\ComfyUI\models\text_encoders\gemma-3-12b-it-qat-q4_0-unquantized\`

## 注意事項

- Gemmaモデルは数GBのサイズがあります
- ダウンロードには時間がかかります
- インターネット接続を維持してください
