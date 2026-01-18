# 🚀 CASTLE-EX 学習進行状況更新

## ✅ 状況

- データファイル（train/eval）検出 OK（`data/` 優先 → ルート → `castle_ex/` の順）
- 学習スクリプトは `scripts/` から実行可能（cwd依存を低減）

## 📍 進行状況の確認方法

```powershell
# 進行状況を確認（定期的に実行）
python scripts/monitor_training.py --output-dir ./outputs/castle_ex_v1_0
```

### チェックポイント確認

```powershell
dir outputs\castle_ex_v1_0\checkpoint-*
```

### TensorBoard

```powershell
tensorboard --logdir ./outputs/castle_ex_v1_0/logs
```

