# CASTLE-EX v1.1データ生成ルール（固定版）

評価結果を見た瞬間に数値が出せるように、ルールを決め打ち。

---

## 📋 基本ルール

- **スコアが弱い指標に直撃するLayer/axes/error_typeを増やす**
- 追加は基本 **+15%（約500件）** から開始
- ただし、特定error_typeが弱いなら **そのtypeだけ+100〜200件** 追加

---

## 🎯 評価指標別の指示出しルール

### 1. Negative Detection（負例検出）が低い（< 80%）

**症状**: 
- `overall.negative_detection < 0.80`
- または`negative_by_error_type`のprecision/recallが全体的に低い

**処方箋**:
- hard negative +60件（L6中心）
- Layer 5の負例テンプレートを増やす
- 弱いerror_typeだけ +100〜200件追加

**コマンド例**:
```bash
# hard negativeを増やす（Layer 6に集中）
python castle_ex/castle_ex_data_generator.py \
  --count 300 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `negative_detection = 0.75` → hard negative +60件、弱いerror_type +150件
- `negative_detection = 0.70` → hard negative +80件、弱いerror_type +200件

---

### 2. Context Sensitivity（文脈感度）が低い（< 75%）

**症状**: 
- `overall.context_sensitivity < 0.75`
- または`by_axes_combo.context`や`by_axes_combo.context,logic`の精度が低い

**処方箋**:
- Layer 4 +150件
- Layer 6の文脈対比 +200件
- 文脈スロット（`{place}`, `{situation}`, `{time}`）のバリエーションを増やす

**コマンド例**:
```bash
# Layer 4/6の文脈データを追加
python castle_ex/castle_ex_data_generator.py \
  --count 400 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `context_sensitivity = 0.70` → Layer 4 +150件、Layer 6 +200件
- `context_sensitivity = 0.65` → Layer 4 +200件、Layer 6 +250件

---

### 3. Emotion Appropriateness（感情適切性）が低い（< 80%）

**症状**: 
- `overall.emotion_appropriateness < 0.80`
- または`by_axes_combo.emotion`や`by_axes_combo.emotion,logic`の精度が低い
- または`negative_by_error_type.emotion_mismatch`のprecision/recallが低い

**処方箋**:
- emotion_mismatch負例 +120件
- Layer 3 +100件
- Layer 6で「共感→状況確認→次の一手」型を増やす

**コマンド例**:
```bash
# Layer 3/6の感情データを追加
python castle_ex/castle_ex_data_generator.py \
  --count 350 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `emotion_appropriateness = 0.75` → emotion_mismatch +120件、Layer 3 +100件
- `emotion_appropriateness = 0.70` → emotion_mismatch +150件、Layer 3 +150件

---

### 4. Axis Consistency（軸の一貫性）が低い（< 85%）

**症状**: 
- `overall.axis_consistency > 0.15`（矛盾率が高い）
- または`by_axes_combo`の精度がバラついている

**処方箋**:
- Layer 3/4の`axis_evidence`を強化
- 軸の組み合わせデータを追加
- 特に3軸統合（`context,emotion,logic`）を増やす

**コマンド例**:
```bash
# 軸の組み合わせデータを追加
python castle_ex/castle_ex_data_generator.py \
  --count 300 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `axis_consistency = 0.20`（矛盾率20%） → 3軸統合 +200件、Layer 3/4 +100件
- `axis_consistency = 0.25`（矛盾率25%） → 3軸統合 +300件、Layer 3/4 +150件

---

### 5. Paraphrase Robustness（言い換え耐性）が低い（< 90%）

**症状**: 
- `overall.paraphrase_robustness < 0.90`
- または`by_layer.1`（Layer 1）の精度が低い

**処方箋**:
- Layer 1のパラフレーズペアを追加
- スロットテンプレートでバリエーションを増やす

