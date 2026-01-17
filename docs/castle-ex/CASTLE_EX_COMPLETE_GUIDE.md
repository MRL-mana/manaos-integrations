# CASTLE-EXフレームワーク 完全ガイド

## 実戦での使い方（ステップバイステップ）

### Step 1: データ生成と品質チェック

```bash
# データ生成（1000件）
python castle_ex/castle_ex_data_generator.py --count 1000 --output my_dataset.jsonl

# 自動生成される stats.json を確認
cat my_dataset_stats.json
```

**確認ポイント:**
- `layer_error_type_cross`: 特定のlayerにerror_typeが集中していないか
- `axes_avg_token_length`: 回答が短すぎる/長すぎる組み合わせがないか
- `duplicate_count`: 重複が10%以下か

### Step 2: データ分布レポート分析

```bash
python castle_ex/castle_ex_stats_viewer.py my_dataset_stats.json
```

**出力から確認すべきこと:**
1. **logic-only偏り**: 45%以下が理想
2. **error_type分布**: 均等性（最小/最大 > 0.5）
3. **重複メッセージ**: 10%以下
4. **axis_evidenceカバレッジ**: Layer 3+で30%以上

### Step 3: データ検証

```bash
python castle_ex/castle_ex_data_validator.py my_dataset.jsonl
```

**確認ポイント:**
- すべてのデータが有効か
- axis_evidenceの警告（Layer 3+で推奨）
- 重複メッセージの警告

### Step 4: 学習スケジュール生成

```bash
python castle_ex/castle_ex_training_pipeline.py my_dataset.jsonl --start-epoch 1 --end-epoch 25
```

**生成されるもの:**
- `training_schedule.json`: 全エポックのスケジュール
- `epoch_001.jsonl` ~ `epoch_025.jsonl`: エポック別データ

### Step 5: 学習実行（外部ツール使用）

生成された `epoch_*.jsonl` を学習フレームワーク（Axolotl、LLaMA-Factoryなど）で使用。

### Step 6: 評価

```bash
python castle_ex/castle_ex_evaluator.py --output evaluation.json
```

**確認すべき指標:**
- `paraphrase_robustness`: 0.85以上が理想
- `semantic_consistency`: 0.90以上が理想
- `negative_detection`: 0.80以上が理想

## よくある問題と解決策

### 問題1: logic-only偏りが高い（>50%）

**原因**: Layer 0-2のデータが多すぎる

**解決策:**
- Layer 5-6のデータを増やす
- 3軸統合（context,emotion,logic）のデータを追加

### 問題2: error_type分布が偏っている

**原因**: 特定のerror_typeのテンプレートが少ない

**解決策:**
- `castle_ex_data_generator.py`の`emotional_causal_negative`にテンプレートを追加
- 各error_typeに最低3-5個のテンプレートを用意

### 問題3: 重複メッセージが多い（>10%）

**原因**: データ生成のテンプレートが少ない

**解決策:**
- 各層のテンプレートを増やす
- バリエーション生成ロジックを追加

### 問題4: axis_evidenceカバレッジが低い（<30%）

**原因**: Layer 3+のデータにaxis_evidenceが不足

**解決策:**
- Layer 5のテンプレートに`axis_evidence`を追加
- validatorの警告に従って修正

## ManaOS向け最適化

### 推奨設定

```bash
# データ生成（ManaOS向け）
python castle_ex/castle_ex_data_generator.py --count 2000 --output manaos_dataset.jsonl

# 分析
python castle_ex/castle_ex_stats_viewer.py manaos_dataset_stats.json
```

### ManaOS向けの重要ポイント

1. **Layer 6に秘書タスクを追加**
   - 作業管理、クレーム対応、日報処理

2. **unsafe_actionエラータイプを重視**
   - ガソスタ現場での危険な提案を避ける

3. **Paraphrase Robustnessを高める**
   - 同じ内容を異なる表現で言われても理解できる

4. **Contextは現場文脈**
   - ガソスタ業務、シフト管理、作業漏れ防止

## データ品質チェックリスト

- [ ] logic-only偏り < 50%
- [ ] error_type分布が均等（最小/最大 > 0.5）
- [ ] 重複メッセージ < 10%
- [ ] axis_evidenceカバレッジ > 30%（Layer 3+）
- [ ] 各layerの比率が理想値の±20%以内
- [ ] 3軸統合（context,emotion,logic）が20%以上
- [ ] hard negativeが負例の5%程度

## 次のステップ

1. **実際に学習を実行**
   - 生成されたepoch_*.jsonlを使用
   - 学習フレームワークに投入

2. **評価を実行**
   - `castle_ex_evaluator.py`で評価
   - 特に`paraphrase_robustness`を重視

3. **改善ループ**
   - 評価結果から問題点を特定
   - stats_viewerで偏りを確認
   - データ生成を調整
   - 再学習

## 参考

- [CASTLE-EX設計図](https://note.com/jazzy_dill8804/n/n940b754772cd)
- `CASTLE_EX_README.md`: 基本ドキュメント
- `castle_ex_stats_viewer.py`: 偏り分析ツール
