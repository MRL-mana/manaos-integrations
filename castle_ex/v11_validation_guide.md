# v1.1 検証ラン手順（品質維持・速度1桁改善）

## やること

1. **検証ラン**（max_seq=1024, batch=1, max_steps=2000）を回す
2. 終わったら **評価** して **【v1.1 評価サマリ（貼り用）】** を出す
3. その数字で「本番行く / LoRA に切り替える / データを足す」を決める

---

## 1) 検証ランを回す

```bat
run_v11_validation.bat
```

または手動:

```bat
python castle_ex\train_castle_ex_full.py ^
  --model D:\castle_ex_training\castle_ex_v1_0 ^
  --output-dir D:\castle_ex_training\castle_ex_v1_1_validation ^
  --train-data castle_ex_dataset_v1_1_train.jsonl ^
  --eval-data castle_ex_dataset_v1_1_eval.jsonl ^
  --no-eval ^
  --learning-rate 1.0e-5 ^
  --max-length 1024 ^
  --batch-size 1 ^
  --save-steps 500 ^
  --save-total-limit 2 ^
  --max-steps 2000
```

- **v1.0 から新規**に 2000 step だけ回す（既存の castle_ex_v1_1 とは別フォルダ）
- 想定: 共有GPUメモリほぼ0、step 数秒〜10秒台、**数時間以内で完了**

---

## 2) 評価して【v1.1 評価サマリ（貼り用）】を出す

検証ランが終わったら、**最後のチェックポイント**（例: `checkpoint-2000`）を指定して評価する。

```bat
python castle_ex\castle_ex_evaluator_fixed.py ^
  --eval-data castle_ex_dataset_v1_1_eval.jsonl ^
  --model D:\castle_ex_training\castle_ex_v1_1_validation\checkpoint-2000 ^
  --model-type transformers ^
  --prompt-format phi3 ^
  --output evaluation_v1_1_validation.json
```

- チェックポイントは `save_steps=500` なので `checkpoint-500`, `1000`, `1500`, `2000` のいずれか。**最後に保存されたフォルダ**を `--model` に指定する（2000 step で止まるなら `checkpoint-2000`）。
- 評価結果の JSON が出たら、評価ツールの **【v1.1 評価サマリ（貼り用）】** 表示部分をコピーして貼る。

---

## 3) 判断基準

- **Layer2 acc ≥ 0.6 & invalid=0** → データは勝ち。このあと本番（max_seq 1536/2048 やフルFT）に進む or LoRA に切り替えてさらに短くする。
- 届かない → データ側を一手足す or 設定（epochs / max_steps）を少し伸ばして再検証。

---

## 設定まとめ（検証ラン）

| 項目 | 値 |
|------|-----|
| max_seq_length | 1024 |
| per_device_train_batch_size | 1 |
| gradient_accumulation_steps | 8（スクリプト既定） |
| gradient_checkpointing | True（既定） |
| save_steps | 500 |
| max_steps | 2000 |
| LoRA/QLoRA | なし（フルFTのまま） |
