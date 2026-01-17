# CASTLE-EXフレームワーク

推論×感情×文脈の3軸統合学習データ設計フレームワーク

## 概要

CASTLE-EXは、LLMの「真の理解」を目指す学習データ設計フレームワークです。推論（Logic）、感情（Emotion）、文脈（Context）の3軸を最初から統合して学習データを設計します。

### フレームワークの特徴

- **7層階層構造**: 公理層から統合層まで段階的に複雑性を増加
- **3軸統合**: 推論・感情・文脈を同時に学習
- **段階的カリキュラム**: エポックごとに適切な層の配分を自動管理
- **品質保証**: 自動検証機能でデータ品質を保証

## インストール

**必要ライブラリ：なし（Python標準ライブラリのみ）**

```bash
# Python 3.10+ 推奨
python --version
```

追加のパッケージインストールは不要です。

## Quickstart（最小実行例）

```bash
python castle_ex/castle_ex_integrated.py pipeline --count 200 --output-dir ./out
```

**出力例:**
```
out/
  ├── castle_ex_dataset.jsonl           # 生成されたデータセット
  ├── castle_ex_dataset_stats.json      # データ分布レポート（自動生成）
  ├── training/
  │   ├── training_schedule.json        # 学習スケジュール
  │   ├── epoch_001.jsonl               # エポック1用データ
  │   ├── epoch_002.jsonl               # エポック2用データ
  │   └── ...
  └── validation_report.json            # 検証レポート
```

**データ分布レポートの内容:**
- layer別件数・比率
- axes組み合わせの比率（logic-only偏り検知）
- positive/negative比率
- error_type分布（均等性チェック）
- **layer×error_typeクロス集計**（偏り検知が一段上がる）
- **axes組み合わせ×平均トークン長**（短文偏りが見える）
- 平均トークン長
- axis_evidenceカバレッジ
- **重複メッセージ検知**（データ水増し事故を防ぐ）

## 使い方

### 1. 完全パイプライン実行（推奨）

データ生成から学習スケジュール生成まで一括実行:

```bash
python castle_ex/castle_ex_integrated.py pipeline --count 1000 --output-dir ./castle_ex_output
```

### 2. 個別コマンド

#### データ生成

```bash
python castle_ex/castle_ex_integrated.py generate --count 1000 --output dataset.jsonl
```

#### データ検証

```bash
python castle_ex/castle_ex_integrated.py validate --file dataset.jsonl
```

#### 学習スケジュール生成

```bash
python castle_ex/castle_ex_integrated.py schedule --dataset dataset.jsonl --start-epoch 1 --end-epoch 25
```

#### モデル評価

```bash
python castle_ex/castle_ex_integrated.py evaluate --output evaluation.json
```

#### データ分布レポート分析

```bash
python castle_ex/castle_ex_stats_viewer.py dataset_stats.json
```

**出力内容:**
- 偏りチェック（logic-only偏り、error_type分布など）
- 次に増やすべきLayer/axesの推奨
- hard negative配置推奨
- 統計サマリー

## 7層構造

### Layer 0: 公理層（15%）
基本的な同一性・差異の認識

### Layer 1: 操作層（15%）
基本的な変換・演算の習得
- 算術操作、論理操作、集合操作
- **語彙・同義語変換**（新規追加）
  - 「怒る＝イライラする＝腹が立つ」
  - 「嬉しい＝喜ぶ＝幸せ」

### Layer 2: 関係層（15%）
要素間の関係パターン習得
- 順序関係、比較関係、包含関係、類推関係

### Layer 3: 感情基礎層（10%）
感情の認識・分類・基本的遷移

### Layer 4: 文脈基礎層（10%）
文脈の認識と文脈による意味変化の基礎

### Layer 5: 因果層（20%）
3軸を含む因果構造の習得

### Layer 6: 統合層（15%）
複合状況での推論・感情・文脈の同時処理

## 段階的学習スケジュール

