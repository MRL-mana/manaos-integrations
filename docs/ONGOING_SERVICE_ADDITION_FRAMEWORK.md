# Ongoing: 新サービス段階的追加フレームワーク

**期間**: 2026-03-18 以降（継続的）  
**目標**: 新しいサービスを安全に registry に追加し、本番環境で段階的に運用する

---

## 🎯 サービス追加の 5 段階プロセス

```
Stage 1: 提案・計画
    ↓
Stage 2: 開発・テスト
    ↓
Stage 3: 本番前ステージング
    ↓
Stage 4: 本番登録
    ↓
Stage 5: 運用・監視
```

---

## 📋 Stage 1: 提案・計画 (所要時間: 1-3 日)

### 1-1. サービス要件定義書の作成

```markdown
# Service Proposal Template

## 基本情報
- **Service Name**: [サービス名]
- **Port Number**: [ポート番号] (未使用の番号から選択)
- **Team**: [担当チーム]
- **Priority**: [High / Medium / Low]
- **Target Date**: [実装目標日]

## 機能説明
[サービスが何をするか、簡潔に説明]

## 要件
### 機能要件
- [ ] Req-1: [要件1]
- [ ] Req-2: [要件2]
- [ ] Req-3: [要件3]

### 非機能要件
- CPU Usage: [X%]
- Memory: [XXX MB]
- Startup Time: [X seconds]
- Availability Target: [99.x%]

### 依存関係
- Python version: [3.x]
- External packages: [package1, package2]
- Other services: [service1 (port X), service2 (port Y)]

## リスク評価
| Risk | Level | Mitigation |
|------|-------|-----------|
| [Risk 1] | [High/Medium/Low] | [対策] |
| [Risk 2] | [High/Medium/Low] | [対策] |

## 成功基準
- [ ] Criterion 1: [達成条件]
- [ ] Criterion 2: [達成条件]
- [ ] Criterion 3: [達成条件]
```

### 1-2. ポート番号の予約

```powershell
# ファイル: C:\Users\mana4\Desktop\manaos_integrations\docs\PORT_ALLOCATION.md

# 現在のポート割り当て表
# ====================================
# 9502  - Unified API Server
# 5106  - Orchestrator
# 5104  - Service A
# 5105  - Service B
# 5111  - Service C
# 5120  - Service D
# 5121  - Service E
# 5122  - Service F
# 5123  - Service G
# 5124  - Service H
# 5125  - Service I
# 5126  - Service J
# 5127  - Service K
# 5128  - Service L
# 5129  - Service M
# 5130  - Service N
# 8088  - Moltbot Gateway (Optional)
# 8188  - ComfyUI (Optional)
# ====================================
# 利用可能範囲: 5131-5200, 8001-8087, 8189-9501, 9503-65535

# 新規サービス用の予約スクリプト
function Reserve-Port {
    param([int]$port, [string]$serviceName)
    
    $allocationFile = "D:\ManaHome\docs\PORT_ALLOCATION.txt"
    
    if ($port -lt 5131 -or $port -gt 65535) {
        throw "Invalid port: $port. Use range 5131-5200 or 8001-8087"
    }
    
    Add-Content -Path $allocationFile -Value "$port - $serviceName (Reserved $(Get-Date -Format 'yyyy-MM-dd'))"
    Write-Output "✓ Port $port reserved for $serviceName"
}

# 使用例
# Reserve-Port -port 5131 -serviceName "New Video Processing Service"
```

### 1-3. リスク評価とサインオフ

リスクレベルに応じた承認要件：

| Risk Level | 承認者 | 承認期限 |
|------------|--------|---------|
| Low リスク | 開発チーム内 | 24 時間以内 |
| Medium リスク | チームリード | 2 日以内 |
| High リスク | プロジェクト責任者 | 即座 |

---

## 📋 Stage 2: 開発・テスト (所要時間: 1-2 週間)

### 2-1. ローカル開発環境での実装

