# 🚀 CASTLE-EX 学習開始

## ✅ 学習を開始しました

学習がバックグラウンドで実行中です。

---

## 📊 学習設定

- **ベースモデル**: microsoft/Phi-3-mini-4k-instruct
- **エポック数**: 25
- **バッチサイズ**: 2
- **Gradient Accumulation**: 4（実効バッチサイズ: 8）
- **学習率**: 2.0e-5
- **最大シーケンス長**: 2048
- **訓練データ**: 3055件
- **評価データ**: 354件

---

## 📍 進行状況の確認方法

### 1. 監視スクリプトを使用（推奨）

```powershell
python monitor_training.py
```

### 2. チェックポイントの確認

```powershell
dir outputs\castle_ex_v1_0\checkpoint-*
```

### 3. TensorBoardで可視化

```powershell
tensorboard --logdir ./outputs/castle_ex_v1_0/logs
```

ブラウザで `http://127.0.0.1:6006` を開く

### 4. 学習状態ファイルの確認

```powershell
type outputs\castle_ex_v1_0\trainer_state.json
```

---

## ⏱️ 予想学習時間

- **モデルダウンロード**: 数分（初回のみ、既にダウンロード済みの可能性あり）
- **データ前処理**: 数分〜10分程度（3055件）
- **最初のチェックポイント**: 500ステップ後（数十分〜1時間程度）
- **完全な学習（25エポック）**: 数時間〜半日程度（GPU性能による）

**RTX 5080（15.9GB）**: 比較的高速に処理される見込み

---

## 📝 学習完了後の手順

### 1. 学習完了の確認

学習が完了すると、以下のメッセージが表示されます：
```
[OK] 学習完了
モデルを保存中: ./outputs/castle_ex_v1_0
[OK] モデル保存完了
```

### 2. 評価の実行

```powershell
python castle_ex_evaluator_fixed.py `
  --eval-data castle_ex_dataset_v1_0_eval.jsonl `
  --output evaluation_v1_0.json `
  --model-type transformers `
  --model ./outputs/castle_ex_v1_0
```

### 3. 評価結果の分析

`evaluation_v1_0.json`を確認して、以下の指標を分析：
- `overall`: 全体の評価指標
- `by_layer`: レイヤー別の精度
- `by_axes_combo`: 軸組み合わせ別の精度
- `negative_by_error_type`: エラータイプ別の精度

### 4. v1.1データ生成

評価結果に基づいて、`CASTLE_EX_V1_1_GENERATION_RULES.md`に従ってv1.1データを生成。

---

## 🔍 トラブルシューティング

### 学習が停止した場合

1. **GPUメモリ不足**: 
   ```powershell
   python train_castle_ex_full.py --model microsoft/Phi-3-mini-4k-instruct --epochs 25 --batch-size 1 --learning-rate 2.0e-5
   ```

2. **メモリ不足**: 
   ```powershell
   python train_castle_ex_full.py --model microsoft/Phi-3-mini-4k-instruct --epochs 25 --batch-size 2 --max-length 1024
   ```

3. **エラー確認**: コンソール出力を確認

### 学習を再開する場合

```powershell
# 最後のチェックポイントから再開
python train_castle_ex_full.py `
  --model ./outputs/castle_ex_v1_0 `
  --epochs 25 `
  --batch-size 2 `
  --learning-rate 2.0e-5
```

---

## 📋 便利なコマンド

```powershell
# 進行状況を確認
python monitor_training.py

# チェックポイント一覧
dir outputs\castle_ex_v1_0\checkpoint-*

# TensorBoard起動
tensorboard --logdir ./outputs/castle_ex_v1_0/logs

# GPUメモリ使用量確認
python -c "import torch; print(f'GPUメモリ: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB / {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f}GB')"
```

---

**学習はバックグラウンドで実行中です。進行状況は定期的に確認してください。** 🚀
