# パフォーマンス監視ガイド

ManaOS Integrationsのパフォーマンス監視システムの使い方。

---

## 📊 概要

パフォーマンス監視システムは、すべてのManaOSサービスの以下のメトリクスを収集・監視します：

- **CPU使用率**: サービスごとのCPU消費
- **メモリ使用量**: RAM消費量（MB、%）
- **応答時間**: ヘルスチェックの応答時間（ms）
- **プロセス情報**: プロセス数、スレッド数
- **健全性**: サービスの正常稼働状態

---

## 🚀 クイックスタート

### 1回だけ実行（スナップショット）

```powershell
python performance_monitor.py --once
```

### 継続的監視（60秒間隔）

```powershell
python performance_monitor.py
```

### カスタム間隔（30秒）

```powershell
python performance_monitor.py --interval 30
```

---

## 📋 使用方法

### 基本実行

```powershell
# デフォルト（60秒間隔、継続監視）
cd manaos_integrations
python performance_monitor.py

# 出力例:
# ==========================================================
# ManaOS Performance Summary
# ==========================================================
#
# Service: Unified API (Port 9510)
#   Status: 🟢 HEALTHY
#   CPU: 2.5%
#   Memory: 145.3 MB (1.8%)
#   Response Time: 23.4 ms
#   Processes: 1 | Threads: 8
#
# Service: LLM Routing (Port 5111)
#   Status: 🟢 HEALTHY
#   CPU: 1.2%
#   Memory: 98.7 MB (1.2%)
#   Response Time: 18.9 ms
#   Processes: 1 | Threads: 6
# ...
```

### VSCodeタスクから実行

```json
// .vscode/tasks.json に追加
{
  "label": "ManaOS: パフォーマンス監視",
  "type": "shell",
  "command": "python",
  "args": [
    "${workspaceFolder}/performance_monitor.py",
    "--interval",
    "30"
  ],
  "problemMatcher": [],
  "isBackground": true
}
```

実行:
```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: パフォーマンス監視"
```

---

## 📈 メトリクスの見方

### CPU使用率

```
CPU: 2.5%
```

- **良好**: 0-10%
- **普通**: 10-30%
- **注意**: 30-50%
- **警告**: 50%以上

**対策:**
- 不要な処理を削減
- キャッシング導入
- 非同期処理に変更

### メモリ使用量

```
Memory: 145.3 MB (1.8%)
```

- **良好**: 0-200 MB
- **普通**: 200-500 MB
- **注意**: 500-1000 MB
- **警告**: 1000 MB以上

**対策:**
- メモリリークチェック
- 不要なデータ構造を削除
- ガベージコレクション強制実行

### 応答時間

```
Response Time: 23.4 ms
```

- **優秀**: 0-50 ms
- **良好**: 50-100 ms
- **普通**: 100-200 ms
- **遅い**: 200 ms以上

**対策:**
- データベースクエリ最適化
- キャッシング導入
- 非同期処理化

---

## 📁 メトリクスデータ

### 保存場所

```
manaos_integrations/metrics/
├── metrics_20260207_120000.json
├── metrics_20260207_120100.json
└── metrics_20260207_120200.json
```

### ファイル形式（JSON）

```json
{
  "timestamp": "2026-02-07T12:00:00.123456",
  "metrics": [
    {
      "timestamp": "2026-02-07T12:00:00.123456",
      "service_name": "Unified API",
      "port": 9510,
      "cpu_percent": 2.5,
      "memory_mb": 145.3,
      "memory_percent": 1.8,
      "response_time_ms": 23.4,
      "status_code": 200,
      "is_healthy": true,
      "process_count": 1,
      "thread_count": 8,
      "error_message": null
    }
  ]
}
```

---

## 📊 メトリクス分析

### PowerShellで簡単分析

```powershell
# 最新のメトリクスを取得
$latest = Get-Content (Get-ChildItem metrics\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName | ConvertFrom-Json

# 全サービスのCPU合計
$totalCpu = ($latest.metrics | Measure-Object -Property cpu_percent -Sum).Sum
Write-Host "Total CPU: $totalCpu%"

# 全サービスのメモリ合計
$totalMemory = ($latest.metrics | Measure-Object -Property memory_mb -Sum).Sum
Write-Host "Total Memory: $totalMemory MB"

# 最も遅いサービス
$slowest = $latest.metrics | Sort-Object response_time_ms -Descending | Select-Object -First 1
Write-Host "Slowest: $($slowest.service_name) - $($slowest.response_time_ms)ms"
```

