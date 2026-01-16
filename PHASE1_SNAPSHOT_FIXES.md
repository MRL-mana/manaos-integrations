# Phase 1 スナップショット修正 - 3つの罠を解消

## ✅ 修正完了項目

### 罠①：メトリクスが0固定になる問題

**問題**: `MRLMemoryMetrics()`を新規作成すると、統計が空になる可能性

**対策**:
1. ダッシュボードJSONをソースにする（`mrl_memory_dashboard.py --json`）
2. フォールバック: 永続化されたメトリクスファイルを読む
3. 最終フォールバック: 直接メトリクスインスタンスから読む（警告付き）

**注意**: メトリクスがメモリ内のみの場合、別プロセスからは取得できません。その場合は、APIサーバーのプロセスから直接取得するか、メトリクスを永続化する必要があります。

---

### 罠②：PIIマスキングが常に`"enabled"`になる問題

**問題**: PIIマスキングをOFFにしても常に`"enabled"`として表示される

**対策**: 環境変数`PII_MASK_ENABLED`から実際の状態を確認

```python
pii_mask_enabled = os.getenv("PII_MASK_ENABLED", "1").lower() in ["1", "true", "yes"]
"pii_mask": "enabled" if pii_mask_enabled else "disabled"
```

---

### 罠③：5xxエラーが常に0になる問題

**問題**: `get_error_count()`が固定で0を返すため、実際のエラーを見逃す

**対策**: ログから実際に5xxエラーをカウント

1. **systemd journalから取得**（Linux、推奨）
   ```bash
   journalctl -u mrl-memory --since "60 min ago"
   ```

2. **ログファイルから取得**（フォールバック）
   - `mrl_memory.log`
   - `logs/mrl_memory.log`
   - など

**正規表現**: `HTTP\s+(5\d{2})|status[:\s]+(5\d{2})`

---

### 追加改善

#### 1. ストレージ健康状態の取得を副作用なしで実行

**問題**: `MRLMemorySystem()`を初期化すると、副作用（ディレクトリ作成、TTL掃除など）が発生する可能性

**対策**: `MRLMemorySystem`を初期化せず、直接ファイルを読む

```python
memory_dir = Path(os.getenv("MRL_MEMORY_DIR", Path(__file__).parent / "mrl_memory"))
```

#### 2. 設定値の明示

**追加項目**: `config`セクション

```json
"config": {
  "write_mode": "readonly",
  "review_effect": "0",
  "write_enabled": "0"
}
```

→ 「書き込みゼロ」だけじゃなく「設定上readonly」を同時に証明できる

#### 3. ストレージ差分（オプション）

**追加項目**: `storage_delta`セクション（ベースラインとの差分）

```json
"storage_delta": {
  "scratchpad_entries": 0,
  "quarantine_entries": 0,
  "promoted_entries": 0
}
```

→ Read-onlyモードで永続化行数が増えていないことを一発で確認できる

---

## 📋 使用方法

### 基本使用

```bash
python phase1_metrics_snapshot.py phase1_metrics_snapshot_baseline.json
```

### ベースラインとの差分を計算

```bash
python phase1_metrics_snapshot.py phase1_metrics_snapshot_warmup.json phase1_metrics_snapshot_baseline.json
```

---

## ⚠️ 注意事項

### メトリクスが0になる可能性

メトリクスがメモリ内のみの場合、別プロセスからは取得できません。その場合は：

1. **APIサーバーのプロセスから直接取得**（将来的な改善）
2. **メトリクスを永続化**（`MRLMemoryMetrics.save_metrics()`を使用）

現在の実装では、メトリクスが0の場合に警告を表示します。

### PIIマスキングの環境変数

環境変数`PII_MASK_ENABLED`を設定してください：

```bash
export PII_MASK_ENABLED=1  # enabled
export PII_MASK_ENABLED=0  # disabled
```

### ログファイルの場所

5xxエラーをカウントするため、ログファイルの場所を確認してください：

- systemd: `journalctl -u mrl-memory`
- ログファイル: `mrl_memory.log` または `logs/mrl_memory.log`

---

## 🎯 判定の信頼性向上

これらの修正により、以下が改善されます：

1. **メトリクスの正確性**: ダッシュボードJSONをソースにすることで、統計が0固定になる問題を回避
2. **セキュリティ設定の正確性**: PIIマスキングの実際の状態を反映
3. **エラー検出**: 実際の5xxエラーをカウントすることで、問題を早期発見
4. **Read-onlyの裏取り**: 設定値の明示とストレージ差分により、Read-onlyモードの健全性を確認

---

**作成日**: 2026-01-15  
**バージョン**: 1.1  
**ステータス**: 3つの罠を解消完了
