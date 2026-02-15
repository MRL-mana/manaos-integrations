# ManaOS統合サービス 一括テストスクリプト

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ManaOS統合サービス 一括テスト" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$services = @(
    @{Name="Unified API Server"; Port=9500; Path="/health"},
    @{Name="Step Deep Research Service"; Port=5121; Path="/health"},
    @{Name="Gallery API Server"; Port=5559; Path="/health"},
    @{Name="System Status API"; Port=5112; Path="/health"},
    @{Name="SSOT API"; Port=5120; Path="/health"},
    @{Name="Service Monitor"; Port=5111; Path="/health"},
    @{Name="Web Voice Interface"; Port=5115; Path="/health"},
    @{Name="Portal Integration API"; Port=5108; Path="/health"},
    @{Name="Slack Integration"; Port=5114; Path="/health"},
    @{Name="Portal Voice Integration"; Port=5116; Path="/health"},
    @{Name="LLM Routing API"; Port=9501; Path="/api/llm/health"}
)

$results = @()
$successCount = 0
$failCount = 0

Write-Host "[テスト開始]" -ForegroundColor Yellow
Write-Host ""

foreach ($service in $services) {
    $url = "http://127.0.0.1:$($service.Port)$($service.Path)"
    Write-Host "テスト中: $($service.Name) ($url)" -ForegroundColor Gray -NoNewline
    
    try {
        $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host " [OK]" -ForegroundColor Green
            $results += @{
                Name = $service.Name
                Port = $service.Port
                Status = "OK"
                Message = "正常に応答"
            }
            $successCount++
        } else {
            Write-Host " [NG] HTTP $($response.StatusCode)" -ForegroundColor Red
            $results += @{
                Name = $service.Name
                Port = $service.Port
                Status = "NG"
                Message = "HTTP $($response.StatusCode)"
            }
            $failCount++
        }
    } catch {
        Write-Host " [NG] 接続失敗" -ForegroundColor Red
        $results += @{
            Name = $service.Name
            Port = $service.Port
            Status = "NG"
            Message = "接続失敗: $($_.Exception.Message)"
        }
        $failCount++
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "テスト結果" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "成功: $successCount / $($services.Count)" -ForegroundColor Green
Write-Host "失敗: $failCount / $($services.Count)" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($failCount -gt 0) {
    Write-Host "[失敗したサービス]" -ForegroundColor Yellow
    foreach ($result in $results) {
        if ($result.Status -eq "NG") {
            Write-Host "  - $($result.Name) (ポート: $($result.Port)): $($result.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
    Write-Host "[対処方法]" -ForegroundColor Yellow
    Write-Host "1. Dockerコンテナが起動しているか確認:" -ForegroundColor White
    Write-Host "   docker-compose -f docker-compose.manaos-services.yml ps" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. サービスを起動:" -ForegroundColor White
    Write-Host "   docker-compose -f docker-compose.manaos-services.yml up -d" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. ログを確認:" -ForegroundColor White
    Write-Host "   docker-compose -f docker-compose.manaos-services.yml logs <service-name>" -ForegroundColor Gray
} else {
    Write-Host "すべてのサービスが正常に動作しています！" -ForegroundColor Green
}

Write-Host ""
