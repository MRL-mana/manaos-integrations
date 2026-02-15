# LLMルーティングシステム 自動ヘルスチェック
# 定期的にサービス状態をチェックして、問題があれば通知

Write-Host "=" * 60
Write-Host "LLMルーティングシステム 自動ヘルスチェック"
Write-Host "=" * 60
Write-Host ""

$checkInterval = 60  # 60秒ごとにチェック
$services = @(
    @{
        Name = "LM Studioサーバー"
        Url = "http://127.0.0.1:1234/v1/models"
        Critical = $false
    },
    @{
        Name = "LLMルーティングAPI（Unified API）"
        Url = "http://127.0.0.1:9510/api/llm/health"
        Critical = $true
    },
    @{
        Name = "Unified APIサーバー"
        Url = "http://127.0.0.1:9510/health"
        Critical = $true
    }
)

function Check-Service {
    param(
        [string]$ServiceName,
        [string]$Url,
        [bool]$Critical
    )
    
    try {
        $null = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 3 -ErrorAction Stop
        return @{
            Status = "healthy"
            Message = "正常"
        }
    } catch {
        if ($Critical) {
            return @{
                Status = "critical"
                Message = "⚠️  重要サービスが停止しています"
            }
        } else {
            return @{
                Status = "warning"
                Message = "⚠️  サービスが停止しています（オプション）"
            }
        }
    }
}

Write-Host "自動ヘルスチェックを開始します..." -ForegroundColor Cyan
Write-Host "チェック間隔: $checkInterval 秒" -ForegroundColor Gray
Write-Host "Ctrl+Cで終了" -ForegroundColor Gray
Write-Host ""

$consecutiveFailures = @{}

try {
    while ($true) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $allHealthy = $true
        
        Write-Host "[$timestamp] ヘルスチェック実行中..." -ForegroundColor Yellow
        
        foreach ($service in $services) {
            $result = Check-Service -ServiceName $service.Name -Url $service.Url -Critical $service.Critical
            
            if ($result.Status -eq "healthy") {
                Write-Host "  ✅ $($service.Name): $($result.Message)" -ForegroundColor Green
                $consecutiveFailures[$service.Name] = 0
            } elseif ($result.Status -eq "critical") {
                Write-Host "  ❌ $($service.Name): $($result.Message)" -ForegroundColor Red
                $allHealthy = $false
                
                # 連続失敗回数をカウント
                if (-not $consecutiveFailures.ContainsKey($service.Name)) {
                    $consecutiveFailures[$service.Name] = 0
                }
                $consecutiveFailures[$service.Name]++
                
                # 3回連続失敗したら警告
                if ($consecutiveFailures[$service.Name] -ge 3) {
                    Write-Host "     ⚠️  3回連続で失敗しています。手動確認を推奨します。" -ForegroundColor Yellow
                }
            } else {
                Write-Host "  ⚠️  $($service.Name): $($result.Message)" -ForegroundColor Yellow
            }
        }
        
        if ($allHealthy) {
            Write-Host "  ✅ すべてのサービスが正常です" -ForegroundColor Green
        }
        
        Write-Host ""
        Start-Sleep -Seconds $checkInterval
    }
} catch {
    Write-Host ""
    Write-Host "ヘルスチェックを終了します..." -ForegroundColor Yellow
}



















