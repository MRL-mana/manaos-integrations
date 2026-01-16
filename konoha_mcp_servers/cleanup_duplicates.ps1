# 重複ファイルを整理（最新版のみ保持）

Write-Host "=== 重複ファイルの整理 ===" -ForegroundColor Cyan
Write-Host ""

$baseDir = "konoha_mcp_servers"
$backupDir = "$baseDir\duplicates_backup"

# バックアップディレクトリを作成
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

# 重複ファイルの定義（最新版を優先）
$duplicates = @{
    "manaos_mcp_server.py" = @{
        "keep" = "archive_20251106"
        "remove" = @("manaos-knowledge_mcp")
    }
    "stitch_mcp_server.py" = @{
        "keep" = "archive_20251106"
        "remove" = @("scripts_additional")
    }
    "image_editor_mcp_server.py" = @{
        "keep" = "archive_20251106"
        "remove" = @("manaos-knowledge_mcp")
    }
    "alita_mct_mcp_server.py" = @{
        "keep" = "archive_20251106"
        "remove" = @("manaos-knowledge_mcp")
    }
    "reflection_mcp_server.py" = @{
        "keep" = "archive_20251106"
        "remove" = @("manaos-knowledge_mcp")
    }
    "mcp_server_gateway.py" = @{
        "keep" = "archive_20251106"
        "remove" = @("manaos-knowledge")
    }
}

$movedCount = 0

foreach ($filename in $duplicates.Keys) {
    $keepDir = $duplicates[$filename]["keep"]
    $removeDirs = $duplicates[$filename]["remove"]
    
    Write-Host "処理中: $filename" -ForegroundColor Yellow
    Write-Host "  保持: $keepDir\$filename" -ForegroundColor Green
    
    foreach ($removeDir in $removeDirs) {
        $removePath = Join-Path $baseDir (Join-Path $removeDir $filename)
        if (Test-Path $removePath) {
            $backupPath = Join-Path $backupDir (Join-Path $removeDir $filename)
            $backupParent = Split-Path $backupPath -Parent
            if (-not (Test-Path $backupParent)) {
                New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
            }
            Move-Item -Path $removePath -Destination $backupPath -Force
            Write-Host "  移動: $removeDir\$filename -> duplicates_backup\" -ForegroundColor Gray
            $movedCount++
        }
    }
    Write-Host ""
}

Write-Host "[OK] $movedCount 個の重複ファイルをバックアップに移動しました" -ForegroundColor Green
Write-Host "バックアップ先: $backupDir" -ForegroundColor Gray










