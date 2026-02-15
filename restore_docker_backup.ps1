# ManaOS Docker Restore Script
# バックアップからDockerボリュームとコンテナデータをリストア

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# バックアップファイルの確認
if (-not (Test-Path $BackupFile)) {
    Write-Host "❌ エラー: バックアップファイルが見つかりません: $BackupFile" -ForegroundColor Red
    exit 1
}

Write-Host "🔄 ManaOS Docker Restore を開始します..." -ForegroundColor Cyan
Write-Host "バックアップファイル: $BackupFile" -ForegroundColor Gray

# 1. バックアップファイルの展開
Write-Host "`n📦 バックアップを展開中..." -ForegroundColor Yellow

$TempDir = Join-Path $env:TEMP "manaos-restore-$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -Path $TempDir -ItemType Directory -Force | Out-Null

if ($BackupFile -match "\.zip$") {
    Expand-Archive -Path $BackupFile -DestinationPath $TempDir -Force
    $BackupPath = Get-ChildItem $TempDir -Directory | Select-Object -First 1 -ExpandProperty FullName
} else {
    $BackupPath = $BackupFile
}

Write-Host "  ✅ 展開完了: $BackupPath" -ForegroundColor Green

# 2. メタデータの読み込み
$MetadataFile = Join-Path $BackupPath "metadata.json"
if (Test-Path $MetadataFile) {
    $Metadata = Get-Content $MetadataFile | ConvertFrom-Json
    Write-Host "`n📝 バックアップ情報:" -ForegroundColor Cyan
    Write-Host "  日時: $($Metadata.BackupDate)" -ForegroundColor Gray
    Write-Host "  バージョン: $($Metadata.ManaOSVersion)" -ForegroundColor Gray
} else {
    Write-Host "`n⚠️ メタデータファイルが見つかりません" -ForegroundColor Yellow
}

# 3. 確認プロンプト
if (-not $Force) {
    Write-Host "`n⚠️ 警告: この操作は既存のデータを上書きします！" -ForegroundColor Yellow
    $Confirmation = Read-Host "続行しますか？ (yes/no)"
    
    if ($Confirmation -ne "yes") {
        Write-Host "❌ 中止しました" -ForegroundColor Red
        Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        exit 0
    }
}

# 4. コンテナの停止
Write-Host "`n🛑 コンテナを停止中..." -ForegroundColor Yellow

docker-compose down 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ 停止完了" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ 一部のコンテナが停止できませんでした" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

# 5. Dockerボリュームのリストア
Write-Host "`n📦 Dockerボリュームをリストア中..." -ForegroundColor Yellow

$VolumeBackups = Get-ChildItem $BackupPath -Filter "*.tar.gz"

