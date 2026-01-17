# CASTLE-EX 学習ガイド（v1.0）

## 📦 固定版データセット

- **データセット**: `castle_ex_dataset_v1_0.jsonl` (3409件)
- **統計ファイル**: `castle_ex_dataset_v1_0_stats.json`
- **訓練データ**: `castle_ex_dataset_v1_0_train.jsonl` (3055件, 89.6%)
- **評価データ**: `castle_ex_dataset_v1_0_eval.jsonl` (354件, 10.4%)

### データセット統計（v1.0）

- **総データ数**: 3409件
- **負例率**: 29.4%（目標: 30%）
- **error_type分布**: 最小/最大=0.70（目標: >0.7）
- **Layer 2**: 192件（目標: 200件、96%達成）

### Layer別内訳

- Layer 0: 266件（正例: 198, 負例: 68）
- Layer 1: 434件（正例: 340, 負例: 94）
- Layer 2: 192件（正例: 192, 負例: 0）
- Layer 3: 349件（正例: 349, 負例: 0）
- Layer 4: 206件（正例: 206, 負例: 0）
- Layer 5: 1474件（正例: 573, 負例: 901）
- Layer 6: 488件（正例: 486, 負例: 2）

### error_type分布

- logic_error: 226件
- context_miss: 207件
- emotion_mismatch: 158件
- overconfident: 158件
- missing_reason: 158件
- unsafe_action: 158件

---

## 🎯 学習スケジュール（25epoch想定）

### Phase 1: Epoch 1-3（ウォームアップ）

**目的**: 基盤を固める

- **Layer配分**: L0-2: 45% / L3-4: 25% / L5-6: 30%
- **重点**: 同一性、操作、関係の基礎を厚く
- **学習率**: 初期値（例: 2e-5）

**推奨設定**:
```yaml
layer_weights:
  Layer 0: 0.15
  Layer 1: 0.20
  Layer 2: 0.10
  Layer 3: 0.15
  Layer 4: 0.10
  Layer 5: 0.20
  Layer 6: 0.10
```

### Phase 2: Epoch 4-10（因果と統合へ寄せる）

**目的**: 因果関係と統合能力を強化

- **Layer配分**: L0-2: 25% / L3-4: 25% / L5-6: 50%
- **重点**: Layer 5（因果層）とLayer 6（統合層）を主役に
- **学習率**: 段階的に下げる（例: 1.5e-5 → 1e-5）

**推奨設定**:
```yaml
layer_weights:
  Layer 0: 0.08
  Layer 1: 0.10
  Layer 2: 0.07
  Layer 3: 0.12
  Layer 4: 0.13
  Layer 5: 0.30
  Layer 6: 0.20
```

### Phase 3: Epoch 11-25（実戦）

**目的**: 統合能力を最優先、hard negativeも効かせる

- **Layer配分**: L0-2: 15% / L3-4: 20% / L5: 25% / L6: 40%
- **重点**: Layer 6（統合層）を最優先、実運用に近い状況を学習
- **学習率**: さらに下げる（例: 8e-6 → 5e-6）

**推奨設定**:
```yaml
layer_weights:
  Layer 0: 0.05
  Layer 1: 0.07
  Layer 2: 0.03
  Layer 3: 0.10
  Layer 4: 0.10
  Layer 5: 0.25
  Layer 6: 0.40
```

---

## 📊 評価の順番（迷子回避）

学習後に見る指標は**この順**で確認：

### 1. Negative Detection（負例検出）

**目的**: 負例を負例として検出できるか

**評価方法**:
- 負例データに対する誤分類率
- error_type別の検出精度

**目標**: 誤分類率 < 10%

**弱点が見つかった場合**:
- error_typeごとに hard negative を負例の7%まで上げる（増やしすぎ注意）

---

### 2. Axis Consistency（軸の一貫性）

**目的**: 軸の矛盾が減っているか

