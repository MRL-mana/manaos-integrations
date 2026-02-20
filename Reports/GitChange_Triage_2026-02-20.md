# Git Change Triage (No Delete)

- Date: 2026-02-20
- Scope: manaos_integrations
- Goal: group changes for clean commits without deletion/move.

## Group A: Ops/Reports/Runbooks (safe)

- .vscode/tasks.json
- Reports/OpenWebUI_Acceptance_Latest_Status.txt
- phase1_metrics_snapshot.json
- Reports/Maintenance_Inventory_2026-02-20.md
- Reports/Maintenance_NoDelete_Runbook.md
- Reports/CleanupCandidates_Logs_2026-02-20.txt
- Reports/CleanupCandidates_DriveTmp_2026-02-20.txt
- Reports/GitChange_Triage_2026-02-20.md

Suggested commit message:
- "ops: refresh reports and tasks"

## Group B: Core integration improvements

- unified_api_server.py
- unified_api_mcp_server/server.py
- tool_server/main.py
- gallery_api_mcp_server/server.py
- manaos_core_api.py
- mem0_integration.py
- google_drive_integration.py
- vscode_cursor_integration.py
- ensure_optional_services.ps1
- run_manaos_full_smoke.ps1
- tests/integration/test_tool_server_integration.py
- check_unconfigured.py

Suggested commit message:
- "feat: image prompt pipeline and integration hardening"

## Group C: New tools and docs

- docs/IMAGE_GENERATION_GUIDE.md
- scripts/generate_image_cli.py
- scripts/maintenance_inventory_dryrun.ps1
- google_calendar_tasks_sheets_integration.py
- reauthenticate_google_api.py

Suggested commit message:
- "docs/tools: add image guide and maintenance helpers"

## Notes

- No deletions performed.
- Keep Group A separate to avoid mixing ops metadata with feature code.
- Group B touches runtime behavior; run smoke tests before commit if desired.