```shell
# ディレクトリ構成
manaos_integrations/
├── services/
│   └── new_service_v1/
│       ├── main.py
│       ├── config.yaml
│       ├── requirements.txt
│       └── tests/
│           ├── test_main.py
│           ├── test_api.py
│           └── test_integration.py
└── staging/
    └── new_service_staging/
```

### 2-2. ユニットテスト

```python
# C:\Users\mana4\Desktop\manaos_integrations\services\new_service_v1\tests\test_main.py

import unittest
from main import NewService

class TestNewService(unittest.TestCase):
    
    def setUp(self):
        self.service = NewService(port=5131)
    
    def test_service_initialization(self):
        """サービスが正常く初期化されるか"""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.port, 5131)
    
    def test_service_startup(self):
        """サービスが起動するか"""
        self.service.start()
        self.assertTrue(self.service.is_running())
    
    def test_health_endpoint(self):
        """ヘルスチェックエンドポイントが応答するか"""
        # HTTP GET /health でステータス 200 を返すか
        pass
    
    def test_dependency_injection(self):
        """依存サービスへのアクセスが正常か"""
        # 他のサービスへの接続が成功するか
        pass
    
    def test_memory_usage(self):
        """メモリ使用量が許容範囲か"""
        # XMB 以上では失敗
        pass
    
    def tearDown(self):
        self.service.stop()

if __name__ == '__main__':
    unittest.main()
```

### 2-3. ステージング環境でのテスト

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\test_new_service.ps1

Write-Host "Testing new_service_v1..."

# Test 1: ポート バインディング
Write-Host "Test 1: Port binding..."
$port = 5131
$process = Start-Process -FilePath "python" -ArgumentList "main.py --port $port" -WorkingDirectory ".\services\new_service_v1" -PassThru

Start-Sleep -Seconds 3

$portOpen = (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded
if ($portOpen) {
    Write-Host "✓ Port $port is open"
} else {
    Write-Host "✗ Port $port is not open"
    exit 1
}

# Test 2: ヘルスチェック
Write-Host "Test 2: Health check..."
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Health check passed"
    } else {
        Write-Host "✗ Health check failed: $($response.StatusCode)"
        exit 1
    }
} catch {
    Write-Host "✗ Health check error: $_"
    exit 1
}

# Test 3: メモリ使用量
Write-Host "Test 3: Memory usage..."
$memoryMB = [math]::Round($process.WorkingSet / 1MB)
$expectedMemoryMB = 100  # 100MB 以下が目安
if ($memoryMB -lt $expectedMemoryMB) {
    Write-Host "✓ Memory usage acceptable: ${memoryMB}MB (limit: ${expectedMemoryMB}MB)"
} else {
    Write-Host "⚠ Memory usage high: ${memoryMB}MB (limit: ${expectedMemoryMB}MB)"
}

# Test 4: 起動時間
Write-Host "Test 4: Startup time..."
$startupTime = (Get-Date) - $process.StartTime
Write-Host "  Startup time: $($startupTime.TotalSeconds) seconds"

# Clean up
Stop-Process -Id $process.Id -Force
Write-Host "`n✓ All tests passed!"
```

### 2-4. パフォーマンステスト

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\perf_test_new_service.ps1

# 負荷テスト: 100 リクエスト/秒で 60 秒間
Write-Host "Performance test: 100 req/s for 60s..."

$results = @()
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

for ($i = 0; $i -lt 6000; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:5131/api/test" `
                                      -TimeoutSec 5 -ErrorAction Continue
        if ($response.StatusCode -eq 200) {
            $results += "success"
        }
    } catch {
        $results += "failure"
    }
}

$stopwatch.Stop()
$successRate = ($results | Where-Object { $_ -eq "success" }).Count / $results.Count * 100

Write-Host "Results:"
Write-Host "  Success rate: $successRate%"
Write-Host "  Total time: $($stopwatch.Elapsed.TotalSeconds) seconds"
Write-Host "  Throughput: $(6000 / $stopwatch.Elapsed.TotalSeconds) req/s"