エポックごとに以下のフェーズで学習:

- **Phase 1 (エポック1-5)**: Layer 0のみ
- **Phase 2 (エポック6-9)**: Layer 0-2（基盤層）
- **Phase 3 (エポック10-12)**: Layer 0-3（感情基礎追加）
- **Phase 4 (エポック13-15)**: Layer 0-4（文脈基礎追加）
- **Phase 5 (エポック16-20)**: Layer 0-5（因果層統合）
- **Phase 6 (エポック21+)**: Layer 0-6（完全統合）

## ファイル構成

```
castle_ex_data_generator.py      # データ生成ツール
castle_ex_data_validator.py      # データ検証ツール
castle_ex_training_pipeline.py   # 学習パイプライン
castle_ex_evaluator.py           # 評価ツール
castle_ex_stats_viewer.py        # データ分布レポート可視化ツール
castle_ex_integrated.py          # 統合実行スクリプト
```

## データ形式

### 拡張JSONL形式（CASTLE-EX仕様）

CASTLE-EXでは、各データに以下のメタデータを含めます：

- **layer**: 層番号（0-6）
- **axes**: 使用されている軸（`logic`, `emotion`, `context`）
- **positive**: `true`=正例、`false`=負例
- **axis_evidence**: 各軸の判定可能な根拠（Layer 3+で推奨）
- **state0**, **action**, **state1**: 因果タプル形式（Layer 5+で使用）
- **error_type**: 負例の場合のエラータイプ

### データ分布レポート

データ生成時に `{filename}_stats.json` が自動生成されます：

- layer別件数・比率
- axes組み合わせの比率（logic-only偏り検知）
- positive/negative比率
- error_type分布
- 平均トークン長
- axis_evidenceカバレッジ

これにより「学習が崩れた原因」を秒で特定できます。

各行が1つの学習データ。3軸統合のメタデータを含む:

#### Layer 0-2（基礎層）の例

```json
{
  "layer": 0,
  "axes": ["logic"],
  "positive": true,
  "messages": [
    {"role": "user", "content": "A = A ?"},
    {"role": "assistant", "content": "同じ。"}
  ]
}
```

#### Layer 5（因果層・3軸統合）の例

```json
{
  "layer": 5,
  "axes": ["logic", "emotion", "context"],
  "positive": true,
  "state0": {"context": "試験前日", "emotion": "不安"},
  "action": "頻出問題に絞って復習",
  "state1": {"context": "模試の正答率 +15%", "emotion": "安心"},
  "axis_evidence": {
    "logic": ["原因→結果の説明が必要", "復習→正答率向上の因果"],
    "emotion": ["不安→励まし/共感が必要", "感情が不安から安心に遷移"],
    "context": ["試験という状況での優先順位"]
  },
  "messages": [
    {"role": "user", "content": "明日試験だけど不安。何を優先すべき？"},
    {"role": "assistant", "content": "不安があるのは自然。今は頻出問題に絞って復習すると効率的です。模試で正答率が15%向上すれば自信につながります。"}
  ]
}
```

**ポイント**: 
- `state1`は観測可能な変化（「正答率 +15%」）にしています。これにより「世界が動いた」感のある学習が可能です。
- `axis_evidence`で各軸の判定可能な根拠を明示しています。

#### 負例（negative）の例

```json
{
  "layer": 5,
  "axes": ["logic", "emotion"],
  "positive": false,
  "error_type": "emotion_mismatch",
  "state0": {"context": "試験に落ちた", "emotion": "悲しい"},
  "action": "反応",
  "state1": {"context": "誤った反応", "emotion": "無視"},
  "axis_evidence": {
    "logic": ["原因→結果の説明が必要"],
    "emotion": ["悲しい→励まし/共感が必要（しかし誤った反応）"]
  },
  "messages": [
    {"role": "user", "content": "試験に落ちて悲しい"},
    {"role": "assistant", "content": "それは嬉しいね！次も頑張ろう！"}
  ]
}
```