**評価方法**:
- `axis_evidence`と実際の応答の整合性
- 軸の組み合わせ（logic-only, emotion+logic, 3軸統合）の精度

**目標**: 軸一貫性 > 85%

**弱点が見つかった場合**:
- Layer 3/4の`axis_evidence`を強化
- 軸の組み合わせデータを追加

---

### 3. Context Sensitivity（文脈感度）

**目的**: 文脈で返答が変わるか

**評価方法**:
- 同じ発話×違う状況での応答の違い
- Layer 4（文脈基礎層）の精度

**目標**: 文脈感度 > 80%

**弱点が見つかった場合**:
- Layer 4とLayer 6で「同じ発話×違う状況」の対比データを追加
- 文脈スロット（`{place}`, `{situation}`, `{time}`）のバリエーションを増やす

---

### 4. Emotion Appropriateness（感情適切性）

**目的**: 感情に適切に反応できるか

**評価方法**:
- Layer 3（感情基礎層）の精度
- emotion_mismatchの検出率

**目標**: 感情適切性 > 85%

**弱点が見つかった場合**:
- Layer 3を追加しつつ、Layer 6で「共感→状況確認→次の一手」型を増やす
- emotion_mismatchの負例を増やす

---

### 5. Paraphrase Robustness（言い換え耐性）

**目的**: 言い換えに耐えるか

**評価方法**:
- Layer 1（操作層）の精度
- 同義語・言い換えペアの精度

**目標**: 言い換え耐性 > 90%

**弱点が見つかった場合**:
- Layer 1のパラフレーズペアを追加
- スロットテンプレートでバリエーションを増やす

---

### 6. Causal Validity（因果妥当性）

**目的**: state遷移が自然か

**評価方法**:
- Layer 5（因果層）の精度
- state遷移の観測可能性（数値/行動/成果）

**目標**: 因果妥当性 > 80%

**弱点が見つかった場合**:
- Layer 5のstate遷移データを追加
- 観測可能な変化（数値、時間、成果）を明確にする

---

## 🔧 学習前の準備コマンド

### 1. データセット固定と分割

```bash
# データセットをv1.0として固定し、train/evalに分割
python castle_ex/castle_ex_learning_prep.py test_final_complete_v2.jsonl --version v1_0
```

### 2. 学習スケジュール生成

```bash
# 学習スケジュールを生成（25epoch想定）
python castle_ex/castle_ex_schedule_generator.py \
  --epochs 25 \
  --seed castle_ex_v1_0 \
  --output castle_ex_schedule_v1_0.json
```

### 3. データ検証

```bash
# データセットの検証
python castle_ex/castle_ex_data_validator.py castle_ex_dataset_v1_0.jsonl
```

### 4. 統計情報確認

```bash
# 統計情報の表示
python castle_ex/castle_ex_stats_viewer.py castle_ex_dataset_v1_0_stats.json
```

### 5. 評価フォーマット生成（オプション）

```bash
# 標準評価フォーマットのテンプレートを生成
python castle_ex/castle_ex_evaluation_formatter.py \
  --dataset castle_ex_dataset_v1_0_eval.jsonl \
  --seed castle_ex_v1_0 \
  --output evaluation_v1_0.json
```

---

## 📈 学習後の評価フロー

### Step 1: 評価実行

**重要**: まずデバッグモードで動作確認してから、実際のモデルで評価してください。

#### デバッグモード（動作確認）

```bash
# 最初の5サンプルだけ評価（gold/pred抽出の確認用）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0_debug.json \
  --max-samples 5 \
  --model-type dummy
```

**確認ポイント**:
- `debug_samples`に5件のサンプルが記録されている
- `gold_answer`が正しく抽出されている（空でない）
- `pred_answer`が記録されている
- `pred_empty`が全て`false`である

#### 実際のモデルで評価