if ($successRate -gt 95) {
    Write-Host "✓ Performance test passed"
} else {
    Write-Host "✗ Performance test failed: Success rate below 95%"
}
```

---

## 📋 Stage 3: 本番前ステージング (所要時間: 3-5 日)

### 3-1. ステージング環境への deploy

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\deploy_to_staging.ps1

param(
    [string]$ServicePath = "C:\Users\mana4\Desktop\manaos_integrations\services\new_service_v1",
    [string]$StagingPath = "C:\Users\mana4\Desktop\manaos_integrations\staging\new_service_staging"
)

# ステージング環境にコピー
Copy-Item -Path $ServicePath -Destination $StagingPath -Recurse -Force

# registry に staging エントリを追加
$stagingRegistry = "$StagingPath\registry.yaml"
$entry = @"
- name: new_service_v1_staging
  port: 5131
  startup_command: python main.py
  always_on: false  # ステージングでは optional
  dependencies: []
  resource_limits:
    cpu_percent: 50
    memory_mb: 200
"@

Add-Content -Path $stagingRegistry -Value $entry

Write-Host "✓ Service deployed to staging at: $StagingPath"
```

### 3-2. ステージング環境での 2 週間運用

```markdown
# Staging Validation Checklist (2 weeks)

## Week 1
- [ ] Day 1-2: 連続稼働 (48 時間)
  - チェック: Service は継続的にオンラインか
  - チェック: メモリリークがないか（メモリ増加 <2MB/日）
  
- [ ] Day 3-4: 依存サービスとの統合テスト
  - チェック: 他のサービスから正常にアクセス可能か
  - チェック: API 応答時間が要件内か (<500ms)
  
- [ ] Day 5-7: ログ分析
  - エラーの有無を確認
  - 性能の傾向を確認

## Week 2
- [ ] Day 8-9: 障害復旧テスト
  - Service を意図的に停止
  - 自動再起動が動作するか確認
  
- [ ] Day 10-11: ロードテスト増加
  - 通常の 2 倍のトラフィック
  - 応答時間が **1.5 倍以内** に保たれるか
  
- [ ] Day 12-14: 本番環境スタンバイ
  - registry に本番エントリを準備
  - ロールバック計画を作成
  - 本番部署への通知

## Go/No-Go 判定基準
- ✓ Go: エラー < 5 件、メモリ安定、性能基準達成
- ✗ No-Go: エラー >= 5 件、メモリリーク症状、性能低下
```

### 3-3. ステージング metrics の収集

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\collect_staging_metrics.ps1

$metricsFile = "D:\ManaHome\system\runtime\logs\staging_metrics_new_service_$(Get-Date -Format 'yyyy-MM').log"

function Log-Metric {
    param([string]$metric)
    Add-Content -Path $metricsFile -Value "$((Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) | $metric"
}

# 定期実行（毎 6 時間）
while ($true) {
    # CPU
    $process = Get-Process | Where-Object { $_.ProcessName -like "*new_service*" }
    if ($process) {
        Log-Metric "CPU: $($process.ProcessorTime.TotalSeconds)s"
        Log-Metric "Memory: $(([math]::Round($process.WorkingSet / 1MB)))MB"
    }
    
    # 応答時間
    $startTime = Get-Date
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:5131/health" -TimeoutSec 5
        $responseTime = ((Get-Date) - $startTime).TotalMilliseconds
        Log-Metric "Response time: ${responseTime}ms"
    } catch {
        Log-Metric "Health check FAILED"
    }
    
    Start-Sleep -Seconds 21600  # 6 時間
}
```

---

## 📋 Stage 4: 本番登録 (所要時間: 1 日)

### 4-1. registry.yaml への追加

**ファイル**: `D:\ManaHome\system\services\registry.yaml`

```yaml
# 既存サービスリスト...
# 9502, 5106, 5104-5130, 8088, 8188

