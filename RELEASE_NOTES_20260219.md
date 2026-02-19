# Release Notes (2026-02-19)

## Summary

- Branch: `master`
- Latest commit: `1f432b5`
- Push status: completed to `origin/master`

## Included Commits

### 1) `1f432b5`
`docs: add openwebui production ops guide and notify helper`

- Added `PRODUCTION_OPERATIONS_GUIDE_v2.md`
- Added `enable_openwebui_production_notify.ps1`

### 2) `90cfa8a`
`chore: add pwsh note to start scripts`

- Added startup note `※ pwsh推奨 / ps1直実行OK` across `start_*.ps1`
- Standardized operator guidance for PowerShell execution

## Post-Push Snapshot

- Git working tree: clean
- `http://127.0.0.1:9502/health` -> `200`
- `http://127.0.0.1:9503/health` -> `200`
- `http://127.0.0.1:3001` -> `200`

## Notes

- This note is intended for quick handoff and operational traceability.
- If additional release granularity is needed, split into docs/ops and runtime sections.