**error_typeの最小セット（6個）**:
- `logic_error`: 結論が間違い
- `missing_reason`: 理由なし
- `emotion_mismatch`: 空気読めない
- `context_miss`: 状況無視
- `overconfident`: 根拠ない断定
- `unsafe_action`: 危険な提案（秘書運用に効く）

負例は各error_typeが均等に分布するよう自動調整されます。

### データ構造の説明

- `layer`: 層番号（0-6）
- `axes`: 使用されている軸（`logic`, `emotion`, `context`）
- `positive`: `true`=正例、`false`=負例
- `state0`, `action`, `state1`: 因果タプル形式（Layer 3+で使用）
- `error_type`: 負例の場合のエラータイプ（`emotion_mismatch`, `context_ignored`, `logic_error`など）

## 層別サンプルデータ

### Layer 0: 公理層
```json
{"layer": 0, "axes": ["logic"], "positive": true, "messages": [{"role": "user", "content": "A = A ?"}, {"role": "assistant", "content": "同じ。"}]}
```

### Layer 1: 操作層（語彙変換含む）
```json
{"layer": 1, "axes": ["logic"], "positive": true, "messages": [{"role": "user", "content": "怒る = イライラする ?"}, {"role": "assistant", "content": "はい。同じ意味です。"}]}
```

### Layer 2: 関係層
```json
{"layer": 2, "axes": ["logic"], "positive": true, "messages": [{"role": "user", "content": "A > B, B > C → A と C は？"}, {"role": "assistant", "content": "A > C。推移律。"}]}
```

### Layer 3: 感情基礎層
```json
{"layer": 3, "axes": ["emotion"], "positive": true, "messages": [{"role": "user", "content": "😊 → 感情は？"}, {"role": "assistant", "content": "喜び・幸福。ポジティブな感情状態。"}]}
```

### Layer 4: 文脈基礎層
```json
{"layer": 4, "axes": ["context"], "positive": true, "messages": [{"role": "user", "content": "「バカだな」(親友から) → 意味は？"}, {"role": "assistant", "content": "親愛表現。ポジティブな意味。関係性が解釈を決める。"}]}
```

### Layer 5: 因果層（3軸統合）
```json
{"layer": 5, "axes": ["logic", "emotion", "context"], "positive": true, "state0": {"emotion": "怒り"}, "action": "冷静に聞く", "state1": {"emotion": "安心"}, "messages": [{"role": "user", "content": "批判された(怒り) → 冷静に聞く → ?"}, {"role": "assistant", "content": "建設的な対話(安心/理解)。感情調整により良い結果。"}]}
```

### Layer 6: 統合層
```json
{"layer": 6, "axes": ["logic", "emotion", "context"], "positive": true, "messages": [{"role": "user", "content": "部下が期限ギリギリに提出(普段は早い)、ミスが多い、最近元気がない → 分析と対応は？"}, {"role": "assistant", "content": "パフォーマンス低下の背景に個人的問題の可能性。仕事の指摘より先に体調や状況を確認。サポートを申し出る。"}]}
```

## 評価指標

### 基本評価

- **層別評価**: 各層での正確率・平均スコア
- **軸別評価**: 推論・感情・文脈各軸でのスコア
- **統合評価**: 3軸統合の検出率

### CASTLE-EX統合評価指標

- **Axis Consistency（軸一貫性）**: 感情/文脈/論理の矛盾率（低いほど良い）
- **Causal Validity（因果妥当性）**: state遷移が自然か（0-1スコア）
- **Emotion Appropriateness（感情適切性）**: 相手の感情に合った返答か（0-1スコア）
- **Context Sensitivity（文脈感度）**: 同じ質問でも文脈で返答が変わるか（0-1スコア）
- **Negative Detection（負例検出）**: 負例を正しく「不適切」と判定できるか
- **Paraphrase Robustness（言い換え耐性）**: 同義・言い換えで回答の品質が落ちない率
- **Semantic Consistency（意味的一貫性）**: 表現が違っても結論が同じ率