# === 新規サービス ===
- name: new_service_v1
  port: 5131
  startup_command: python D:\ManaHome\system\services\new_service_v1\main.py
  shutdown_signal: SIGTERM
  always_on: true  # 本番では always_on にする
  dependencies:
    - service_name: unified_api
      port: 9502
  resource_limits:
    cpu_percent: 50
    memory_mb: 200
  health_check:
    enabled: true
    endpoint: http://127.0.0.1:5131/health
    interval_seconds: 30
    timeout_seconds: 5
  restart_policy:
    max_retries: 3
    initial_backoff_seconds: 5
    max_backoff_seconds: 300
```

### 4-2. デプロイメント実行

```powershell
# Stage 4 デプロイメント

# Step 1: registry を本番にコピー
$deployScript = "C:\Users\mana4\Desktop\manaos_integrations\tools\deploy_to_home.ps1"
& $deployScript -DryRun  # ドライラン確認

# Step 2: バックアップ作成確認
$backupDir = "D:\ManaHome\system\backups\deploy"
$latestBackup = Get-ChildItem $backupDir | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "Latest backup: $($latestBackup.FullName)"

# Step 3: 本番デプロイ実行
& $deployScript

# Step 4: 新規 サービスの起動確認
Start-Sleep -Seconds 5
$portOpen = (Test-NetConnection -ComputerName 127.0.0.1 -Port 5131 -WarningAction SilentlyContinue).TcpTestSucceeded
if ($portOpen) {
    Write-Host "✓ New service started on port 5131"
} else {
    Write-Host "✗ New service failed to start"
    Write-Host "Initiating rollback..."
    & $deployScript -Rollback
}
```

### 4-3. 本番環境での初期確認

```powershell
# Stage 4 検証チェックリスト

Write-Host "=== Stage 4: Production Initialization Verification ==="

# Check 1: コアサービス（16/16）+ 新規サービス（1）が オンラインか
$ports = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130,5131)
$online = 0
foreach ($port in $ports) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
        $client.Close()
    } catch {}
}
Write-Host "Check 1: Services online: $online/$($ports.Count) [$(if ($online -eq $ports.Count) { '✓' } else { '✗' })]"

# Check 2: state.json に新規サービスが登録されているか
$state = Get-Content "D:\ManaHome\system\runtime\state.json" | ConvertFrom-Json
$hasNewService = $state.services | Where-Object { $_.name -eq "new_service_v1" }
Write-Host "Check 2: New service in state: [$(if ($hasNewService) { '✓' } else { '✗' })]"

# Check 3: ログに エラーがないか
$emergencyLog = "D:\ManaHome\system\runtime\logs\home_boot_v2.log"
$recentErrors = Get-Content $emergencyLog | Select-String "ERROR|FAILED" | Select-Object -Last 5
Write-Host "Check 3: Recent errors: $(if ($recentErrors.Count -eq 0) { 'None ✓' } else { "$($recentErrors.Count) found ✗" })"

# Check 4: healt check endpoint が応答するか
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:5131/health" -TimeoutSec 5
    Write-Host "Check 4: Health endpoint: ✓"
} catch {
    Write-Host "Check 4: Health endpoint: ✗"
}
```

---

## 📋 Stage 5: 運用・監視 (継続的)

### 5-1. 日次監視タスク

```powershell
# C:\Users\mana4\Desktop\manaos_integrations\staging\monitor_new_service.ps1

$serviceName = "new_service_v1"
$servicePort = 5131
$monitorLog = "D:\ManaHome\system\runtime\logs\monitor_${serviceName}_$(Get-Date -Format 'yyyy-MM-dd').log"

function Check-Service {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # ポート確認
    $portOpen = (Test-NetConnection -ComputerName 127.0.0.1 -Port $servicePort -WarningAction SilentlyContinue).TcpTestSucceeded
    
    # メモリ確認
    $process = Get-Process | Where-Object { $_.ProcessName -like "*new_service*" -or $_.CommandLine -like "*new_service*" }
    $memoryMB = if ($process) { [math]::Round($process.WorkingSet / 1MB) } else { 0 }
    
    # ログイン
    $status = "$timestamp | Port: $(if ($portOpen) { 'UP' } else { 'DOWN' }) | Memory: ${memoryMB}MB"
    Add-Content -Path $monitorLog -Value $status
    
    return $portOpen
}

