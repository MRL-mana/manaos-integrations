# System3 Weekly Tasks Runner
# Runs log rotation and playbook promotion

Write-Host "System3 Weekly Tasks - 2026-01-04 23:34:29" -ForegroundColor Cyan
Write-Host ""

# 1. Log rotation and backup
Write-Host "[1] Running log rotation and backup..." -ForegroundColor Yellow
& python "C:\Users\mana4\Desktop\manaos_integrations\log_rotation_backup.py"
Write-Host ""

# 2. Playbook auto promotion
Write-Host "[2] Running playbook auto promotion..." -ForegroundColor Yellow
& python "C:\Users\mana4\Desktop\manaos_integrations\playbook_auto_promotion.py"
Write-Host ""

Write-Host "Weekly tasks completed" -ForegroundColor Green
