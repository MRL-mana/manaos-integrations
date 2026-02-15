# CASTLE-EX 評価セットアップガイド

## 🚨 重要：評価が0点になる原因

`evaluation_v1_0.json`が全指標0.0の場合、**データの問題ではなく、評価パイプラインの問題**の可能性が高い。

---

## ✅ 修正済みevaluatorの確認

`castle_ex_evaluator_fixed.py`では以下を修正済み：

1. **Gold answer抽出**: `messages`の最後の`assistant`メッセージを正しく抽出
2. **User prompt抽出**: `assistant`を除いた`messages`を正しく抽出
3. **デバッグ出力**: 最初の5サンプルの`gold_answer`と`pred_answer`を記録
4. **標準フォーマット出力**: `evaluation_v1_0.json`形式で出力

---

## 🔧 評価実行手順

### Step 1: デバッグモードで動作確認

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
- `pred_answer`が記録されている（ダミーの場合は"ダミー予測: ..."）
- `pred_empty`が全て`false`である

---

### Step 2: 実際のモデルを接続

#### オプションA: Ollamaを使用

```bash
# Ollamaで評価（モデル名を指定）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model qwen2.5:14b \
  --ollama-url http://127.0.0.1:11434/api/generate
```

**前提条件**:
- Ollamaが起動している（`http://127.0.0.1:11434`）
- 指定したモデルがダウンロード済み

---

#### オプションB: Transformersを使用

```bash
# Transformersで評価（モデルパスを指定）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type transformers \
  --model microsoft/DialoGPT-medium
```

**前提条件**:
- `transformers`ライブラリがインストール済み
- 指定したモデルがダウンロード可能（またはローカルに存在）

---

#### オプションC: 外部トレーナーのチェックポイントを使用

外部トレーナー（例: Axolotl、LLaMA-Factoryなど）のチェックポイントを使用する場合、`castle_ex_evaluator_fixed.py`の`main()`関数を修正：

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

### Step 3: 全件評価実行

```bash
# 全件評価（--max-samplesを外す）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type ollama \
  --model qwen2.5:14b
```

---

## 📊 評価結果の確認

### 正常な場合

```json
{
  "overall": {
    "negative_detection": 0.85,  // ← 0.0以外の値
    "axis_consistency": 0.88,
    ...
  },
  "by_layer": {
    "0": {"acc": 0.92},  // ← 0.0以外の値
    "1": {"acc": 0.88},
    ...
  },
  "debug_samples": [
    {
      "gold_answer": "対話が15分継続し...",
      "pred_answer": "対話が15分継続し...",  // ← モデルの実際の予測
      "pred_empty": false  // ← falseであること
    }
  ]
}
```

### 問題がある場合

```json
{
  "overall": {
    "negative_detection": 0.0,  // ← 全部0.0
    ...
  },
  "debug_samples": [
    {
      "gold_answer": "対話が15分継続し...",
      "pred_answer": "",  // ← 空文字列
      "pred_empty": true  // ← trueならモデル呼び出しに問題
    }
  ]
}
```

---

## 🎯 よくある問題と対処法

### 問題1: `pred_answer`が常に空

**原因**: モデル呼び出しが失敗している

**対処**:
1. Ollamaが起動しているか確認: `curl http://127.0.0.1:11434/api/tags`
2. モデル名が正しいか確認: `ollama list`
3. ネットワークエラーがないか確認（タイムアウト設定を確認）

---

### 問題2: `gold_answer`が空

**原因**: データセットの`messages`形式が想定と異なる

**対処**:
1. データセットの1件を確認:
   ```python
   import json
   with open('castle_ex_dataset_v1_0_eval.jsonl', 'r') as f:
       item = json.loads(f.readline())
       print(item.get("messages", []))
   ```
2. `messages`の最後に`assistant`ロールがあるか確認

---

### 問題3: 全指標が0.0（モデルは動作している）

**原因**: 評価ロジック（`evaluate_response()`）が厳しすぎる

**対処**:
1. `debug_samples`の`gold_answer`と`pred_answer`を比較
2. 部分一致の閾値（現在0.5）を調整
3. 評価ロジックを改善（BLEU、ROUGEなどのメトリクスを使用）

---

## 📝 次のステップ

1. ✅ **デバッグモードで動作確認**: `--max-samples 5`
2. ✅ **実際のモデルを接続**: `--model-type ollama`または`transformers`
3. ✅ **全件評価実行**: `--max-samples`を外す
4. ✅ **評価結果を分析**: `evaluation_v1_0.json`を確認
5. ✅ **v1.1データ生成**: `CASTLE_EX_V1_1_GENERATION_RULES.md`に従う

---

## 🔗 関連ファイル

- `castle_ex_evaluator_fixed.py`: 修正済みevaluator
- `CASTLE_EX_EVALUATION_DEBUG_GUIDE.md`: デバッグガイド
- `evaluation_v1_0.json`: 評価結果フォーマット（テンプレート）
- `castle_ex_dataset_v1_0_eval.jsonl`: 評価データセット