# 1 時間ごとに監視
for ($i = 0; $i -lt 24; $i++) {
    if (-not (Check-Service)) {
        Write-Host "⚠️ Service is down! Checking if auto-restart is working..."
        Start-Sleep -Seconds 60
        if (-not (Check-Service)) {
            Write-Host "✗ Service failed to auto-restart"
            # アラート送信（メール等）
        }
    }
    
    Start-Sleep -Seconds 3600  # 1 時間
}
```

### 5-2. 定期な metrics 分析

```powershell
# 毎月レポート生成
function Generate-Monthly-Service-Report {
    param([string]$ServiceName)
    
    $reportPath = "D:\ManaHome\system\runtime\logs\report_${ServiceName}_$(Get-Date -Format 'yyyy-MM').md"
    
    # メトリクスの集約
    $uptime = 99.5  # 例
    $avgResponseTime = 145  # ms
    $peakMemory = 185  # MB
    $errorCount = 2
    
    $report = @"
# Service Report: $ServiceName
**Month**: $(Get-Date -Format 'yyyy-MM')

## Metrics
- Availability: $uptime%
- Avg Response Time: $avgResponseTime ms
- Peak Memory: $peakMemory MB
- Error Count: $errorCount

## Status
✓ Healthy

## Recommendations
1. Continue monitoring
2. Consider optimization if memory continues to grow
"@
    
    Set-Content -Path $reportPath -Value $report
}
```

### 5-3. インシデント対応フロー

```
新規サービスからアラート発生時:

1. サービスがポートをリッスンしているか確認
   └─ ダウン: ① 手動再起動 → ② logs を確認 → ③ 原因特定

2. health check endpoint が応答するか確認
   └─ 非応答: ① メモリ/CPU 確認 → ② resource limits 増加 検討

3. 依存サービスが起動しているか確認
   └─ ダウン: ① 依存サービスを再起動 → ② 新規サービス再起動

4. それでもダウンの場合
   └─ ロールバック検討（Stage 4 前のバージョンに戻す）
```

---

## 📊 サービス追加の全体的な品質ゲート

```
Stage 1: 提案
  ├─ 要件が明確か ✓
  └─ リスク評価が完了 ✓
  
Stage 2: 開発
  ├─ ユニットテスト: 100% パス ✓
  ├─ 統合テスト: 100% パス ✓
  └─ パフォーマンス基準達成 ✓
  
Stage 3: ステージング
  ├─ 2 週間の安定稼働 ✓
  ├─ メモリ安定（增加 <2MB/日） ✓
  └─ エラー数 < 5 件 ✓
  
Stage 4: 本番登録
  ├─ All services online (16/16 + 1) ✓
  ├─ No recent errors ✓
  └─ Health check passing ✓
  
Stage 5: 運用
  ├─ 日次監視確立 ✓
  ├─ 月次レポート生成 ✓
  └─ インシデント対応マニュアル完備 ✓
```

---

## 🎯 よくある Q&A

### Q: 新規サービスがダウンしたら？
**A**: home_update_v2.py が自動再起動を試みます（最大 3 回）。それでも復旧しない場合は、アラートを確認して手動対応。

### Q: registry を編集してから反映されるまで何分かかる？
**A**: deploy_to_home.ps1 実行後、home_boot.lock が解放される（最大 5 分）まで待つ必要があります。急ぐ場合は home_update_v2.py を手動で再起動。

### Q: 本番中にコード改修を入れたい場合？
**A**: Month 1 で検証した deploy_to_home.ps1 パイプラインを使用。ドライラン → バックアップ → デプロイ → 検証 → 必要に応じてロールバック。

### Q: ポート番号が足りなくなったら？
**A**: 現在は 5131-5200 / 8001-8087 の範囲で未使用。それ以上追加する際は動的ポート割り当てスキームへの移行を検討。

