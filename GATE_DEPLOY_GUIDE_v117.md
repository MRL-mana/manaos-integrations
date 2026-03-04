# v1.1.7 gate判定クイックリファレンス

## タイムライン (2026-03-04 12:57 START)

| 時刻 | イベント |
|------|---------|
| ~14:20 | checkpoint-100 保存 (monitor が eval→gate JSON 生成) |
| ~15:30 | checkpoint-200 保存 |
| ~16:47 | checkpoint-300 保存 → **gate判定** |

※ 1 step ≈ 50s (GA=16, batch=1)

---

## gate判定実行手順

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations

# 1. gate JSON を確認
Get-ChildItem Reports -Filter "gate_v117_ck300_*.json" | Sort-Object LastWriteTime -Desc | Select-Object -First 1 | Get-Content | ConvertFrom-Json

# 2. gate判定+自動 prod 差し替え
powershell -ExecutionPolicy Bypass -File .\auto_gate_check_and_deploy_v117.ps1

#    または DryRun で内容確認だけ
powershell -ExecutionPolicy Bypass -File .\auto_gate_check_and_deploy_v117.ps1 -DryRun
```

---

## GO判定基準

| 指標 | GO条件 |
|------|-------|
| acc | >= 0.75 |
| contains_hai | <= 10 |
| contains_repeat_phrase | <= 5 |

---

## NO-GO 対応フロー

### NO-GO A (acc < 0.75)
```powershell
# NG例をeval JSONから自動抽出して再注入データ生成
powershell -ExecutionPolicy Bypass -File .\nogo_A_inject_and_retrain.ps1

# 出力: castle_ex_dataset_layer2_lora_v1_1_7_1_train.jsonl
# → retrain:
powershell -ExecutionPolicy Bypass -File .\run_v117_1_patch_onebutton.ps1
```

### NO-GO B (repeat >= 6)
```powershell
# デコードパラメータ確認（max_new_tokens=64, no_repeat_ngram_size=3）
powershell -ExecutionPolicy Bypass -File .\nogo_B_check_decode_params.ps1
```

### NO-GO C (hai >= 11)
```powershell
# 短文化正例プレースホルダー生成（output は要人手編集）
powershell -ExecutionPolicy Bypass -File .\nogo_C_add_short_positives.ps1
# → output フィールドを編集してから run_v117_1_patch_onebutton.ps1
```

---

## init-lora-from 注意点

v1.1.7 学習起動時に以下 warning が出た:
```
[init-lora-from] missing=259 unexpected=64
```
原因: prod adapter が `qkv_proj` (Phi-3 combined), 学習設定が `q/k/v_proj` (split)  
影響: **warm-start は機能せずランダム初期化と同等**  
対応: checkpoint-100 の acc が 0.4 前後なら正常と判断して待機、0.3未満なら停止を検討

---

## パス早見表

| 用途 | パス |
|------|-----|
| 学習出力 | `D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_patch` |
| prod adapter | `D:\castle_ex_training\lora_castle_ex_layer2_prod` |
| prod backup | `D:\castle_ex_training\_prod_backups\` |
| gate JSON | `Reports\gate_v117_ck300_*.json` |
| eval JSON | `Reports\castle_ex_layer2_quick_eval_checkpoint-300_*.json` |
| monitor log | `logs\monitor_v117_ck300_*.log` |
| train stdout | `logs\layer2_lora_v117_train_*.stdout.log` |
