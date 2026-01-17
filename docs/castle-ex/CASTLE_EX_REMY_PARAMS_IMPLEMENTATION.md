# CASTLE-EX レミ先輩推奨パラメータ実装完了

## 実装完了したパラメータ

### 1. Layer配分（レミ先輩推奨）
- L0: 8%
- L1: 16%
- L2: 8%
- L3: 12%
- L4: 12%
- L5: 22%
- L6: 22%

### 2. 負例率
- positive: 70%
- negative: 30%

### 3. error_type配分（負例内）
- logic_error: 18.3%
- missing_reason: 15%
- emotion_mismatch: 15%
- context_miss: 18.3%
- overconfident: 15%
- unsafe_action: 18.3%（少し厚く）

### 4. hard negative配分
- 負例の5%（全体の1.5%）
- Layer 6: 80%
- Layer 5: 20%
- error_type配分: unsafe_action:40%, context_miss:30%, overconfident:30%

### 5. axis_evidence必須化ルール
- L5/L6: 100%（必須）
- L3/L4: 80%（必須）
- L0-L2: 任意（0-30%でOK）

### 6. 目標件数に達するまで生成を回す
- `--target-unique` オプションで目標ユニーク数を指定
- 最大10回までリトライ
- reject統計を `*_reject_stats.json` に出力

## 現在の問題点

### 重複率が95%と非常に高い
- 原因: テンプレートのバリエーション不足
- 対策: 各層のテンプレートを増やす必要がある

### 目標ユニーク数に到達できない
- 現在: 98件（目標: 1500件）
- 原因: テンプレートが少ないため、同じテンプレートから生成されたデータが重複として除去されている

## 次のステップ

1. **テンプレートのバリエーションを増やす**
   - Layer 0-2: 3-5倍に増やす
   - Layer 3-4: 2-3倍に増やす
   - Layer 5: 負例テンプレートを各error_typeに5-10個追加
   - Layer 6: 3軸統合テンプレートを10-20個に増やす

2. **reject_stats.jsonを分析**
   - どの層でrejectが多いかを特定
   - テンプレート不足の層を優先的に補強

3. **axes配分の実装**
   - 現在はlayer配分のみ実装
   - axes配分（logic:28%, emotion:10%, context:10%, emotion+logic:12%, context+logic:12%, 3軸:28%）の実装が必要

## 実装済み機能

- ✅ Layer配分（レミ先輩推奨）
- ✅ 負例率30%
- ✅ error_type配分（均等化、unsafe_actionを少し厚く）
- ✅ hard negative配分（L6:80%, L5:20%）
- ✅ axis_evidence必須化ルール（L5/L6:100%, L3/L4:80%）
- ✅ 目標件数に達するまで生成を回すループ
- ✅ reject統計の出力

## 未実装機能

- ⚠️ axes配分の制御（現在はlayer配分のみ）
- ⚠️ テンプレートのバリエーション増加（手動で追加が必要）