```bash
# Ollamaで評価
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model qwen2.5:14b

# または Transformersで評価
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type transformers \
  --model <モデルパス>
```

**重要**: 評価結果は標準フォーマット（`evaluation_v1_0.json`）で出力してください。`overall`と`negative_by_error_type`の数値だけでも十分、次の手が決まります。

**注意**: `evaluation_v1_0.json`が全指標0.0の場合、評価パイプラインの問題（モデルが呼び出されていない、gold抽出が失敗しているなど）の可能性が高い。`CASTLE_EX_EVALUATION_DEBUG_GUIDE.md`を参照してください。

### Step 2: 評価結果分析

評価結果（`evaluation_v1_0.json`）を分析し、以下の情報を確認：

- **層別精度**: Layer 0-6の精度
- **軸別精度**: logic-only, emotion+logic, 3軸統合の精度
- **error_type別精度**: 各error_typeの検出精度
- **弱点の特定**: 上記6つの評価指標で弱い部分を特定

### Step 3: v1.1データ生成

評価結果に基づいて、v1.1データを生成：

```bash
# 例: 負例検出が弱い場合
python castle_ex/castle_ex_data_generator.py \
  --count 500 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --target-layer2-count 200 \
  --target-error-type-ratio 0.70 \
  --output castle_ex_dataset_v1_1.jsonl
```

---

## 🎯 典型的な弱点と処方箋

### ケースA: 負例検出が弱い

**症状**: Negative Detection < 80%

**処方箋**:
- error_typeごとに hard negative を負例の7%まで上げる（増やしすぎ注意）
- Layer 5の負例テンプレートを増やす

**コマンド例**:
```bash
# hard negativeを増やす（Layer 6に集中）
python castle_ex/castle_ex_data_generator.py \
  --count 300 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --output castle_ex_dataset_v1_1.jsonl
```

---

### ケースB: 文脈感度が弱い

**症状**: Context Sensitivity < 75%

**処方箋**:
- Layer 4とLayer 6で「同じ発話×違う状況」の対比データを追加
- 文脈スロット（`{place}`, `{situation}`, `{time}`）のバリエーションを増やす

**コマンド例**:
```bash
# Layer 4/6の文脈データを追加
python castle_ex/castle_ex_data_generator.py \
  --count 400 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

---

### ケースC: 空気読めない（emotion mismatch増える）

**症状**: Emotion Appropriateness < 80%

**処方箋**:
- Layer 3を追加しつつ、Layer 6で「共感→状況確認→次の一手」型を増やす
- emotion_mismatchの負例を増やす

**コマンド例**:
```bash
# Layer 3/6の感情データを追加
python castle_ex/castle_ex_data_generator.py \
  --count 350 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

---

## 📝 学習ログと評価結果の提出

学習を実行したら、以下を提出してください：

1. **学習ログ**: 各epochのloss、accuracy
2. **評価結果**: `evaluation_v1_0.json`（層別/軸別の内訳を含む）
3. **統計比較**: v1.0 vs v1.1の統計比較

これらがあれば、次のv1.1データ生成の具体的な指示（どのテンプレを何件増やすか）を数値で出します。

**重要**: `evaluation_v1_0.json`が共有できなくてもOK。`overall`と`negative_by_error_type`の数値だけでも十分、次の手が決まります。

---

## 📋 評価結果フォーマット（標準形）

評価結果は以下の標準フォーマットで出力してください：

