# ✅ CASTLE-EX 学習準備完了

## 🎉 すべての準備が整いました

学習を開始する準備が完了しました。以下の確認が完了しています：

### ✅ 確認済み項目

1. **データセット**
   - ✅ 訓練データ: `castle_ex_dataset_v1_0_train.jsonl` (3055件)
   - ✅ 評価データ: `castle_ex_dataset_v1_0_eval.jsonl` (354件)

2. **学習スケジュール**
   - ✅ `castle_ex_schedule_v1_0.json` (25エポック、Phase 1-3)
   - ✅ Phase 1 (Epoch 1-3): ウォームアップ
   - ✅ Phase 2 (Epoch 4-10): 因果と統合へ寄せる
   - ✅ Phase 3 (Epoch 11-25): 実戦

3. **評価パイプライン**
   - ✅ `castle_ex_evaluator_fixed.py` 動作確認済み
   - ✅ Ollama統合確認済み（qwen2.5:7b）
   - ✅ 評価結果出力確認済み

4. **設定ファイル**
   - ✅ `castle_ex_training_config.yaml` (Axolotl用)
   - ✅ `training_summary_v1_0.txt` (学習サマリー)

---

## 🚀 学習開始手順

### オプション1: Axolotlを使用する場合

```bash
# 1. Axolotlをインストール（未インストールの場合）
pip install axolotl

# 2. 設定ファイルを確認・編集
# castle_ex_training_config.yaml を編集してベースモデルを指定

# 3. 学習実行
axolotl train castle_ex_training_config.yaml
```

### オプション2: LLaMA-Factoryを使用する場合

```bash
# 1. LLaMA-Factoryをインストール（未インストールの場合）
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e .

# 2. 学習実行
llama-factory train \
  --model_name_or_path <ベースモデル> \
  --dataset castle_ex_dataset_v1_0_train.jsonl \
  --output_dir ./outputs/castle_ex_v1_0 \
  --num_train_epochs 25
```

### オプション3: カスタムトレーナーを使用する場合

各epochで以下の設定を適用してください：

1. **学習スケジュールの読み込み**
   ```python
   import json
   with open('castle_ex_schedule_v1_0.json', 'r') as f:
       schedule = json.load(f)
   ```

2. **各epochの設定取得**
   ```python
   epoch_config = schedule['epochs'][epoch - 1]
   layer_weights = epoch_config['layer_weights']
   negative_ratio = epoch_config['negative_ratio']
   ```

3. **データのフィルタリング**
   - `layer_weights`に基づいてデータをサンプリング
   - `negative_ratio`に基づいて正例/負例の比率を調整

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

## 📝 学習完了後の評価

学習完了後、以下のコマンドで評価を実行してください：

```bash
# 評価実行（Ollama）
python castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model <学習済みモデル名>

# または、Transformersを使用する場合
python castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type transformers \
  --model <モデルパス>
```

---

## 🎯 次のステップ

1. ✅ **学習準備完了**: すべてのファイルとツールが準備済み
2. ⏳ **外部トレーナーのインストール**: AxolotlまたはLLaMA-Factoryをインストール
3. ⏳ **学習実行**: 外部トレーナーで`castle_ex_schedule_v1_0.json`を参照して学習
4. ⏳ **評価実行**: `castle_ex_evaluator_fixed.py`で実際のモデルを接続して評価
5. ⏳ **評価結果分析**: `evaluation_v1_0.json`を確認して弱点を特定
6. ⏳ **v1.1データ生成**: `CASTLE_EX_V1_1_GENERATION_RULES.md`に従って追加生成

---

## 📋 チェックリスト

- [x] データセット準備完了
- [x] 学習スケジュール生成完了
- [x] 評価パイプライン動作確認完了
- [x] 設定ファイル準備完了
- [ ] 外部トレーナーインストール（AxolotlまたはLLaMA-Factory）
- [ ] 学習実行
- [ ] 評価実行
- [ ] 評価結果分析
- [ ] v1.1データ生成

---

**準備完了！外部トレーナーをインストールして学習を開始してください。** 🚀
