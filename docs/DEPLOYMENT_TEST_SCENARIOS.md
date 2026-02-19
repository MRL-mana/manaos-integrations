# Deployment Test Scenarios
# ファイル: C:\Users\mana4\Desktop\manaos_integrations\docs\DEPLOYMENT_TEST_SCENARIOS.md
# 目的: Month 1 と Ongoing フェーズでのテストシナリオをテンプレート化する

---

## 🧪 Scenario 1: マイナー改修デプロイ (Month 1 推奨)

### シナリオ概要
**改修**: ログローテーション機能の追加  
**ファイル**: home_update_v2.py  
**リスク**: 低 (ログシステムのみに影響)  
**所要時間**: 5分（デプロイ）+ 10分（検証）

### テスト手順

```powershell
# Step 1: 改修コード準備
# C:\\Users\\mana4\\Desktop\\manaos_integrations\\staging\\home_update_v2_modified.py を作成
# オリジナル: 無制限にログ増長
# 改修後: 100MB で自動ローテーション

# Step 2: ドライラン実行
cd C:\\Users\\mana4\\Desktop\\manaos_integrations\\tools
.\\deploy_to_home.ps1 -DryRun

# Expected output:
# ✓ Files to be copied: home_update_v2.py
# ✓ Backup location: D:\\ManaHome\\system\\backups\\deploy\\20260315_134500
# ✓ Health check would test ports: 9502, 5106

# Step 3: 本番デプロイ実行
.\\deploy_to_home.ps1

# Expected output:
# ✓ Deployed 1 file(s): home_update_v2.py
# ✓ Health check PASSED (ports 9502, 5106 responding)
# ✓ Backup created: D:\\ManaHome\\system\\backups\\deploy\\20260315_134500

# Step 4: 検証
# 4-1: コアサービス確認（16/16 オンライン）
$ports = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
$online = 0
foreach ($port in $ports) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
        $client.Close()
    } catch {}
}
Write-Output "Core services online: $online/16"

# 4-2: ログローテーション機能が有効か確認
$homeUpdateCode = Get-Content D:\\ManaHome\\system\\boot\\home_update_v2.py | Select-String \"MAX_LOG_SIZE|rotate\"
Write-Output \"Log rotation code present: $(if ($homeUpdateCode) { 'Yes' } else { 'No' })\"

# 4-3: エラーログ確認
$errors = Get-Content D:\\ManaHome\\system\\runtime\\logs\\home_update_v2.log | Select-String \"ERROR\" | Measure-Object
Write-Output \"Errors since deployment: $($errors.Count)\"

# Step 5: ロールバック検証（デプロイ成功後）
# .\\deploy_to_home.ps1 -Rollback
# (只在必要时执行，此处仅示例)
```

### Result Checklist
- [ ] ドライラン成功
- [ ] デプロイ成功（0/1 ファイル以上）
- [ ] 16/16 コアサービスがオンライン
- [ ] エラー数が 3 件以下
- [ ] ログローテーション機能が有効

---

## 🧪 Scenario 2: 複数ファイル改修デプロイ (Month 2+)

### シナリオ概要
**改修**: API レスポンス最適化（3ファイル）  
**ファイル**:
- home_update_v2.py（ポーリング間隔調整）
- startup_update.ps1（オプショナルブートタイムアウト短縮）
- system/services/registry.yaml（メモリ制限調整）

**リスク**: 中 (複数コンポーネント影響)  
**所要時間**: 10分（デプロイ）+ 30分（検証）

### テスト手順

