# 🚀 CASTLE-EX 学習開始 - 今すぐ実行可能

## ✅ 準備完了！

現在の環境（Python 3.10.6 + PyTorch + Transformers）で学習を開始できます。

---

## 🎯 学習開始方法

### 方法1: バッチファイルで実行（推奨・最も簡単）

```powershell
.\start_training_now.bat
```

このスクリプトは以下を自動実行します:
1. 環境確認
2. ベースモデルの指定（デフォルト: microsoft/Phi-3-mini-4k-instruct）
3. 学習開始確認
4. 学習実行

### 方法2: コマンドラインで直接実行

```powershell
# デフォルト設定で学習開始
python train_castle_ex_full.py --model microsoft/Phi-3-mini-4k-instruct --epochs 25 --batch-size 2 --learning-rate 2.0e-5

# カスタム設定で学習開始
python train_castle_ex_full.py `
  --model <ベースモデル> `
  --train-data castle_ex_dataset_v1_0_train.jsonl `
  --eval-data castle_ex_dataset_v1_0_eval.jsonl `
  --output-dir ./outputs/castle_ex_v1_0 `
  --epochs 25 `
  --batch-size 2 `
  --learning-rate 2.0e-5 `
  --max-length 2048
```

---

## 📊 学習設定

### デフォルト設定
- **ベースモデル**: microsoft/Phi-3-mini-4k-instruct
- **エポック数**: 25
- **バッチサイズ**: 2
- **学習率**: 2.0e-5
- **最大シーケンス長**: 2048
- **Gradient Accumulation**: 4
- **Warmup Steps**: 100

### 学習スケジュール
- **Phase 1 (Epoch 1-3)**: ウォームアップ
- **Phase 2 (Epoch 4-10)**: 因果と統合へ寄せる
- **Phase 3 (Epoch 11-25)**: 実戦

**注意**: 現在の実装では、学習スケジュールの`layer_weights`と`negative_ratio`は自動適用されません。必要に応じて、データセットのフィルタリングを追加してください。

---

## 🎯 推奨ベースモデル

### 小規模モデル（推奨・学習が速い）
- `microsoft/Phi-3-mini-4k-instruct` (デフォルト)
- `microsoft/Phi-3-small-8k-instruct`
- `Qwen/Qwen2.5-0.5B-Instruct`

### 中規模モデル
- `microsoft/Phi-3-medium-4k-instruct`
- `Qwen/Qwen2.5-1.5B-Instruct`
- `Qwen/Qwen2.5-3B-Instruct`

### 大規模モデル（時間がかかります）
- `Qwen/Qwen2.5-7B-Instruct`
- `Qwen/Qwen2.5-14B-Instruct`

---

## 📝 学習完了後の評価

```powershell
python castle_ex_evaluator_fixed.py `
  --eval-data castle_ex_dataset_v1_0_eval.jsonl `
  --output evaluation_v1_0.json `
  --model-type transformers `
  --model ./outputs/castle_ex_v1_0
```

---

## ⚠️ 注意事項

1. **GPUメモリ**: モデルサイズに応じてGPUメモリが必要です
2. **学習時間**: 25エポックの学習には数時間〜数日かかる場合があります
3. **チェックポイント**: 500ステップごとに自動保存されます
4. **ログ**: TensorBoardログは `./outputs/castle_ex_v1_0/logs` に保存されます

---

## 🚀 今すぐ開始

```powershell
.\start_training_now.bat
```

**準備完了！学習を開始してください。** 🚀
