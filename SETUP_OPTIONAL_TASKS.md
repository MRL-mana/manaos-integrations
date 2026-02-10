# 忘れないように全部やる：定期タスクの登録

## やること（1回だけ）

**管理者として PowerShell を開き**、以下を実行する。

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\mana4\Desktop\manaos_integrations\scripts\setup_mrl_memory_optional_tasks.ps1"
```

これで次の 4 タスクが登録される。

| タスク名 | いつ | 何をするか |
|----------|------|-------------|
| MRL_Memory_24h_Summary_Daily | 毎日 01:00 | 24時間分のサマリーを `snapshots/` に JSON で保存 |
| MRL_Memory_Dashboard_Daily | 毎日 01:15 | `snapshot_dashboard.html` を最新スナップショットで更新 |
| MRL_Memory_Baseline_Weekly | 毎週日曜 02:00 | 直近スナップショットからベースラインを更新 |
| MRL_Memory_Cleanup_Monthly | 毎月1日 03:00 | 30日より古いスナップショットフォルダを削除 |

## 確認

```powershell
Get-ScheduledTask -TaskName 'MRL_Memory_*' | Select-Object TaskName, State | Format-Table -AutoSize
```

## 注意

- **管理者権限が必要**（タスクの登録のため）
- クリーンアップは「30日より古い」を**実際に削除**する。初回前に `python cleanup_old_snapshots.py snapshots --older-than 30 --dry-run` で対象を確認しておくとよい。
- Python のパスは `C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe` 固定。別の Python を使う場合はスクリプト内の `$python` を書き換える。

---

**更新日**: 2026-01-30