```powershell
# Step 1: ステージングでの統合テスト
# C:\\Users\\mana4\\Desktop\\manaos_integrations\\staging\\test_api_optimization.ps1

# テスト 1: home_update_v2.py の ポーリング間隔変更
# 元: 5秒 → 新: 10秒
# 確認: ヘルスチェック動作は正常か

# テスト 2: startup_update.ps1 のタイムアウト短縮
# 元: 120秒 → 新: 60秒
# 確認: オプショナルサービス起動は失敗しないか

# テスト 3: registry.yaml のメモリ制限
# 新設定を読み込んだ際、既存プロセスは影響を受けなか

# Step 2: バージョント管理
$timestamp = Get-Date -Format \"yyyyMMdd_HHmmss\"
$backupDir = \"C:\\Users\\mana4\\Desktop\\manaos_integrations\\staging\\backups\\$timestamp\"
New-Item -ItemType Directory -Path $backupDir -Force

Copy-Item D:\\ManaHome\\system\\boot\\home_update_v2.py -Destination $backupDir\\home_update_v2.py.orig
Copy-Item D:\\ManaHome\\system\\boot\\startup_update.ps1 -Destination $backupDir\\startup_update.ps1.orig
Copy-Item D:\\ManaHome\\system\\services\\registry.yaml -Destination $backupDir\\registry.yaml.orig

# Step 3: 変更内容をドキュメント化
$changeLog = @\"
# Changes Summary - $timestamp

## Files Modified
1. home_update_v2.py
   - Line X: Polling interval 5s → 10s
   - Reason: Reduce CPU load
   - Risk: None (async operation)

2. startup_update.ps1
   - Line Y: Optional service timeout 120s → 60s
   - Reason: Faster boot sequence
   - Risk: Low (optional services, best-effort)

3. system/services/registry.yaml
   - Service X: memory_mb 200 → 300
   - Reason: Prevent OOM errors
   - Risk: Low (monitoring in place)
\"@

Set-Content -Path $backupDir\\CHANGES.txt -Value $changeLog

# Step 4: ドライラン
.\\deploy_to_home.ps1 -DryRun

# Expected: 3 ファイルがコピーされることを確認

# Step 5: デプロイ実行
$deployStartTime = Get-Date
.\\deploy_to_home.ps1
$deployTime = (Get-Date) - $deployStartTime

Write-Output \"Deployment completed in: $($deployTime.TotalMinutes) minutes\"

# Step 6: 詳細検証（30分間の監視）
for ($i = 0; $i -lt 30; $i++) {
    # 毎分チェック
    $ports = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
    $online = 0
    foreach ($port in $ports) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
            $client.Close()
        } catch {}
    }
    
    Write-Output \"[$i min] Core services online: $online/16\"
    Start-Sleep -Seconds 60
}

# Step 7: ロールバック準備（トラブル時）
if ($online -lt 15) {
    Write-Host \"⚠️ Service degradation detected. Initiating rollback...\"
    .\\deploy_to_home.ps1 -Rollback
    Start-Sleep -Seconds 30
    
    # ロールバック検証
    $online = 0
    foreach ($port in $ports) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
            $client.Close()
        } catch {}
    }
    
    Write-Output \"After rollback - Core services online: $online/16\"
}
```

### Result Checklist
- [ ] ステージング統合テスト合格
- [ ] 変更ログ作成完了
- [ ] ドライラン成功
- [ ] デプロイ成功（3/3 ファイル）
- [ ] 30 分間の監視completed（16/16 継続）
- [ ] 必要に応じてロールバック動作確認

---

## 🧪 Scenario 3: 新規サービス追加デプロイ (Ongoing)

### シナリオ概要
**新規サービス**: Video Processing Service  
**ポート**: 5131  
**期待機能**: 動画ファイルをアップロード → 処理 → 結果通知  
**リスク**: 中〜高 (新規コンポーネント)  
**デプロイ期間**: 4週間 (Stage 1-4)

### Stage 1: 提案フェーズ (1-3 日)

```markdown
# Service Proposal: Video Processing Service

## Service Details
- Name: video_processor_v1
- Port: 5131
- Team: Media Team
- Timeline: 2026-03-25 to 2026-04-22

## Requirements
- [x] Input: MP4, WebM video files (max 1GB)
- [x] Output: High-quality derivatives (480p, 720p, 1080p)
- [x] Processing time: < 5 minutes per 1GB
- [x] API: REST endpoint POST /process, GET /status

## Dependencies
- ffmpeg library
- 500MB disk space per concurrent job
- Unified API integration (port 9502)

## Risks
| Risk | Level | Mitigation |
|------|-------|-----------|
| High disk I/O | Medium | SSD storage, async processing |
| Long processing time | Medium | Worker thread pool, queue management |
| Failed job recovery | Medium | State persistence, retry logic |
```

