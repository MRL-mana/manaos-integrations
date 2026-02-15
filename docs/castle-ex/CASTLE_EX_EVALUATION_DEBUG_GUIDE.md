# CASTLE-EX 評価デバッグガイド

## 🚨 重要：評価が0点になる原因と対処法

`evaluation_v1_0.json`が全指標0.0の場合、**データの問題ではなく、評価パイプラインの問題**の可能性が高い。

---

## 📋 原因切り分け（5分で確定）

### Step 1: デバッグモードで評価実行

```bash
# 最初の5サンプルだけ評価（デバッグ用）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0_debug.json \
  --max-samples 5 \
  --model-type dummy
```

**確認ポイント**:
- `debug_samples`に`pred_answer`が空でないか
- `gold_answer`が正しく抽出されているか
- `pred_empty`が`true`になっていないか

---

### Step 2: Gold Answer抽出の確認

**問題**: evaluatorが`messages`から正解を正しく抽出できていない

**確認方法**:
```python
# 評価データの1件を確認
import json
with open('castle_ex_dataset_v1_0_eval.jsonl', 'r', encoding='utf-8') as f:
    item = json.loads(f.readline())
    messages = item.get("messages", [])
    # 最後のassistantメッセージが正解
    gold = next((msg["content"] for msg in reversed(messages) if msg.get("role") == "assistant"), None)
    print(f"Gold: {gold}")
```

**修正済み**: `castle_ex_evaluator_fixed.py`では`extract_gold_answer()`で正しく抽出

---

### Step 3: モデル呼び出しの確認

**問題**: モデルが呼び出されていない、または空文字列を返している

**確認方法**:
- `debug_samples`の`pred_empty`が`true`なら、モデル呼び出しに問題
- `pred_answer`が空文字列なら、モデルが正しく動作していない

**対処法**:
1. 外部トレーナーのチェックポイントを確認
2. モデルローダーが正しく実装されているか確認
3. `model_predictor`関数が正しく動作しているか確認

---

## 🔧 修正済みevaluatorの使い方

### 基本使用（ダミーモデル）

```bash
# デバッグ用（全件評価、ダミーモデル）
python castle_ex/castle_ex_evaluator_fixed.py \
  --eval-data castle_ex_dataset_v1_0_eval.jsonl \
  --output evaluation_v1_0.json \
  --model-type dummy
```

**注意**: ダミーモデルは実際の評価には使用しない。動作確認用。

---

### 実際のモデルを接続する場合

外部トレーナーの種類に応じて、`castle_ex_evaluator_fixed.py`の`main()`関数を修正：

#### Ollamaの場合

```python
elif args.model_type == 'ollama':
    import requests
    def ollama_predict(prompt: str) -> str:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": args.model, "prompt": prompt}
        )
        return response.json().get("response", "")
    model_predictor = ollama_predict
```

#### Transformersの場合

```python
elif args.model_type == 'transformers':
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model)
    def transformers_predict(prompt: str) -> str:
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_length=512)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    model_predictor = transformers_predict
```

---

## 📊 デバッグ出力の見方

### 正常な場合

```json
{
  "debug_samples": [
    {
      "item_index": 0,
      "layer": 4,
      "gold_answer": "強がりの可能性。本当は不安や痛みがあるかもしれない。",
      "pred_answer": "強がりの可能性。本当は不安や痛みがあるかもしれない。",
      "pred_empty": false
    }
  ],
  "overall": {
    "negative_detection": 0.85,
    ...
  }
}
```

### 問題がある場合

```json
{
  "debug_samples": [
    {
      "item_index": 0,
      "layer": 4,
      "gold_answer": "強がりの可能性。本当は不安や痛みがあるかもしれない。",
      "pred_answer": "",
      "pred_empty": true  // ← これがtrueならモデル呼び出しに問題
    }
  ],
  "overall": {
    "negative_detection": 0.0,  // ← 全部0なら評価が動いてない
    ...
  }
}
```

---

## ✅ チェックリスト

### 評価実行前

- [ ] 学習が完了している（チェックポイントが存在する）
- [ ] 評価データセット（`castle_ex_dataset_v1_0_eval.jsonl`）が存在する
- [ ] モデルローダーが正しく実装されている

### 評価実行後

- [ ] `debug_samples`に5件のサンプルが記録されている
- [ ] `pred_empty`が全て`false`である
- [ ] `gold_answer`が正しく抽出されている
- [ ] `overall`の指標が0.0以外の値になっている
- [ ] `by_layer`の精度が0.0以外の値になっている

---

## 🎯 次のステップ

1. **デバッグモードで評価実行**: `--max-samples 5`で動作確認
2. **モデル接続**: 実際のモデルを`model_predictor`に接続
3. **全件評価**: `--max-samples`を外して全件評価
4. **結果分析**: `evaluation_v1_0.json`を分析してv1.1データを生成

---

## 📝 よくあるエラーと対処法

### エラー1: `gold_answer not found`

**原因**: `messages`に`assistant`ロールがない

**対処**: データセットを確認。`messages`の最後に`assistant`メッセージがあるか確認

---

### エラー2: `pred_answer`が常に空

**原因**: モデル呼び出しが失敗している

**対処**:
1. モデルパス/チェックポイントが正しいか確認
2. モデルローダーの実装を確認
3. 例外が握りつぶされていないか確認

---

### エラー3: 全指標が0.0

**原因**: 評価ロジックが正しく動作していない

**対処**:
1. `debug_samples`を確認
2. `evaluate_response()`の実装を確認
3. `calculate_statistics()`の実装を確認