### Pythonで高度な分析

```python
import json
import glob
from pathlib import Path

# すべてのメトリクスを読み込み
metrics_files = sorted(Path("metrics").glob("metrics_*.json"))
all_data = []
for file in metrics_files:
    with open(file) as f:
        data = json.load(f)
        all_data.extend(data["metrics"])

# サービスごとの平均応答時間
from collections import defaultdict
response_times = defaultdict(list)
for metric in all_data:
    if metric["response_time_ms"]:
        response_times[metric["service_name"]].append(metric["response_time_ms"])

for service, times in response_times.items():
    avg = sum(times) / len(times)
    print(f"{service}: {avg:.2f}ms average")
```

---

## 🔔 アラート設定

### PowerShellスクリプトでアラート

```powershell
# alert_on_high_cpu.ps1

$latest = Get-Content (Get-ChildItem metrics\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName | ConvertFrom-Json

foreach ($metric in $latest.metrics) {
    if ($metric.cpu_percent -gt 50) {
        Write-Host "⚠️ HIGH CPU: $($metric.service_name) - $($metric.cpu_percent)%" -ForegroundColor Red
        # メール送信、Slack通知などをここに追加
    }
    
    if ($metric.memory_mb -gt 1000) {
        Write-Host "⚠️ HIGH MEMORY: $($metric.service_name) - $($metric.memory_mb)MB" -ForegroundColor Red
    }
    
    if ($metric.response_time_ms -gt 200) {
        Write-Host "⚠️ SLOW RESPONSE: $($metric.service_name) - $($metric.response_time_ms)ms" -ForegroundColor Yellow
    }
}
```

### タスクスケジューラで定期実行

```powershell
# 毎時実行するスケジュールタスク作成
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Users\mana4\Desktop\manaos_integrations\alert_on_high_cpu.ps1"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "ManaOS Alert Check" -Action $action -Trigger $trigger
```

---

## 🎯 パフォーマンス最適化のヒント

### 1. メモリリークを検出

```python
# 継続的に監視してメモリ増加をチェック
python performance_monitor.py --interval 10
# メモリが右肩上がりに増加していればリーク疑い
```

### 2. CPU使用率が高い場合

```powershell
# どの関数が遅いかプロファイリング
python -m cProfile -o profile.stats your_service.py

# 結果を分析
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### 3. 応答時間が遅い場合

```python
# デバッグログを有効にして詳細確認
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 4. 定期的なクリーンアップ

```powershell
# 古いメトリクスファイルを削除（30日以上前）
Get-ChildItem metrics\*.json | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | Remove-Item
```

---

## 🔧 トラブルシューティング

### Q: `ModuleNotFoundError: No module named 'psutil'`

**A:** psutilをインストール:
```powershell
pip install psutil
```

### Q: メトリクスが表示されない

**A:** サービスが起動しているか確認:
```powershell
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

### Q: 応答時間が常に`None`

**A:** サービスのヘルスチェックエンドポイントを確認:
```powershell
curl http://127.0.0.1:9510/health
curl http://127.0.0.1:5103/health
```

---

## 📊 Grafanaダッシュボード（オプション）

### Prometheusエクスポーターを追加

```python
# prometheus_exporter.py
from prometheus_client import start_http_server, Gauge
import time

# メトリクス定義
cpu_gauge = Gauge('manaos_cpu_percent', 'CPU usage', ['service'])
memory_gauge = Gauge('manaos_memory_mb', 'Memory usage MB', ['service'])
response_time_gauge = Gauge('manaos_response_time_ms', 'Response time', ['service'])

def collect_metrics():
    monitor = PerformanceMonitor()
    metrics = monitor.collect_all_metrics()
    
    for metric in metrics:
        cpu_gauge.labels(service=metric.service_name).set(metric.cpu_percent)
        memory_gauge.labels(service=metric.service_name).set(metric.memory_mb)
        if metric.response_time_ms:
            response_time_gauge.labels(service=metric.service_name).set(metric.response_time_ms)

if __name__ == "__main__":
    start_http_server(8000)  # Prometheusエンドポイント
    while True:
        collect_metrics()
        time.sleep(15)
```

---

## 📚 関連ドキュメント

- **[SYSTEM3_GUIDE.md](SYSTEM3_GUIDE.md)** - 自律監視システム
- **[FAQ.md](FAQ.md#パフォーマンス)** - パフォーマンス関連FAQ
- **[VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)** - 開発環境

---

**最終更新**: 2026年2月7日  
**対応バージョン**: Python 3.11+