**実戦での重要度**: Paraphrase Robustnessは秘書AI運用で最も重要。同じ内容を異なる表現で言われても正しく理解できるか。

### 評価例

```bash
python castle_ex/castle_ex_evaluator.py --output evaluation.json
```

出力例:
```json
{
  "layer_scores": {
    "0": {"accuracy": 0.95, "average_score": 0.98},
    "5": {"accuracy": 0.85, "average_score": 0.87}
  },
  "axis_scores": {
    "logic": {"average": 0.90, "count": 150},
    "emotion": {"average": 0.82, "count": 100},
    "context": {"average": 0.85, "count": 120},
    "integrated": {"average": 0.88, "count": 80}
  },
  "integration_metrics": {
    "axis_consistency": 0.12,
    "causal_validity": 0.89,
    "emotion_appropriateness": 0.85,
    "context_sensitivity": 0.87
  }
}
```

## ManaOS向け拡張（オプション）

CASTLE-EXをManaOS向けに拡張する場合、Layer 6（統合層）で以下のタスクを学習できます：

### 秘書タスクの学習

- **報告書スキャン→要点抽出→タスク化**
- **作業が詰まったときの感情ケア + 具体案**
- **Contextは"現場"文脈（ガソスタ業務）**
  - クレーム対応
  - シフト混雑
  - 作業漏れ防止

これにより、ローカルLLMが**リアル秘書**として機能するようになります。

### 拡張例

```json
{
  "layer": 6,
  "axes": ["logic", "emotion", "context"],
  "positive": true,
  "state0": {"context": "作業が詰まっている", "emotion": "焦り"},
  "action": "優先順位を整理し、感情ケアを提供",
  "state1": {"context": "タスクが整理された、優先順位が明確", "emotion": "安心"},
  "axis_evidence": {
    "logic": ["原因→結果の説明が必要", "整理→効率化の因果"],
    "emotion": ["焦り→感情ケアが必要", "感情が焦りから安心に遷移"],
    "context": ["作業が詰まっているという状況での判断"]
  },
  "messages": [
    {"role": "user", "content": "作業が詰まって焦ってる。どうすればいい？"},
    {"role": "assistant", "content": "焦る気持ちはわかります。まず優先順位を整理しましょう。緊急度と重要度で分類すると効率的です。"}
  ]
}
```

### ManaOS向けタスク例

#### クレーム対応

```json
{
  "layer": 6,
  "axes": ["logic", "emotion", "context"],
  "positive": true,
  "state0": {"context": "クレーム対応中、客が激怒", "emotion": "困惑"},
  "action": "感情を受け止め、冷静に解決策を提示",
  "state1": {"context": "クレームが解決、関係が修復", "emotion": "安心"},
  "axis_evidence": {
    "logic": ["原因→結果の説明が必要", "適切な対応→解決の因果"],
    "emotion": ["困惑→感情調整が必要", "感情が困惑から安心に遷移"],
    "context": ["クレーム対応という状況での判断"]
  },
  "messages": [
    {"role": "user", "content": "クレーム対応中、客が激怒している。どう対応すべき？"},
    {"role": "assistant", "content": "まずはお客様の気持ちを受け止めます。その後、具体的な解決策を提示しましょう。感情的にならず、冷静に対応することが重要です。"}
  ]
}
```

**ManaOS向けの重要ポイント**:
- `unsafe_action`エラータイプで「火気」「危険物」「クレーム煽り」などの地雷を避ける
- 現場文脈（ガソスタ業務）を意識したstate遷移
- 観測可能な変化（「クレームが解決」「タスクが整理された」）を明示

## 参考資料

- [CASTLE-EX設計図](https://note.com/jazzy_dill8804/n/n940b754772cd)
- CASTLEフレームワーク（基盤）
- LEWM論文（感情学習）

## ライセンス

MIT License

