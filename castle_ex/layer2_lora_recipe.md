# Layer2 LoRA 学習：確定レシピ（v1.1 → v1.1.1）

## 方針

- **ベース**: v1.1 フルFT済みモデル（固定）
- **学習データ**: Layer2 のみ（950件 = train 846 / eval 104）
- **目的**: 「常識よりデータを優先する」判断癖を付与
- **影響範囲**: Layer2 のみ（他Layerは触らない）

---

## LoRA 設計（推奨初期値）

| 項目 | 値 |
|------|-----|
| rank (r) | 16 |
| lora_alpha | 32 |
| lora_dropout | 0.05 |
| target_modules | q_proj,k_proj,v_proj,o_proj |

---

## 学習コマンド（そのまま叩ける形）

### バッチで一発

```bat
run_layer2_lora_train.bat
```

### 手動（同じ内容）

```bat
python castle_ex\train_castle_ex_lora.py ^
  --base-model D:\castle_ex_training\castle_ex_v1_1 ^
  --train-data castle_ex_dataset_layer2_lora_train.jsonl ^
  --eval-data castle_ex_dataset_layer2_lora_eval.jsonl ^
  --output-dir D:\castle_ex_training\lora_castle_ex_layer2_v1_1_1 ^
  --lora-r 16 --lora-alpha 32 --lora-dropout 0.05 ^
  --target-modules q_proj,k_proj,v_proj,o_proj ^
  --max-length 512 --batch-size 2 --gradient-accumulation-steps 8 ^
  --learning-rate 2e-4 --max-steps 2000 ^
  --save-steps 500 --eval-steps 500 --fp16
```

- **max-length 512**: Layer2 に十分・速い
- **lr 2e-4**: LoRA は強めでOK
- **eval-steps 500**: 跳ね始めを確認可能

---

## 評価（学習後）

LoRA をロードして v1.1 eval を再実行。

```bat
python castle_ex\castle_ex_evaluator_fixed.py ^
  --model D:\castle_ex_training\castle_ex_v1_1 ^
  --lora D:\castle_ex_training\lora_castle_ex_layer2_v1_1_1 ^
  --model-type transformers --prompt-format phi3 ^
  --eval-data castle_ex_dataset_v1_1_eval.jsonl ^
  --output evaluation_v1_1_1_layer2_lora.json
```

**【v1.1 評価サマリ（貼り用）】** が表示されるので、そのまま貼って最終ジャッジ。

---

## 合格ライン（本番OK）

- **Layer2 acc ≥ 0.6**
- l2_attribute / l2_comparison の **0.0 消滅**
- **invalid = 0** 維持
- 他Layerの acc が **±0.02 以内**

---

## 本番構成（完成形）

```
Base Model
 └─ castle_ex_core (v1.1)
     └─ castle_ex_layer2_lora (v1.1.1)
```

- Layer2 判断は LoRA に任せる
- 他Layerは v1.1 の安定挙動
- 差し替え・ロールバック可能

---

## 跳ねなければ

- **+2,000 step**（合計 4,000）で再学習
- または comparison だけ **+200 件** データを足して再生成・再学習

---

## 続きの手順（チェックリスト）

1. **データ**: `castle_ex_dataset_layer2_lora_train.jsonl` / `_eval.jsonl` があること（`generate_layer2_lora_data.py --out ... --split` で生成済みならスキップ）
2. **学習**: リポジトリルートで `run_layer2_lora_train.bat` を実行 → `D:\castle_ex_training\lora_castle_ex_layer2_v1_1_1` に LoRA が出力される
3. **評価**: 学習後 `run_layer2_lora_eval.bat` を実行 → `evaluation_v1_1_1_layer2_lora.json` を確認し、v1.1 評価サマリを貼って合格ラインを確認
4. **合格ライン**: Layer2 acc ≥ 0.6、l2_attribute / l2_comparison の 0.0 消滅、invalid = 0、他Layer ±0.02 以内