```json
{
  "dataset": "castle_ex_dataset_v1_0_eval.jsonl",
  "seed": "castle_ex_v1_0",
  "overall": {
    "negative_detection": 0.00,
    "axis_consistency": 0.00,
    "context_sensitivity": 0.00,
    "emotion_appropriateness": 0.00,
    "paraphrase_robustness": 0.00,
    "causal_validity": 0.00
  },
  "by_layer": {
    "0": {"acc": 0.00},
    "1": {"acc": 0.00},
    "2": {"acc": 0.00},
    "3": {"acc": 0.00},
    "4": {"acc": 0.00},
    "5": {"acc": 0.00},
    "6": {"acc": 0.00}
  },
  "by_axes_combo": {
    "logic": {"acc": 0.00},
    "emotion": {"acc": 0.00},
    "context": {"acc": 0.00},
    "emotion,logic": {"acc": 0.00},
    "context,logic": {"acc": 0.00},
    "context,emotion,logic": {"acc": 0.00}
  },
  "negative_by_error_type": {
    "logic_error": {"precision": 0.00, "recall": 0.00},
    "missing_reason": {"precision": 0.00, "recall": 0.00},
    "emotion_mismatch": {"precision": 0.00, "recall": 0.00},
    "context_miss": {"precision": 0.00, "recall": 0.00},
    "overconfident": {"precision": 0.00, "recall": 0.00},
    "unsafe_action": {"precision": 0.00, "recall": 0.00}
  }
}
```

### 評価フォーマット生成

標準フォーマットのテンプレートを生成：

```bash
python castle_ex/castle_ex_evaluation_formatter.py \
  --dataset castle_ex_dataset_v1_0_eval.jsonl \
  --seed castle_ex_v1_0 \
  --output evaluation_v1_0.json
```

---

## 🎯 v1.1データ生成の指示出しルール（固定）

評価結果を見た瞬間に数値が出せるように、ルールを決め打ち。

### 基本ルール

- **スコアが弱い指標に直撃するLayer/axes/error_typeを増やす**
- 追加は基本 **+15%（約500件）** から開始
- ただし、特定error_typeが弱いなら **そのtypeだけ+100〜200件** 追加

### 具体的な指示例

#### ケース1: Negative Detection が低い（< 80%）

**指示**:
- hard negative +60件（L6中心）
- Layer 5の負例テンプレートを増やす

**コマンド例**:
```bash
python castle_ex/castle_ex_data_generator.py \
  --count 300 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --output castle_ex_dataset_v1_1.jsonl
```

#### ケース2: Context Sensitivity が低い（< 75%）

**指示**:
- Layer 4 +150件
- Layer 6の文脈対比 +200件

**コマンド例**:
```bash
python castle_ex/castle_ex_data_generator.py \
  --count 400 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

#### ケース3: Emotion Appropriateness が低い（< 80%）

**指示**:
- emotion_mismatch負例 +120件
- Layer 3 +100件

**コマンド例**:
```bash
python castle_ex/castle_ex_data_generator.py \
  --count 350 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

#### ケース4: 特定error_typeが弱い（precision/recall < 70%）

**指示**:
- 該当error_typeだけ +100〜200件追加
- スロットテンプレートでバリエーションを増やす

**コマンド例**:
```bash
python castle_ex/castle_ex_data_generator.py \
  --count 200 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-error-type-ratio 0.70 \
  --output castle_ex_dataset_v1_1.jsonl
```

---

## 🚀 次のステップ（チェックリスト）

1. ✅ **データセット固定**: `castle_ex_dataset_v1_0.jsonl`
2. ✅ **train/eval分割**: ハッシュベース固定分割完了
3. ✅ **学習スケジュール生成**: `castle_ex_schedule_v1_0.json`生成完了
4. ⏳ **学習実行**: 外部トレーナーで実行（`castle_ex_schedule_v1_0.json`を参照）
5. ⏳ **評価実行**: `castle_ex_evaluator.py`で実行して`evaluation_v1_0.json`を出力
6. ⏳ **評価結果分析**: 弱点を特定（`overall`と`negative_by_error_type`を確認）
7. ⏳ **v1.1データ生成**: 評価結果に基づいて追加生成（指示出しルールに従う）

---

## ✅ 学習前チェックリスト

