# 🚀 CASTLE-EX 学習開始ガイド

## ✅ 準備完了確認

すべての準備が整いました。以下のファイルが利用可能です：

### データセット
- ✅ `castle_ex_dataset_v1_0.jsonl` (3409件)
- ✅ `castle_ex_dataset_v1_0_train.jsonl` (3055件)
- ✅ `castle_ex_dataset_v1_0_eval.jsonl` (354件)

### 学習スケジュール
- ✅ `castle_ex_schedule_v1_0.json` (25epoch、Phase 1-3)

### 評価ツール
- ✅ `castle_ex_evaluator_fixed.py` (修正済み、Ollama/Transformers統合)

### ヘルパーツール
- ✅ `castle_ex_training_helper.py` (学習スケジュール確認)
- ✅ `castle_ex_training_config.yaml` (Axolotl用設定ファイル)

---

## 🎯 学習実行手順

### Step 1: 学習スケジュール確認

```bash
# 全Phaseの設定を確認
python castle_ex_training_helper.py --schedule castle_ex_schedule_v1_0.json

# 特定のepochの設定を確認
python castle_ex_training_helper.py --schedule castle_ex_schedule_v1_0.json --epoch 1
```

### Step 2: 外部トレーナーで学習実行

外部トレーナー（Axolotl、LLaMA-Factoryなど）で学習を実行：

#### Axolotlの場合

```bash
# 設定ファイルを編集してから実行
axolotl train castle_ex_training_config.yaml
```

#### LLaMA-Factoryの場合

```bash
llama-factory train \
  --model_name_or_path <ベースモデル> \
  --dataset castle_ex_dataset_v1_0_train.jsonl \
  --output_dir ./outputs/castle_ex_v1_0 \
  --num_train_epochs 25
```

**重要**: 各epochで`layer_weights`と`negative_ratio`を適用してください（`castle_ex_schedule_v1_0.json`を参照）。

### Step 3: 評価実行

学習完了後、評価を実行：

```bash
# デバッグモードで動作確認
python castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0_debug.json \
  --max-samples 5 \
  --model-type dummy

# 実際のモデルで評価（Ollama）
python castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model qwen2.5:14b
```

---

## 📊 学習スケジュール概要

### Phase 1: Epoch 1-3（ウォームアップ）
- Layer配分: L0-2: 45% / L3-4: 25% / L5-6: 30%
- Negative Ratio: 0.25
- 学習率: 2.0e-5

### Phase 2: Epoch 4-10（因果と統合へ寄せる）
- Layer配分: L0-2: 25% / L3-4: 25% / L5-6: 50%
- Negative Ratio: 0.30
- 学習率: 1.5e-5 → 1e-5

### Phase 3: Epoch 11-25（実戦）
- Layer配分: L0-2: 15% / L3-4: 20% / L5: 25% / L6: 40%
- Negative Ratio: 0.33
- 学習率: 8e-6 → 5e-6

---

## 📝 評価結果の提出

学習を実行したら、以下を共有してください：

1. **学習ログ**: 各epochのloss、accuracy
2. **評価結果**: `evaluation_v1_0.json`（または`overall`と`negative_by_error_type`の数値だけでもOK）
3. **統計比較**: v1.0 vs v1.1の統計比較（v1.1生成後）

これらがあれば、次のv1.1データ生成の具体的な指示（どのテンプレを何件増やすか）を数値で出します。

---

## 🎯 次のアクション

1. ✅ **学習準備完了**: すべてのファイルとツールが準備済み
2. ⏳ **学習実行**: 外部トレーナーで`castle_ex_schedule_v1_0.json`を参照して学習
3. ⏳ **評価実行**: `castle_ex_evaluator_fixed.py`で実際のモデルを接続して評価
4. ⏳ **評価結果分析**: `evaluation_v1_0.json`を確認して弱点を特定
5. ⏳ **v1.1データ生成**: `CASTLE_EX_V1_1_GENERATION_RULES.md`に従って追加生成

---

**準備完了！学習を開始してください。** 🚀
