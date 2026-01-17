# ✅ CASTLE-EX 学習開始 最終チェックリスト

## 🎉 準備完了！

すべての準備が完了しました。以下の確認が完了しています：

---

## ✅ 完了項目

### 1. データセット
- ✅ `castle_ex_dataset_v1_0_train.jsonl` (3055件)
- ✅ `castle_ex_dataset_v1_0_eval.jsonl` (354件)
- ✅ データセット統計: `castle_ex_dataset_v1_0_stats.json`

### 2. 学習スケジュール
- ✅ `castle_ex_schedule_v1_0.json` (25エポック、Phase 1-3)
- ✅ 学習サマリー: `training_summary_v1_0.txt`

### 3. 評価パイプライン
- ✅ `castle_ex_evaluator_fixed.py` 動作確認済み
- ✅ Ollama統合確認済み（qwen2.5:7b）
- ✅ 評価結果出力確認済み

### 4. 設定ファイル
- ✅ `castle_ex_training_config.yaml` (Axolotl用)
- ✅ `castle_ex_training_helper.py` (学習ヘルパー)

### 5. 自動化スクリプト
- ✅ `run_training.py` (学習実行準備スクリプト)
- ✅ `start_training.bat` (Windows用学習開始スクリプト)
- ✅ `start_training.sh` (Linux/Mac用学習開始スクリプト)

---

## 🚀 学習開始手順

### ステップ1: 外部トレーナーのインストール

**Axolotlの場合:**
```bash
pip install axolotl
```

**LLaMA-Factoryの場合:**
```bash
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e .
```

### ステップ2: 学習実行

**方法1: 自動スクリプトを使用（推奨）**
```bash
# Windows
start_training.bat

# Linux/Mac
./start_training.sh
```

**方法2: 手動実行**

**Axolotlの場合:**
```bash
axolotl train castle_ex_training_config.yaml
```

**LLaMA-Factoryの場合:**
```bash
llama-factory train \
  --model_name_or_path <ベースモデル> \
  --dataset castle_ex_dataset_v1_0_train.jsonl \
  --output_dir ./outputs/castle_ex_v1_0 \
  --num_train_epochs 25
```

### ステップ3: 評価実行

学習完了後:
```bash
python castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model <学習済みモデル名>
```

---

## 📊 学習スケジュール詳細

### Phase 1: Epoch 1-3（ウォームアップ）
- **Layer配分**: L0:15% / L1:20% / L2:10% / L3:15% / L4:10% / L5:20% / L6:10%
- **Negative Ratio**: 0.25 (25%)
- **推奨学習率**: 2.0e-5

### Phase 2: Epoch 4-10（因果と統合へ寄せる）
- **Layer配分**: L0:8% / L1:10% / L2:7% / L3:12% / L4:13% / L5:30% / L6:20%
- **Negative Ratio**: 0.30 (30%)
- **推奨学習率**: 1.5e-5 → 1e-5

### Phase 3: Epoch 11-25（実戦）
- **Layer配分**: L0:5% / L1:7% / L2:3% / L3:10% / L4:10% / L5:25% / L6:40%
- **Negative Ratio**: 0.33 (33%)
- **推奨学習率**: 8e-6 → 5e-6

---

## 📋 最終チェックリスト

- [x] データセット準備完了
- [x] 学習スケジュール生成完了
- [x] 評価パイプライン動作確認完了
- [x] 設定ファイル準備完了
- [x] 自動化スクリプト生成完了
- [ ] 外部トレーナーインストール（AxolotlまたはLLaMA-Factory）
- [ ] 学習実行
- [ ] 評価実行
- [ ] 評価結果分析
- [ ] v1.1データ生成

---

## 🎯 次のアクション

1. **外部トレーナーをインストール**（AxolotlまたはLLaMA-Factory）
2. **学習を開始**（`start_training.bat`または手動コマンド）
3. **学習完了を待つ**（25エポック、時間がかかります）
4. **評価を実行**（`castle_ex_evaluator_fixed.py`）
5. **評価結果を分析**（`evaluation_v1_0.json`）
6. **v1.1データを生成**（`CASTLE_EX_V1_1_GENERATION_RULES.md`に従って）

---

**準備完了！学習を開始してください。** 🚀
