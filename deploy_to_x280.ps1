# Deploy scripts to X280
# Transfer scripts with auto-admin functionality to X280

Write-Host "=== Deploy Scripts to X280 ===" -ForegroundColor Cyan
Write-Host ""

# X280 connection settings
$X280Host = "x280"
$X280User = "mana"
$X280RemoteDir = "C:\manaos_x280"

# Files to transfer
$filesToTransfer = @(
    "x280_common_admin_check.ps1",
    "x280_api_gateway_start.ps1",
    "x280_api_gateway.py",
    "common_admin_check.ps1"
)

Write-Host "[1/3] Checking X280 connection..." -ForegroundColor Yellow
try {
    $testResult = ssh $X280Host "echo Connection OK; hostname" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Connected to X280" -ForegroundColor Green
        Write-Host "  $testResult" -ForegroundColor Gray
    } else {
        Write-Host "[ERROR] Cannot connect to X280" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] X280 connection error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Creating remote directory..." -ForegroundColor Yellow
$createDirCmd = "powershell.exe -Command `"if (-not (Test-Path '$X280RemoteDir')) { New-Item -ItemType Directory -Path '$X280RemoteDir' -Force | Out-Null; Write-Host 'Directory created' } else { Write-Host 'Directory exists' }`""
$createDirResult = ssh $X280Host $createDirCmd 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Remote directory ready" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Remote directory creation error (continuing...)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] Transferring files..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$transferredFiles = @()
$failedFiles = @()

foreach ($file in $filesToTransfer) {
    $localPath = Join-Path $scriptDir $file
    if (Test-Path $localPath) {
        Write-Host "  Transferring: $file..." -NoNewline -ForegroundColor Gray
        
        # Transfer via SCP
        $remotePath = "$X280RemoteDir\$file"
        $scpResult = scp $localPath "${X280Host}:${remotePath}" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " [OK]" -ForegroundColor Green
            $transferredFiles += $file
        } else {
            Write-Host " [FAILED]" -ForegroundColor Red
            Write-Host "    Error: $scpResult" -ForegroundColor Red
            $failedFiles += $file
        }
    } else {
        Write-Host "  Skip: $file (not found)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Transfer Results ===" -ForegroundColor Cyan
Write-Host "Success: $($transferredFiles.Count) files" -ForegroundColor Green
if ($failedFiles.Count -gt 0) {
    Write-Host "Failed: $($failedFiles.Count) files" -ForegroundColor Red
    foreach ($file in $failedFiles) {
        Write-Host "  - $file" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== How to Run on X280 ===" -ForegroundColor Cyan
Write-Host "SSH to X280 and run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ssh $X280Host" -ForegroundColor White
Write-Host "  cd $X280RemoteDir" -ForegroundColor White
Write-Host "  .\x280_api_gateway_start.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or, remote execution:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ssh $X280Host `"cd $X280RemoteDir; .\x280_api_gateway_start.ps1`"" -ForegroundColor White
Write-Host ""