### Stage 2: 開発フェーズ (1-2 週間)

```powershell
# ステージング開発構造
manaos_integrations/
└── services/
    └── video_processor_v1/
        ├── main.py          # エントリポイント
        ├── config.yaml      # 設定（ffmpeg path, max_jobs 等）
        ├── requirements.txt # ffmpeg-python, etc
        └── tests/
            ├── test_main.py
            ├── test_api.py
            └── test_integration.py

# Unit tests スケルトン
# C:\\Users\\mana4\\Desktop\\manaos_integrations\\services\\video_processor_v1\\tests\\test_main.py:

import unittest
from main import VideoProcessor

class TestVideoProcessor(unittest.TestCase):
    
    def setUp(self):
        self.processor = VideoProcessor(port=5131, max_workers=2)
    
    def test_init(self):
        self.assertIsNotNone(self.processor)
        self.assertEqual(self.processor.port, 5131)
    
    def test_api_endpoint(self):
        # POST /process で job が登録されるか
        pass
    
    def test_ffmpeg_integration(self):
        # ffmpeg のインストール確認
        pass
    
    def test_max_concurrent_jobs(self):
        # max_workers=2 で 3 個目の job は待機するか
        pass
    
    def test_disk_space_check(self):
        # 十分なディスク空き容量があるか確認
        pass

if __name__ == '__main__':
    unittest.main()
```

### Stage 3: ステージング検証 (2 週間)

```powershell
# Week 1: 基本機能検証
# C:\\Users\\mana4\\Desktop\\manaos_integrations\\staging\\validate_video_processor_week1.ps1

Write-Host \"Week 1: Basic Validation\"

# Test 1: Service startup
$service = Start-Process -FilePath python -ArgumentList \"main.py\" -WorkingDirectory \".\\services\\video_processor_v1\" -PassThru
Start-Sleep -Seconds 3

$portOpen = (Test-NetConnection -ComputerName 127.0.0.1 -Port 5131 -WarningAction SilentlyContinue).TcpTestSucceeded
Write-Host \"Test 1 - Service started: $(if ($portOpen) { 'PASS' } else { 'FAIL' })\"

# Test 2: Health endpoint
try {
    $response = Invoke-WebRequest -Uri \"http://127.0.0.1:5131/health\" -TimeoutSec 5
    Write-Host \"Test 2 - Health endpoint: $(if ($response.StatusCode -eq 200) { 'PASS' } else { 'FAIL' })\"
} catch {
    Write-Host \"Test 2 - Health endpoint: FAIL\"
}

# Test 3: Simple video processing (1MB test file)
$testVideoPath = \"C:\\Users\\mana4\\Desktop\\manaos_integrations\\staging\\test_video_1mb.mp4\"
try {
    $uploadResponse = Invoke-WebRequest -Uri \"http://127.0.0.1:5131/process\" `
                                        -Method POST `
                                        -InFile $testVideoPath `
                                        -TimeoutSec 30
    
    $jobId = ($uploadResponse.Content | ConvertFrom-Json).job_id
    Write-Host \"Test 3 - Video upload: PASS (Job ID: $jobId)\"
    
    # Monitor job status
    Start-Sleep -Seconds 10
    $statusResponse = Invoke-WebRequest -Uri \"http://127.0.0.1:5131/status/$jobId\" -TimeoutSec 5
    $status = ($statusResponse.Content | ConvertFrom-Json).status
    Write-Host \"  Job status: $status\"
} catch {
    Write-Host \"Test 3 - Video upload: FAIL\"
}

# Test 4: Memory usage
$memoryMB = [math]::Round($service.WorkingSet / 1MB)
Write-Host \"Test 4 - Memory usage: ${memoryMB}MB (limit: 500MB)\"

Stop-Process -Id $service.Id -Force

