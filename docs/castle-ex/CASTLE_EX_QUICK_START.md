# CASTLE-EX クイックスタートガイド

## 🚀 学習準備完了

すべての準備が整いました。以下の手順で学習を開始できます。

---

## ✅ 準備完了チェックリスト

- [x] データセット固定: `castle_ex_dataset_v1_0.jsonl` (3409件)
- [x] train/eval分割: ハッシュベース固定分割完了
  - [x] 訓練データ: `castle_ex_dataset_v1_0_train.jsonl` (3055件, 89.6%)
  - [x] 評価データ: `castle_ex_dataset_v1_0_eval.jsonl` (354件, 10.4%)
- [x] 学習スケジュール生成: `castle_ex_schedule_v1_0.json` (25epoch、Phase 1-3)
- [x] 評価パイプライン修正: `castle_ex_evaluator_fixed.py` (gold/pred抽出、デバッグ出力、Ollama/Transformers統合)

---

## 📋 学習実行（外部トレーナー）

### Step 1: 学習スケジュールを読み込む

`castle_ex_schedule_v1_0.json`を読み込み、各epochの設定を適用：

```python
import json

with open('castle_ex_schedule_v1_0.json', 'r', encoding='utf-8') as f:
    schedule = json.load(f)

for epoch_config in schedule['epochs']:
    epoch = epoch_config['epoch']
    layer_weights = epoch_config['layer_weights']
    negative_ratio = epoch_config['negative_ratio']
    
    # 外部トレーナーで適用
    # - layer_weights: 各Layerの重み
    # - negative_ratio: 負例の割合
```

### Step 2: 学習実行

外部トレーナー（Axolotl、LLaMA-Factoryなど）で学習を実行：

```bash
# 例: Axolotlの場合
axolotl train castle_ex_config.yaml

# 例: LLaMA-Factoryの場合
llama-factory train \
  --model_name_or_path <ベースモデル> \
  --dataset castle_ex_dataset_v1_0_train.jsonl \
  --output_dir ./outputs/castle_ex_v1_0
```

**重要**: 各epochで`layer_weights`と`negative_ratio`を適用してください。

---

## 📊 評価実行

### Step 1: デバッグモードで動作確認

```bash
# 最初の5サンプルだけ評価（gold/pred抽出の確認用）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0_debug.json \
  --max-samples 5 \
  --model-type dummy
```

**確認**: `evaluation_v1_0_debug.json`の`debug_samples`で`gold_answer`と`pred_answer`が正しく記録されているか確認

---

### Step 2: 実際のモデルで評価

#### Ollamaを使用

```bash
# Ollamaで評価（モデル名を指定）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model qwen2.5:14b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

#### Transformersを使用

```bash
# Transformersで評価（モデルパスを指定）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type transformers \
  --model <モデルパス>
```

#### 外部トレーナーのチェックポイントを使用

外部トレーナーのチェックポイントを使用する場合、`castle_ex_evaluator_fixed.py`の`main()`関数に`custom`タイプを追加：

```python
elif args.model_type == 'custom':
    # カスタムモデルローダー
    def custom_predict(prompt: str) -> str:
        # 外部トレーナーのチェックポイントを読み込み
        # モデルで予測を生成
        # 予測テキストを返す
        pass
    
    model_predictor = custom_predict
```

---

## 📈 評価結果分析

評価結果（`evaluation_v1_0.json`）を確認：

### 確認ポイント

1. **`overall`（6指標）**: 0.0以外の値になっているか
2. **`by_layer`（Layer 0-6の精度）**: 0.0以外の値になっているか
3. **`by_axes_combo`（軸組み合わせ別精度）**: バランスが取れているか
4. **`negative_by_error_type`（error_type別のprecision/recall）**: 偏りがないか

### 弱点の特定

以下の順で確認：

1. **Negative Detection** (`overall.negative_detection`): < 80%なら弱い
2. **Axis Consistency** (`overall.axis_consistency`): < 85%なら弱い
3. **Context Sensitivity** (`overall.context_sensitivity`): < 75%なら弱い
4. **Emotion Appropriateness** (`overall.emotion_appropriateness`): < 80%なら弱い
5. **Paraphrase Robustness** (`overall.paraphrase_robustness`): < 90%なら弱い
6. **Causal Validity** (`overall.causal_validity`): < 80%なら弱い

---

## 🎯 v1.1データ生成

評価結果に基づいて、`CASTLE_EX_V1_1_GENERATION_RULES.md`に従ってv1.1データを生成：

```bash
# 例: Negative Detectionが低い場合
python castle_ex/castle_ex_data_generator.py \
  --count 300 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --output castle_ex_dataset_v1_1.jsonl
```

---

## 📝 学習ログと評価結果の提出

学習を実行したら、以下を共有してください：

1. **学習ログ**: 各epochのloss、accuracy
2. **評価結果**: `evaluation_v1_0.json`（または`overall`と`negative_by_error_type`の数値だけでもOK）
3. **統計比較**: v1.0 vs v1.1の統計比較（v1.1生成後）

これらがあれば、次のv1.1データ生成の具体的な指示（どのテンプレを何件増やすか）を数値で出します。

---

## 🔗 関連ファイル

### データセット
- `castle_ex_dataset_v1_0.jsonl`: 固定版データセット（3409件）
- `castle_ex_dataset_v1_0_train.jsonl`: 訓練データ（3055件）
- `castle_ex_dataset_v1_0_eval.jsonl`: 評価データ（354件）

### 学習スケジュール
- `castle_ex_schedule_v1_0.json`: 学習スケジュール（25epoch、Phase 1-3）

### 評価ツール
- `castle_ex_evaluator_fixed.py`: 修正済みevaluator（gold/pred抽出、デバッグ出力、Ollama/Transformers統合）

### ガイド
- `CASTLE_EX_LEARNING_GUIDE.md`: 学習ガイド（完全版）
- `CASTLE_EX_EVALUATION_SETUP.md`: 評価セットアップガイド
- `CASTLE_EX_EVALUATION_DEBUG_GUIDE.md`: 評価デバッグガイド
- `CASTLE_EX_V1_1_GENERATION_RULES.md`: v1.1データ生成ルール（固定版）

---

## 🎯 次のアクション

1. **学習実行**: 外部トレーナーで`castle_ex_schedule_v1_0.json`を参照して学習
2. **評価実行**: `castle_ex_evaluator_fixed.py`で実際のモデルを接続して評価
3. **評価結果分析**: `evaluation_v1_0.json`を確認して弱点を特定
4. **v1.1データ生成**: `CASTLE_EX_V1_1_GENERATION_RULES.md`に従って追加生成

**準備完了！学習を開始してください。** 🚀

