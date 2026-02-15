# 🎤 Style-Bert-VITS2でレミ声固定 - 完全ガイド

**秘書レミ完全体の最終仕上げ：専用ボイスモデルの学習**

---

## 📋 目次

1. [概要](#概要)
2. [Style-Bert-VITS2のセットアップ](#style-bert-vits2のセットアップ)
3. [レミ声データの準備](#レミ声データの準備)
4. [モデル学習](#モデル学習)
5. [ManaOS統合](#manaos統合)
6. [トラブルシューティング](#トラブルシューティング)

---

## 概要

Style-Bert-VITS2は、日本語に特化した高品質な音声合成モデルです。
レミの声データを学習させることで、**専用のレミボイス**を作成できます。

### メリット

- ✅ **自然な日本語音声**: 日本語に最適化されたモデル
- ✅ **声の個性**: レミ専用の声を作成可能
- ✅ **ローカル運用**: 完全オフラインで動作
- ✅ **追加学習**: 既存モデルに追加学習も可能

---

## Style-Bert-VITS2のセットアップ

### 1. リポジトリのクローン

```powershell
# 作業ディレクトリに移動
cd C:\Users\mana4\Desktop

# Style-Bert-VITS2をクローン
git clone https://github.com/litagin02/Style-Bert-VITS2.git
cd Style-Bert-VITS2
```

### 2. 依存関係のインストール

```powershell
# Python環境をアクティベート（仮想環境を使用している場合）

# 依存関係をインストール
pip install -r requirements.txt

# PyTorch（CUDA対応版）をインストール
# RTX 5080を使用する場合
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. モデルファイルのダウンロード

```powershell
# 事前学習済みモデルをダウンロード
# （公式リポジトリの手順に従う）
```

---

## レミ声データの準備

### 1. 音声データの収集

レミの声データを準備します：

- **推奨**: 5-10分の音声データ
- **フォーマット**: WAV形式、16kHz、モノラル
- **品質**: ノイズが少なく、クリアな音声

### 2. 音声データの前処理

```powershell
# 音声ファイルを準備
# 例: remi_voice_data/
#   - remi_001.wav
#   - remi_002.wav
#   - ...

# サンプリングレートを統一（16kHz）
# FFmpegを使用
ffmpeg -i input.wav -ar 16000 -ac 1 output.wav
```

### 3. テキストファイルの準備

各音声ファイルに対応するテキストファイルを作成：

```
remi_voice_data/
  - remi_001.wav
  - remi_001.txt  (内容: "こんにちは、レミです。")
  - remi_002.wav
  - remi_002.txt  (内容: "お疲れ様です。")
  - ...
```

---

## モデル学習

### 1. データセットの準備

```powershell
# Style-Bert-VITS2のデータセット形式に変換
# スクリプトを使用（公式リポジトリ参照）
python preprocess.py --input_dir remi_voice_data --output_dir dataset/remi
```

### 2. 学習設定

`config.json`を編集：

```json
{
  "model": {
    "name": "remi_voice",
    "n_speakers": 1,
    "sample_rate": 24000
  },
  "train": {
    "batch_size": 4,
    "epochs": 100,
    "save_interval": 10
  }
}
```

### 3. 学習実行

```powershell
# 学習を開始
python train.py --config config.json

# GPU使用状況を確認
nvidia-smi
```

### 4. 学習時間の目安

- **RTX 5080**: 約2-4時間（100エポック）
- **CPU**: 約10-20時間（非推奨）

---

## ManaOS統合

### 1. Style-Bert-VITS2 APIサーバーの起動

```powershell
# Style-Bert-VITS2のAPIサーバーを起動
cd Style-Bert-VITS2
python api_server.py --model_path models/remi_voice --port 5000
```

### 2. 環境変数の設定

`.env`ファイルに追加：

```env
# Style-Bert-VITS2設定
VOICE_TTS_ENGINE=style_bert_vits2
STYLE_BERT_VITS2_URL=http://127.0.0.1:5000
STYLE_BERT_VITS2_SPEAKER_ID=0  # レミのスピーカーID
```

### 3. ManaOS統合APIの確認

```powershell
# 統合APIサーバーを起動
python unified_api_server.py

# テスト
curl -X POST http://127.0.0.1:9502/api/voice/synthesize `
  -H "Content-Type: application/json" `
  -d "{\"text\": \"こんにちは、レミです。\"}"
```

---

## トラブルシューティング

### 問題1: 学習が遅い

**解決策**:
- GPU使用を確認: `nvidia-smi`
- バッチサイズを調整
- 混合精度学習を有効化

### 問題2: 音声品質が低い

**解決策**:
- 学習データの品質を向上
- エポック数を増やす
- 学習率を調整

### 問題3: APIサーバーが起動しない

**解決策**:
- ポートが使用中でないか確認
- モデルパスが正しいか確認
- ログを確認

---

## 次のステップ

1. **追加学習**: より多くのデータで追加学習
2. **感情表現**: 感情ラベルを追加して感情表現を強化
3. **スタイル調整**: 話速・音高・抑揚の調整

---

## 参考リンク

- [Style-Bert-VITS2 GitHub](https://github.com/litagin02/Style-Bert-VITS2)
- [公式ドキュメント](https://github.com/litagin02/Style-Bert-VITS2/wiki)

---

**レミ声固定、完成！** 🎉

