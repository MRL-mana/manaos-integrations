# artifacts/ — 生成物置き場ルール

JSONLはすべて **生成物** 扱い。repoにはスクリプトとseedだけ残す。

## 再生成手順

| ファイル | 生成スクリプト |
|---|---|
| `castle_ex_dataset_layer2_lora_v*.jsonl` | `castle_ex/generate_layer2_lora_data_v*.py` |
| `castle_ex_dataset_layer2_lora_*_audit100.jsonl` | `castle_ex/generate_layer2_audit_data.py` |

```powershell
# 例: v1.1.7 データ再生成
py -3.10 castle_ex/generate_layer2_lora_data_v1_1_7.py
```

## gitignoreルール

- `artifacts/**/*.jsonl` → 除外（生成物）
- `artifacts/**/*.json` → 除外（生成物）
- `Reports/castle_ex_layer2_quick_eval_*.json` → 除外（ローカル運用）
- `Reports/gate_v1*.json` → 除外（ローカル運用）

## prod adapter の更新手順

1. `monitor_*_ckpt_then_quick_eval.ps1` が `passed=true` を返す
2. `lora_castle_ex_layer2_prod` を新adapterで差し替え
3. 100件監査セットで回帰確認
4. OKなら確定 → コミット `feat: prod adapter updated to vX.X.X`
