# ManaOS 統合起動スクリプト - マスター版
# すべての起動スクリプトを統合した包括的な起動システム

param(
    [Parameter()]
    [ValidateSet('minimal', 'standard', 'full', 'core', 'optional', 'development')]
    [string]$Profile = 'standard',
    
    [Parameter()]
    [switch]$SkipHealthCheck,
    
    [Parameter()]
    [switch]$DryRun
)
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        ManaOS 統合起動システム v2.0                      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "プロファイル: $Profile" -ForegroundColor Yellow
if ($DryRun) {
    Write-Host "モード: DRY RUN（実際には起動しません）" -ForegroundColor Yellow
}
Write-Host ""

# ===== サービス定義 =====
$coreServices = @(
    @{Name="MRL Memory"; Port=5105; Script="mrl_memory_integration"; Module=$true},
    @{Name="LLM Routing"; Port=5111; Script="llm_routing_mcp_server"; Module=$true},
    @{Name="Learning System"; Port=5126; Script="learning_system_api"; Module=$true},
    @{Name="Video Pipeline"; Port=5112; Script="video_pipeline_mcp_server"; Module=$true},
    @{Name="Unified API"; Port=9502; Script="unified_api_server.py"; Module=$false; Py310=$true}
)

$infrastructureServices = @(
    @{Name="Ollama"; Port=11434; External=$true; Check="/api/tags"},
    @{Name="Gallery API"; Port=5559; Script="gallery_api_server.py"; Module=$false}
)

$mcpServices = @(
    @{Name="Pico HID MCP"; Port=5136; Script="pico_hid_mcp_server"; Module=$true}
)

$optionalServices = @(
    @{Name="Moltbot Gateway"; Port=8088; Script="start_moltbot.ps1"; ScriptFile=$true},
    @{Name="UI Operations"; Port=5110; Script="ui_operations_api.py"; Module=$false},
    @{Name="ComfyUI"; Port=8188; External=$true}
)

# ===== プロファイル別サービス選択 =====
$servicesToStart = @()

switch ($Profile) {
    'minimal' {
        $servicesToStart = $coreServices[0..2] + $coreServices[4]  # MRL, LLM, Learning, Unified
    }
    'standard' {
        $servicesToStart = $coreServices + $infrastructureServices[0..1]  # Core + Ollama, Gallery
    }
    'full' {
        $servicesToStart = $coreServices + $infrastructureServices + $mcpServices + $optionalServices
    }
    'core' {
        $servicesToStart = $coreServices
    }
    'optional' {
        $servicesToStart = $optionalServices
    }
    'development' {
        $servicesToStart = $coreServices[0..2] + $coreServices[4] + $infrastructureServices[1]
    }
}

Write-Host "起動予定: $($servicesToStart.Count) サービス" -ForegroundColor Green
Write-Host ""

# ===== ヘルパー関数 =====
function Test-ServiceRunning {
    param([int]$Port)
    
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        return $connection -ne $null
    } catch {
        return $false
    }
}

function Test-ServiceHealth {
    param(
        [int]$Port,
        [string]$Endpoint = "/health"
    )
    
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port$Endpoint" -TimeoutSec 3 -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-ServiceProcess {
    param(
        [hashtable]$Service
    )
    
    if ($DryRun) {
        Write-Host "  [DRY RUN] $($Service.Name) を起動"; return $true
    }
    
    # 外部サービスはスキップ
    if ($Service.External) {
        Write-Host "  ⏭️  $($Service.Name) は外部サービス（スキップ）" -ForegroundColor Gray
        return $true
    }
    
    # すでに起動中かチェック
    if (Test-ServiceRunning -Port $Service.Port) {
        Write-Host "  ✅ $($Service.Name) は既に起動中" -ForegroundColor Green
        return $true
    }
    
    try {
        if ($Service.Module) {
            # Python モジュールとして起動
            $cmd = "python -m $($Service.Script)"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:PYTHONIOENCODING='utf-8'; $cmd" -WindowStyle Minimized
        } elseif ($Service.ScriptFile) {
            # PowerShell スクリプトとして起動
            $scriptPath = Join-Path $scriptDir $Service.Script
            Start-Process powershell -ArgumentList "-NoExit", "-File", $scriptPath -WindowStyle Minimized
        } elseif ($Service.Py310) {
            # Python 3.10 指定
            $cmd = "py -3.10 $($Service.Script)"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:PORT='$($Service.Port)'; $cmd" -WindowStyle Minimized
        } else {
            # 通常の Python スクリプト
            $cmd = "python $($Service.Script)"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:PORT='$($Service.Port)'; $cmd" -WindowStyle Minimized
        }
        
        Write-Host "  🚀 $($Service.Name) を起動しました" -ForegroundColor Green
        Start-Sleep -Seconds 2
        return $true
        
    } catch {
        Write-Host "  ❌ $($Service.Name) の起動に失敗: $_" -ForegroundColor Red
        return $false
    }
}

# ===== メイン処理 =====
$successCount = 0
$failCount = 0

foreach ($service in $servicesToStart) {
    Write-Host "[$($servicesToStart.IndexOf($service)+1)/$($servicesToStart.Count)] " -NoNewline
    
    if (Start-ServiceProcess -Service $service) {
        $successCount++
    } else {
        $failCount++
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

# ===== ヘルスチェック =====
if (-not $SkipHealthCheck -and -not $DryRun) {
    Write-Host "`nヘルスチェック実行中..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    $healthyCount = 0
    foreach ($service in $servicesToStart | Where-Object { -not $_.External }) {
        if (Test-ServiceHealth -Port $service.Port) {
            Write-Host "  ✅ $($service.Name)" -ForegroundColor Green
            $healthyCount++
        } else {
            Write-Host "  ⚠️  $($service.Name) (応答なし)" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "ヘルスチェック結果: $healthyCount / $($servicesToStart.Count - ($servicesToStart | Where-Object External).Count) サービスが正常" -ForegroundColor $(if ($healthyCount -eq ($servicesToStart.Count - ($servicesToStart | Where-Object External).Count)) { 'Green' } else { 'Yellow' })
}

# ===== サマリー =====
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              起動完了                                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "成功: $successCount サービス" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "失敗: $failCount サービス" -ForegroundColor Red
}
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "  • ヘルスチェック: python check_services_health.py" -ForegroundColor Gray
Write-Host "  • サービス停止:   .\stop_all_services.ps1" -ForegroundColor Gray
Write-Host ""
