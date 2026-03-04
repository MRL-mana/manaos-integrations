# CASTLE-EX Layer2 スタイル矯正 LoRA — 勝ちレシピ v1.1.6

**固定日**: 2026-03-04  
**ステータス**: `gate passed` (acc=1.0, contains_hai=0, contains_repeat_phrase=0)  
**Production Adapter**: `D:\castle_ex_training\lora_castle_ex_layer2_prod`

---

## 1. 問題定義

Layer2（関係推論）の応答に以下の癖が出た：

| error_type | 症状例 |
|---|---|
| `aizuchi_tail` | 正答の後ろに「はい。」が余計に付く |
| `repeat_phrase` | 同じフレーズを3回以上繰り返す |
| `verbose_echo` | 質問文をそのままエコーして長くなる |

---

## 2. 失敗した試み（教訓込み）

| バージョン | 設定 | 手 | 結果 | 原因 |
|---|---|---|---|---|
| v1.1.4 | lr=2e-4, steps=4500 | 普通に学習 | gate FAIL (acc=0.25) | train data に positive=False 47% 混在、evaluator バグ |
| v1.1.5 | lr=1e-4, steps=5000 | lr 半減 | gate FAIL (acc=0.25) | 同上（根本原因未修正のまま） |
| v1.1.6 | lr=2e-4, steps=800 | **positive=True only + evaluator 修正** | **gate PASS (acc=1.0)** | ✅ |

### 根本原因 2 つ

1. **学習データの設計ミス**: `positive=False`（悪回答例）を CLM で学習すると、悪回答も next-token prediction の正解として学習される。正答と誤答が相殺されてLoRAの delta が実質ゼロになる。
2. **evaluator のバグ**: `is_correct_negative_v2` が error_type を無視して一律にシグナルワード判定していた。`aizuchi_tail` で「属性値（中/高/低）がpredに含まれている」だけで NG 判定していた。

---

## 3. 勝ちパラメータ

```
base_model:    D:\castle_ex_training\castle_ex_v1_1  (Phi-3 系)
train_data:    castle_ex_dataset_layer2_lora_v1_1_6_posonly_train.jsonl
               → 200件 (positive=True のみ)
eval_data:     castle_ex_dataset_layer2_lora_v1_1_4_stylefix_eval.jsonl
               → 20件 (positive=False, hardneg テスト)
output_dir:    D:\castle_ex_training\lora_castle_ex_layer2_v1_1_6_posonly

# LoRA
lora_r:         16
lora_alpha:     32
lora_dropout:   0.05
target_modules: q_proj, k_proj, v_proj, o_proj

# 学習
learning_rate:              2e-4
max_steps:                  800
save_steps:                 200
eval_steps:                 500
batch_size:                 1
gradient_accumulation_steps: 16
fp16:                       true
max_length:                 384
resume_from_checkpoint:     なし（フレッシュスタート）
```

---

## 4. データ設計ルール（CLM LoRA のみ適用）

- **`positive=True` のみを train data に含める**
- `positive=False`（hardneg / 悪回答例）は **eval data 専用**（LoRAが悪パターンを出さないかテスト）
- DPO / 対比学習を使う場合は chosen/rejected ペア形式に変換してから投入する

```
train: positive=True  → "模範解答を学ぶ"
eval:  positive=False → "悪パターンを出さないかテスト"
```

---

## 5. Evaluator 設計ルール

`is_correct_negative_v2(gold, pred, error_type)` は `error_type` 別に判定する。

| error_type | 判定ロジック |
|---|---|
| `aizuchi_tail` | pred に「はい/いいえ」が含まれていなければ OK（属性値は無視） |
| `repeat_phrase` | pred の同一トークンが3回以上 → NG |
| `verbose_echo` | gold のシグナルワード（の方が/値）が pred に含まれていれば NG |
| `None` / その他 | シグナルワードベースのフォールバック |

---

## 6. 推論時の推奨設定

```python
generate_kwargs = dict(
    max_new_tokens=64,
    do_sample=False,          # greedy
    temperature=None,
    repetition_penalty=1.1,   # repeat_phrase の追加安全弁（任意）
    no_repeat_ngram_size=3,   # 任意
)
```

---

## 7. Gate 条件

| 指標 | 閾値 |
|---|---|
| acc | ≥ 0.75 |
| contains_hai | ≤ 10 |
| contains_repeat_phrase | ≤ 5 |

**v1.1.6 ck800 の実績**: acc=1.0 / hai=0 / repeat=0 → **passed=True**

---

## 8. Production Adapter

```
D:\castle_ex_training\lora_castle_ex_layer2_prod\
├── adapter_config.json
├── adapter_model.safetensors  (12.0 MB)
└── tokenizer.*
```

LoRA ロード例:
```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained(
    r"D:\castle_ex_training\castle_ex_v1_1",
    device_map="cuda:0", torch_dtype="auto", trust_remote_code=True,
)
model = PeftModel.from_pretrained(base, r"D:\castle_ex_training\lora_castle_ex_layer2_prod")
```

---

## 9. 再学習が必要になる条件

以下が発生したら v1.1.7 として小さく当てる：

- 新しいテンプレート追加後に repeat/hai が再発した
- 語彙が増えてスタイルが崩れた
- 他 Layer の学習で Layer2 の口調が汚染された

**通常は再学習不要。**

---

## 10. 再現コマンド

```powershell
# データ生成（positive=True only）
Get-Content .\castle_ex_dataset_layer2_lora_v1_1_4_stylefix_train.jsonl |
  ForEach-Object { $x = $_ | ConvertFrom-Json; if ($x.positive -eq $true) { $_ } } |
  Set-Content .\castle_ex_dataset_layer2_lora_v1_1_6_posonly_train.jsonl -Encoding utf8

# 学習
powershell -ExecutionPolicy Bypass -File ".\run_v116_onebutton.ps1"

# gate
py.exe -3.10 -u scripts\run\run_layer2_quick_eval.py `
  --base-model "D:\castle_ex_training\castle_ex_v1_1" `
  --output-dir "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_6_posonly" `
  --checkpoint-step 800 `
  --eval-data "castle_ex_dataset_layer2_lora_v1_1_4_stylefix_eval.jsonl" `
  --device-map "cuda:0"
```
