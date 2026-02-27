# OpenWebUI/Tailscale Production Operations Guide v2

## Quick Start (Production-Ready)

### Startup (one-time)
```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
powershell -NoProfile -ExecutionPolicy Bypass -File ".\operate_openwebui_production.ps1"
```

### Enable Notifications (optional, one-time)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\enable_openwebui_production_notify.ps1" `
  -WebhookUrl "YOUR_WEBHOOK_URL" `
  -WebhookFormat discord `
  -WebhookMention "@ops"
```

### Daily Health Check (automatic)
- Scheduled at 09:00 (editable via DailyTime parameter)
- Auto-enabled after production operation startup
- Includes auto-recovery on failure

### Manual Health Check
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\check_openwebui_production.ps1" `
  -RequireStartupSource -AutoRecoverOnFailure
```

## OpenWebUI Acceptance Monitoring

### One-time Registration (Daily + Light Monitor)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\register_openwebui_acceptance_daily_task.ps1" `
  -AlsoRegisterLightMonitor -LightIntervalMinutes 5
```

### Manual Run (Non-stop)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '.\run_openwebui_acceptance_pipeline_full_auto.ps1'; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & '.\check_latest_openwebui_acceptance.ps1' -RequirePass; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & '.\notify_openwebui_acceptance_pass.ps1' -WriteStatusFile"
```

### Light Monitor Job (on-demand)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\run_openwebui_acceptance_status_monitor_job.ps1"
```

## Environment Variables (Advanced)

Set these once to enable notifications globally:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\set_openwebui_notify_env.ps1" `
  -WebhookUrl "YOUR_WEBHOOK_URL" `
  -WebhookFormat discord `
  -WebhookMention "@ops"
```

Then all production scripts will auto-detect and use them:
- `MANAOS_WEBHOOK_URL`
- `MANAOS_WEBHOOK_FORMAT`
- `MANAOS_WEBHOOK_MENTION`
- `MANAOS_NOTIFY_ON_SUCCESS` (true/false)

### Clear Environment Variables
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\set_openwebui_notify_env.ps1" -Clear
```

## Endpoints

- **Local**: http://127.0.0.1:3001
- **Tailscale IP**: http://100.73.247.100:3001
- **Tailscale HTTPS**: https://mana.tail370497.ts.net

## Startup Methods

1. **Automatic (preferred)**  
   - HKCU Run entry: `ManaOS_OpenWebUI_Tailscale_AutoStart` (logon)
   - Daily health: `ManaOS_OpenWebUI_DailyHealth` (09:00 scheduled)
   - Post-logon verify: `ManaOS_OpenWebUI_Verify_OnLogon` (run-key fallback)

2. **Manual**  
   - Run `operate_openwebui_production.ps1` from terminal

## Monitoring & Recovery

| Component | Status | Last Check |
|-----------|--------|------------|
| Production operation | ✅ OK | [logs/production_operation_latest.json](logs/production_operation_latest.json) |
| Health check | ✅ PASSED | [logs/production_health_latest.json](logs/production_health_latest.json) |
| Daily registration | ✅ REGISTERED | [logs/daily_health_registration_status.json](logs/daily_health_registration_status.json) |
| Auto-recovery | ✅ ENABLED | [logs/production_recovery_latest.json](logs/production_recovery_latest.json) |

## Logs & Diagnostics

Latest runs:
- `logs/production_operation_latest.json`
- `logs/production_health_latest.json`
- `logs/production_health_latest.log`
- `logs/verify_openwebui_autostart_last.log`

History (per-line JSON):
- `logs/production_operation_history.jsonl`
- `logs/production_health_history.jsonl`
- `logs/production_recovery_history.jsonl`
- `logs/openwebui_tailscale_status_history.jsonl`

Reason dictionary:
- `latest_ok_reason` / `ok_reason` values and meanings: [REASON_ENUM.md](REASON_ENUM.md)
- Lint (manual): `pwsh -NoProfile -ExecutionPolicy Bypass -File .\lint_reason_enum.ps1 -IncludeCheckScripts`
- Lint task install: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\install_reason_enum_lint_task.ps1 -IncludeCheckScripts -RunNow`
- Lint task install (Webhook): `pwsh -NoProfile -ExecutionPolicy Bypass -File .\install_reason_enum_lint_task.ps1 -IncludeCheckScripts -WebhookUrl "YOUR_WEBHOOK_URL" -WebhookFormat discord -WebhookMention "@ops" -NotifyFailureCooldownMinutes 60 -RunNow`
- Lint task status: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_lint_task.ps1`