# Week 2: Load & recovery testing
Write-Host \"`nWeek 2: Load & Recovery Testing\"

# Restarting service for week 2 tests...
```

### Stage 4: 本番デプロイ

```powershell
# Final pre-deployment checks

Write-Host \"=== Pre-Deployment Final Verification ===\"

# Check 1: All tests passed in staging
Write-Host \"Check 1: Unit tests - PASS\"
Write-Host \"Check 2: Integration tests - PASS\"
Write-Host \"Check 3: Performance tests - PASS (CPU < 50%, Memory < 300MB)\"
Write-Host \"Check 4: 2-week staging run - PASS (Availability 99.8%)\"

# Check 5: Deployment readiness
$registryEntry = @\"
- name: video_processor_v1
  port: 5131
  startup_command: python D:\\ManaHome\\system\\services\\video_processor_v1\\main.py
  always_on: true
  dependencies:
    - service_name: unified_api
      port: 9502
  resource_limits:
    cpu_percent: 50
    memory_mb: 500
  health_check:
    enabled: true
    endpoint: http://127.0.0.1:5131/health
    interval_seconds: 30
    timeout_seconds: 5
  restart_policy:
    max_retries: 3
    initial_backoff_seconds: 5
    max_backoff_seconds: 300
\"@

# Add to registry
Add-Content -Path D:\\ManaHome\\system\\services\\registry.yaml -Value $registryEntry

# Deploy
.\\deploy_to_home.ps1 -DryRun
# (ドライラン成功後)
.\\deploy_to_home.ps1

# Verify
Start-Sleep -Seconds 10
$newServicePortOpen = (Test-NetConnection -ComputerName 127.0.0.1 -Port 5131 -WarningAction SilentlyContinue).TcpTestSucceeded
Write-Host \"New service online: $(if ($newServicePortOpen) { 'YES' } else { 'NO' })\"

# Verify all 17 services online (16 core + 1 new)
$allPorts = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130,5131)
$online = 0
foreach ($port in $allPorts) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        if ($client.ConnectAsync('127.0.0.1', $port).Wait(900)) { $online++ }
        $client.Close()
    } catch {}
}
Write-Host \"All services online: $online/$($allPorts.Count)\"
```

### Stage 5: 運用監視

```powershell
# C:\\Users\\mana4\\Desktop\\manaos_integrations\\tools\\monitor_video_processor.ps1

# Weekly metrics tracking
$metricsLog = \"D:\\ManaHome\\system\\runtime\\logs\\video_processor_weekly_$(Get-Date -Format 'yyyy-MM-dd').log\"

# Monitor params
$port = 5131
$successThreshold = 95  # %

$failureCount = 0
$successCount = 0
$avgProcessingTime = 0

# Run for 1 week
for ($i = 0; $i -lt 10080; $i += 60) {  # Every hour for 1 week
    
    # Check service health
    $portOpen = (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded
    
    if ($portOpen) {
        $successCount++
    } else {
        $failureCount++
        Write-Host \"⚠️ Service down at $(Get-Date). Checking auto-restart...\"
    }
    
    # Log status
    $status = \"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Status: $(if ($portOpen) { 'UP' } else { 'DOWN' })\"
    Add-Content -Path $metricsLog -Value $status
    
    Start-Sleep -Seconds 3600  # 1 hour
}

# Weekly summary
$uptime = ($successCount / ($successCount + $failureCount)) * 100
Write-Host \"Weekly uptime: $uptime%\"

if ($uptime -lt $successThreshold) {
    Write-Host \"⚠️ Uptime below target. Review logs and consider optimization.\"
}
```

---

## 📊 テスト結果マトリックス

| Scenario | Risk | Duration | Pass Criteria | Frequency |
|----------|------|----------|---------------|-----------|
| Scenario 1 (Log Rotation) | Low | 15 min | 9/9 checks | Every month |
| Scenario 2 (Multi-file) | Medium | 40 min | 16/16 core + no errors | Every 2-3 months |
| Scenario 3 (New Service) | High | 4 weeks | Stage 1-5 all PASS | Quarterly |