**コマンド例**:
```bash
# Layer 1のパラフレーズデータを追加
python castle_ex/castle_ex_data_generator.py \
  --count 200 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `paraphrase_robustness = 0.85` → Layer 1 +150件
- `paraphrase_robustness = 0.80` → Layer 1 +200件

---

### 6. Causal Validity（因果妥当性）が低い（< 80%）

**症状**: 
- `overall.causal_validity < 0.80`
- または`by_layer.5`（Layer 5）の精度が低い

**処方箋**:
- Layer 5のstate遷移データを追加
- 観測可能な変化（数値、時間、成果）を明確にする

**コマンド例**:
```bash
# Layer 5の因果データを追加
python castle_ex/castle_ex_data_generator.py \
  --count 250 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `causal_validity = 0.75` → Layer 5 +200件
- `causal_validity = 0.70` → Layer 5 +250件

---

### 7. 特定error_typeが弱い（precision/recall < 70%）

**症状**: 
- `negative_by_error_type.<error_type>.precision < 0.70`
- または`negative_by_error_type.<error_type>.recall < 0.70`

**処方箋**:
- 該当error_typeだけ +100〜200件追加
- スロットテンプレートでバリエーションを増やす

**コマンド例**:
```bash
# 特定error_typeを増やす
python castle_ex/castle_ex_data_generator.py \
  --count 200 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-error-type-ratio 0.70 \
  --output castle_ex_dataset_v1_1.jsonl
```

**具体的な数値指示例**:
- `logic_error.precision = 0.65` → logic_error +150件
- `context_miss.recall = 0.60` → context_miss +180件
- `emotion_mismatch.precision = 0.55` → emotion_mismatch +200件

---

## 📊 複合ケース（複数の指標が弱い場合）

### ケースA: Negative Detection + Context Sensitivity が低い

**処方箋**:
- hard negative +60件（L6中心）
- Layer 4 +150件
- Layer 6の文脈対比 +200件

**合計**: 約410件追加

---

### ケースB: Emotion Appropriateness + Axis Consistency が低い

**処方箋**:
- emotion_mismatch負例 +120件
- Layer 3 +100件
- 3軸統合 +200件

**合計**: 約420件追加

---

### ケースC: 全体的に弱い（複数の指標が目標未達）

**処方箋**:
- 基本追加: +500件（+15%）
- 弱い指標に応じて追加: +200〜300件
- 合計: 約700〜800件追加

**コマンド例**:
```bash
# 全体的に弱い場合
python castle_ex/castle_ex_data_generator.py \
  --count 800 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --target-layer2-count 200 \
  --target-error-type-ratio 0.70 \
  --output castle_ex_dataset_v1_1.jsonl
```

---

## 🎯 評価結果から数値指示を出す手順

1. **`overall`を確認**: 6指標のスコアを確認
2. **`negative_by_error_type`を確認**: 弱いerror_typeを特定
3. **`by_layer`を確認**: 弱いLayerを特定
4. **`by_axes_combo`を確認**: 弱い軸組み合わせを特定
5. **上記ルールに従って数値指示を出す**: どのテンプレを何件増やすか

---

## 📝 数値指示の例（実際の出力）

評価結果から以下のような指示を出します：

```
評価結果分析:
- Negative Detection: 0.75（目標: 0.80）→ 弱い
- Context Sensitivity: 0.72（目標: 0.75）→ 弱い
- emotion_mismatch.precision: 0.65（目標: 0.70）→ 弱い

v1.1データ生成指示:
1. hard negative +60件（L6中心）
2. Layer 4 +150件
3. Layer 6の文脈対比 +200件
4. emotion_mismatch負例 +150件

合計: 約560件追加

コマンド:
python castle_ex/castle_ex_data_generator.py \
  --count 560 \
  --existing castle_ex_dataset_v1_0.jsonl \
  --target-negative-ratio 0.30 \
  --target-error-type-ratio 0.70 \
  --output castle_ex_dataset_v1_1.jsonl
```

---

## ✅ チェックリスト

- [ ] 評価結果（`evaluation_v1_0.json`）を確認
- [ ] `overall`の6指標を確認
- [ ] `negative_by_error_type`のprecision/recallを確認
- [ ] `by_layer`の精度を確認
- [ ] `by_axes_combo`の精度を確認
- [ ] 弱い指標を特定
- [ ] 上記ルールに従って数値指示を出す
- [ ] v1.1データを生成
- [ ] v1.1データの統計を確認
- [ ] v1.0とv1.1の統計を比較