Reason lint notify diagnostics:
- `latest_failure_notify_attempted: True` / `latest_failure_notified: False` / `latest_failure_notify_suppressed_reason: webhook_not_configured` → Webhook未設定
- `latest_failure_notify_attempted: True` / `latest_failure_notified: False` / `latest_failure_notify_suppressed_reason: notify_send_failed` → Webhook送信失敗
- `latest_failure_notify_attempted: True` / `latest_failure_notified: False` / `latest_failure_notify_suppressed_reason: same_category_cooldown(...m_remaining)` → クールダウン抑制
- 通知テスト（擬似失敗）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\run_reason_enum_lint_once.ps1 -IncludeCheckScripts -SimulateFailure`
- cooldown実地検証（Scheduler経由・自動復帰込み）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\verify_reason_enum_lint_cooldown.ps1`
- cooldown自己診断タスク登録（週次）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\install_reason_enum_lint_cooldown_verify_task.ps1 -Day SUN -StartTime 03:30`
- cooldown自己診断タスク解除: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\uninstall_reason_enum_lint_cooldown_verify_task.ps1`
- cooldown自己診断タスク解除→未登録確認: `pwsh -NoProfile -ExecutionPolicy Bypass -Command "& '.\uninstall_reason_enum_lint_cooldown_verify_task.ps1'; & '.\status_reason_enum_lint_cooldown_verify_task.ps1'; if ($LASTEXITCODE -ne 0) { Write-Host '[OK] Cooldown verify task not found expected after uninstall'; exit 0 }"`
- cooldownライフサイクル実行（要約ログ保存）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\run_reason_enum_lint_cooldown_lifecycle.ps1`
- cooldownライフサイクル実行（RequirePassAfterRun）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\run_reason_enum_lint_cooldown_lifecycle.ps1 -RequirePassAfterRun`
- cooldownライフサイクル状態: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_lint_cooldown_lifecycle.ps1`
- cooldownライフサイクル状態（RequirePass / 失敗時 exit 1）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_lint_cooldown_lifecycle.ps1 -RequirePass`
- cooldownライフサイクル最新ログ: `logs/reason_enum_cooldown_lifecycle.latest.json`
- cooldownライフサイクル履歴: `logs/reason_enum_cooldown_lifecycle.history.jsonl`
- opsスナップショット出力: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\export_reason_enum_ops_snapshot.ps1`
- opsスナップショット出力（JSON）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\export_reason_enum_ops_snapshot.ps1 -AsJson`
- opsスナップショット状態: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_ops_snapshot.ps1`
- opsスナップショット状態（JSON）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_ops_snapshot.ps1 -AsJson`
- opsスナップショット状態（RequirePass / 失敗時 exit 1）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_ops_snapshot.ps1 -RequirePass`
- opsスナップショット最新: `logs/reason_enum_ops_snapshot.latest.json`
- opsスナップショット履歴: `logs/reason_enum_ops_snapshot.history.jsonl`
- cooldown自己診断タスク状態: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_lint_cooldown_verify_task.ps1`
- cooldown自己診断タスク状態（JSON）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\status_reason_enum_lint_cooldown_verify_task.ps1 -AsJson`
- 通知フロー一括テスト: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\test_reason_enum_lint_notify_flow.ps1 -IncludeCheckScripts`
- フルチェーン一括テスト（通知 + クールダウン）: `pwsh -NoProfile -ExecutionPolicy Bypass -File .\test_reason_enum_lint_full_chain.ps1 -IncludeCheckScripts`
- 補足: status出力の `task_last_result_meaning` で Scheduler の前回結果コードを即時解釈可能
- 補足: `latest_ok_reason: source_missing` のときは `latest_ok_reason_bridge` にタスク結果由来の推定理由を表示

Reason lint (recommended before commit):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\lint_reason_enum.ps1" -IncludeCheckScripts
```

VS Code task:
- `Tasks: Run Task` → `ManaOS: Reason Enum Lint`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Verify Task Status (JSON)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Verify Lifecycle`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Lifecycle Run (Log)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Lifecycle Run (Log+RequirePass)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Lifecycle Status`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Lifecycle Status (JSON)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Lifecycle Status (RequirePass)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Cooldown Lifecycle Full`
- `Tasks: Run Task` → `ManaOS: Reason Enum Ops Snapshot Export`
- `Tasks: Run Task` → `ManaOS: Reason Enum Ops Snapshot Export (JSON)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Ops Snapshot Status`
- `Tasks: Run Task` → `ManaOS: Reason Enum Ops Snapshot Status (JSON)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Ops Snapshot Status (RequirePass)`
- `Tasks: Run Task` → `ManaOS: Reason Enum Ops Snapshot Full`

## Troubleshooting

### OpenWebUI not responding
```powershell
docker ps --filter "name=open-webui"
# If stopped, docker start open-webui
```

### Tailscale connectivity check
```powershell
$ts = Join-Path $env:ProgramFiles 'Tailscale IPN\tailscale.exe'
& $ts status
```

### Force recovery
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\recover_openwebui_production.ps1" `
  -RequireStartupSource -MaxAgeMinutes 180
```

## Notes

- Scheduled task creation may fail due to permissions; fallback to HKCU Run is automatic.
- All health checks require startup evidence (run-key or scheduled task).
- Auto-recovery re-runs the full production operation if health check fails.
- Webhook notifications support: `generic`, `slack`, `discord` formats.