foreach ($VolumeBackup in $VolumeBackups) {
    $VolumeName = $VolumeBackup.BaseName
    $FullVolumeName = "manaos_integrations_$VolumeName"
    
    Write-Host "  → $VolumeName" -ForegroundColor Gray
    
    # ボリュームが存在しない場合は作成
    docker volume create $FullVolumeName 2>&1 | Out-Null
    
    # リストア
    docker run --rm `
        -v ${FullVolumeName}:/data `
        -v ${BackupPath}:/backup `
        alpine sh -c "cd /data && tar xzf /backup/$($VolumeBackup.Name)" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ リストア完了" -ForegroundColor Green
    } else {
        Write-Host "    ❌ リストア失敗" -ForegroundColor Red
    }
}

# 6. 設定ファイルのリストア
Write-Host "`n⚙️ 設定ファイルをリストア中..." -ForegroundColor Yellow

$ConfigBackupPath = Join-Path $BackupPath "config"

if (Test-Path $ConfigBackupPath) {
    $ConfigFiles = Get-ChildItem $ConfigBackupPath -Recurse -File
    
    foreach ($ConfigFile in $ConfigFiles) {
        $RelativePath = $ConfigFile.FullName.Substring($ConfigBackupPath.Length + 1)
        $DestPath = Join-Path (Get-Location) $RelativePath
        $DestDir = Split-Path -Parent $DestPath
        
        if (-not (Test-Path $DestDir)) {
            New-Item -Path $DestDir -ItemType Directory -Force | Out-Null
        }
        
        Copy-Item $ConfigFile.FullName -Destination $DestPath -Force
        Write-Host "  ✅ $RelativePath" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠️ 設定ファイルのバックアップが見つかりません" -ForegroundColor Yellow
}

# 7. コンテナの起動
Write-Host "`n🚀 コンテナを起動中..." -ForegroundColor Yellow

docker-compose up -d 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ 起動完了" -ForegroundColor Green
} else {
    Write-Host "  ❌ 起動失敗" -ForegroundColor Red
}

Start-Sleep -Seconds 5

# 8. コンテナ内のデータディレクトリをリストア
Write-Host "`n📂 コンテナデータをリストア中..." -ForegroundColor Yellow

$ContainerPaths = Get-ChildItem $BackupPath -Directory | Where-Object { $_.Name -match "^manaos-" }

foreach ($ContainerPath in $ContainerPaths) {
    $ContainerName = $ContainerPath.Name
    Write-Host "  → $ContainerName" -ForegroundColor Gray
    
    # コンテナが実行中か確認
    $Running = docker ps --filter "name=$ContainerName" --filter "status=running" --format "{{.Names}}"
    
    if (-not $Running) {
        Write-Host "    ⚠️ コンテナが実行されていません" -ForegroundColor Yellow
        continue
    }
    
    $DataDirs = Get-ChildItem $ContainerPath.FullName -Directory
    
    foreach ($DataDir in $DataDirs) {
        $TargetPath = $DataDir.Name -replace "_", "/"
        
        docker cp $DataDir.FullName "${ContainerName}:${TargetPath}" 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✅ $TargetPath" -ForegroundColor Green
        } else {
            Write-Host "    ❌ $TargetPath" -ForegroundColor Red
        }
    }
}

# 9. サービスの再起動
Write-Host "`n♻️ サービスを再起動中..." -ForegroundColor Yellow

docker-compose restart 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ 再起動完了" -ForegroundColor Green
} else {
    Write-Host "  ❌ 再起動失敗" -ForegroundColor Red
}

# 10. クリーンアップ
Write-Host "`n🧹 クリーンアップ中..." -ForegroundColor Yellow

if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  ✅ 一時ファイルを削除しました" -ForegroundColor Green
}

# 11. サービス状態の確認
Write-Host "`n🔍 サービス状態を確認中..." -ForegroundColor Yellow

Start-Sleep -Seconds 3

$Services = docker-compose ps --format json | ConvertFrom-Json

Write-Host "`n📊 サービス状態:" -ForegroundColor Cyan
foreach ($Service in $Services) {
    $Status = if ($Service.State -eq "running") { "✅" } else { "❌" }
    Write-Host "  $Status $($Service.Service): $($Service.State)" -ForegroundColor $(if ($Service.State -eq "running") { "Green" } else { "Red" })
}

# 完了サマリー
Write-Host "`n✅ リストアが完了しました！" -ForegroundColor Green
Write-Host "`n📊 リストアサマリー:" -ForegroundColor Cyan
Write-Host "  バックアップファイル: $(Split-Path -Leaf $BackupFile)" -ForegroundColor Gray
Write-Host "  リストア日時: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# サービスURLの表示
Write-Host "`n🌐 サービスURL:" -ForegroundColor Cyan
Write-Host "  Unified API:    http://localhost:9502" -ForegroundColor Gray
Write-Host "  MRL Memory:     http://localhost:9507" -ForegroundColor Gray
Write-Host "  Learning System: http://localhost:9508" -ForegroundColor Gray
Write-Host "  LLM Routing:    http://localhost:9509" -ForegroundColor Gray
Write-Host "  Gallery API:    http://localhost:5559" -ForegroundColor Gray
Write-Host "  Prometheus:     http://localhost:9090" -ForegroundColor Gray
Write-Host "  Grafana:        http://localhost:3000" -ForegroundColor Gray

Write-Host "`n💡 次のステップ:" -ForegroundColor Yellow
Write-Host "  各サービスにアクセスして動作を確認してください" -ForegroundColor Gray
Write-Host "  問題がある場合は、docker-compose logs <service> でログを確認してください" -ForegroundColor Gray
