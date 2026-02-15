# ManaOS Docker Backup Script
# すべてのDockerボリュームとコンテナデータをバックアップ

param(
    [string]$BackupDir = ".\backups\docker",
    [switch]$Compress = $true,
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

# バックアップディレクトリの作成
if (-not (Test-Path $BackupDir)) {
    New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupPath = Join-Path $BackupDir "manaos-backup-$Timestamp"
New-Item -Path $BackupPath -ItemType Directory -Force | Out-Null

Write-Host "🔄 ManaOS Docker Backup を開始します..." -ForegroundColor Cyan
Write-Host "バックアップ先: $BackupPath" -ForegroundColor Gray

# 1. Dockerボリュームのバックアップ
Write-Host "`n📦 Dockerボリュームをバックアップ中..." -ForegroundColor Yellow

$Volumes = @(
    "manaos_integrations_prometheus-data",
    "manaos_integrations_grafana-data"
)

foreach ($Volume in $Volumes) {
    $VolumeName = $Volume -replace "manaos_integrations_", ""
    Write-Host "  → $VolumeName" -ForegroundColor Gray
    
    $BackupFile = Join-Path $BackupPath "$VolumeName.tar.gz"
    
    docker run --rm `
        -v ${Volume}:/data `
        -v ${BackupPath}:/backup `
        alpine tar czf /backup/$VolumeName.tar.gz -C /data . 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ 完了" -ForegroundColor Green
    } else {
        Write-Host "    ❌ 失敗" -ForegroundColor Red
    }
}

# 2. コンテナ内のデータディレクトリをバックアップ
Write-Host "`n📂 コンテナデータをバックアップ中..." -ForegroundColor Yellow

$Containers = @(
    @{Name="manaos-unified-api"; Paths=@("/app/data", "/app/logs")},
    @{Name="manaos-mrl-memory"; Paths=@("/app/data/memory_cache", "/app/logs")},
    @{Name="manaos-learning-system"; Paths=@("/app/data", "/app/logs")},
    @{Name="manaos-gallery-api"; Paths=@("/app/gallery_images", "/app/logs")}
)

foreach ($Container in $Containers) {
    $ContainerName = $Container.Name
    Write-Host "  → $ContainerName" -ForegroundColor Gray
    
    # コンテナが実行中か確認
    $Running = docker ps --filter "name=$ContainerName" --filter "status=running" --format "{{.Names}}"
    
    if (-not $Running) {
        Write-Host "    ⚠️ コンテナが実行されていません" -ForegroundColor Yellow
        continue
    }
    
    foreach ($Path in $Container.Paths) {
        $SafePath = $Path -replace "/", "_"
        $DestPath = Join-Path $BackupPath "$ContainerName$SafePath"
        
        docker cp "${ContainerName}:${Path}" $DestPath 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✅ $Path" -ForegroundColor Green
        } else {
            Write-Host "    ❌ $Path (存在しない可能性)" -ForegroundColor Red
        }
    }
}

# 3. Docker Composeファイルと設定をバックアップ
Write-Host "`n⚙️ 設定ファイルをバックアップ中..." -ForegroundColor Yellow

$ConfigFiles = @(
    "docker-compose.yml",
    ".env",
    "Dockerfile",
    "monitoring\prometheus.yml",
    "monitoring\grafana\datasources\prometheus.yml",
    "monitoring\grafana\dashboards\dashboard.yml"
)

$ConfigBackupPath = Join-Path $BackupPath "config"
New-Item -Path $ConfigBackupPath -ItemType Directory -Force | Out-Null

foreach ($File in $ConfigFiles) {
    if (Test-Path $File) {
        $Dest = Join-Path $ConfigBackupPath $File
        $DestDir = Split-Path -Parent $Dest
        
        if (-not (Test-Path $DestDir)) {
            New-Item -Path $DestDir -ItemType Directory -Force | Out-Null
        }
        
        Copy-Item $File -Destination $Dest -Force
        Write-Host "  ✅ $File" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ $File (見つかりません)" -ForegroundColor Yellow
    }
}

# 4. バックアップのメタデータを作成
Write-Host "`n📝 メタデータを作成中..." -ForegroundColor Yellow

$Metadata = @{
    Timestamp = $Timestamp
    BackupDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    ManaOSVersion = "1.0.0"
    DockerVersion = (docker version --format "{{.Server.Version}}")
    Containers = (docker ps --format "{{.Names}}:{{.Status}}")
    Volumes = $Volumes
} | ConvertTo-Json -Depth 3

$Metadata | Out-File (Join-Path $BackupPath "metadata.json") -Encoding UTF8

Write-Host "  ✅ metadata.json" -ForegroundColor Green

# 5. 圧縮（オプション）
if ($Compress) {
    Write-Host "`n🗜️ バックアップを圧縮中..." -ForegroundColor Yellow
    
    $ZipFile = "$BackupPath.zip"
    Compress-Archive -Path $BackupPath -DestinationPath $ZipFile -Force
    
    if (Test-Path $ZipFile) {
        Remove-Item -Path $BackupPath -Recurse -Force
        Write-Host "  ✅ 圧縮完了: $(Split-Path -Leaf $ZipFile)" -ForegroundColor Green
        
        $Size = (Get-Item $ZipFile).Length / 1MB
        Write-Host "  📊 サイズ: $([math]::Round($Size, 2)) MB" -ForegroundColor Gray
    }
}

# 6. 古いバックアップの削除
Write-Host "`n🧹 古いバックアップを削除中..." -ForegroundColor Yellow

$CutoffDate = (Get-Date).AddDays(-$RetentionDays)
$OldBackups = Get-ChildItem $BackupDir -Filter "manaos-backup-*" | 
    Where-Object { $_.LastWriteTime -lt $CutoffDate }

if ($OldBackups.Count -gt 0) {
    foreach ($OldBackup in $OldBackups) {
        Remove-Item $OldBackup.FullName -Recurse -Force
        Write-Host "  🗑️ 削除: $($OldBackup.Name)" -ForegroundColor Gray
    }
    Write-Host "  ✅ $($OldBackups.Count) 件の古いバックアップを削除しました" -ForegroundColor Green
} else {
    Write-Host "  ℹ️ 削除するバックアップはありません" -ForegroundColor Gray
}

# 完了サマリー
Write-Host "`n✅ バックアップが完了しました！" -ForegroundColor Green
Write-Host "`n📊 バックアップサマリー:" -ForegroundColor Cyan
Write-Host "  バックアップ先: $BackupDir" -ForegroundColor Gray
Write-Host "  タイムスタンプ: $Timestamp" -ForegroundColor Gray
Write-Host "  保持期間: $RetentionDays 日" -ForegroundColor Gray

# バックアップファイルの一覧を表示
$BackupFiles = Get-ChildItem $BackupDir -Filter "manaos-backup-*"
Write-Host "`n📁 バックアップファイル ($($BackupFiles.Count) 件):" -ForegroundColor Cyan

foreach ($File in $BackupFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 5) {
    $Size = $File.Length / 1MB
    $Age = [math]::Round(((Get-Date) - $File.LastWriteTime).TotalDays, 1)
    Write-Host "  • $($File.Name) ($([math]::Round($Size, 2)) MB, $Age 日前)" -ForegroundColor Gray
}

Write-Host "`n💡 リストア方法:" -ForegroundColor Yellow
Write-Host "  .\restore_docker_backup.ps1 -BackupFile '$BackupDir\manaos-backup-$Timestamp.zip'" -ForegroundColor Gray