- [ ] データセット固定完了（`castle_ex_dataset_v1_0.jsonl`）
- [ ] train/eval分割完了（`castle_ex_dataset_v1_0_train.jsonl`, `castle_ex_dataset_v1_0_eval.jsonl`）
- [ ] 学習スケジュール生成完了（`castle_ex_schedule_v1_0.json`）
- [ ] データ検証完了（`castle_ex_data_validator.py`）
- [ ] 統計情報確認完了（`castle_ex_stats_viewer.py`）

---

## ✅ 学習実行チェックリスト

- [ ] 学習スケジュール（`castle_ex_schedule_v1_0.json`）を読み込み
- [ ] 各epochの`layer_weights`と`negative_ratio`を適用
- [ ] train loss（epochごと）をログに記録
- [ ] eval loss（epochごと）をログに記録
- [ ] eval metrics（6指標のスコア）をログに記録
- [ ] （推奨）confusion matrix（error_type別の負例検出精度）を記録
- [ ] （推奨）layer別 accuracyを記録
- [ ] （推奨）axes組み合わせ別 accuracy（logic-only / 3軸など）を記録

---

## ✅ 評価実行チェックリスト

- [ ] **デバッグモードで動作確認**（`--max-samples 5`）
  - [ ] `debug_samples`に5件のサンプルが記録されている
  - [ ] `gold_answer`が正しく抽出されている（空でない）
  - [ ] `pred_answer`が記録されている
  - [ ] `pred_empty`が全て`false`である
- [ ] **実際のモデルを接続**（`--model-type ollama`または`transformers`）
- [ ] 評価データ（`castle_ex_dataset_v1_0_eval.jsonl`）を読み込み
- [ ] 評価を実行して`evaluation_v1_0.json`を出力
- [ ] `overall`（6指標）を記録（0.0以外の値になっているか確認）
- [ ] `by_layer`（Layer 0-6の精度）を記録（0.0以外の値になっているか確認）
- [ ] `by_axes_combo`（軸組み合わせ別精度）を記録
- [ ] `negative_by_error_type`（error_type別のprecision/recall）を記録
- [ ] （推奨）評価結果を分析して弱点を特定

**重要**: 全指標が0.0の場合、`CASTLE_EX_EVALUATION_DEBUG_GUIDE.md`と`CASTLE_EX_EVALUATION_SETUP.md`を参照してください。

---

## 📚 参考資料

- `CASTLE_EX_README.md`: フレームワーク概要
- `CASTLE_EX_COMPLETE_GUIDE.md`: 完全ガイド
- `CASTLE_EX_V1_1_GENERATION_RULES.md`: v1.1データ生成ルール（固定版）
- `castle_ex_dataset_v1_0_stats.json`: v1.0統計情報
- `castle_ex_schedule_v1_0.json`: 学習スケジュール（25epoch）
- `evaluation_v1_0.json`: 評価結果フォーマット（テンプレート）

---

## 📋 生成されたファイル一覧

### データセット
- `castle_ex_dataset_v1_0.jsonl`: 固定版データセット（3409件）
- `castle_ex_dataset_v1_0_stats.json`: 統計情報
- `castle_ex_dataset_v1_0_train.jsonl`: 訓練データ（3055件, 89.6%）
- `castle_ex_dataset_v1_0_eval.jsonl`: 評価データ（354件, 10.4%）

### 学習スケジュール
- `castle_ex_schedule_v1_0.json`: 学習スケジュール（25epoch、Phase 1-3）

### 評価フォーマット
- `evaluation_v1_0.json`: 評価結果フォーマット（テンプレート）

### ツール
- `castle_ex_learning_prep.py`: 学習準備スクリプト（一括実行）
- `castle_ex_dataset_splitter.py`: データセット分割ツール（ハッシュベース固定分割）
- `castle_ex_schedule_generator.py`: 学習スケジュール生成ツール
- `castle_ex_evaluation_formatter.py`: 評価フォーマット生成ツール

