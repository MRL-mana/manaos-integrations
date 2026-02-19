# 次のステップ実行ガイド: Week 1 → Month 1 → Ongoing

**作成日**: 2026-02-18  
**対象期間**: 2026-02-18 から 2026-03-18 以降  
**概要**: ManaOS Home 本番運用の 3 段階フェーズ

---

## 📋 全体構成

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEEK 1: 安定性確認フェーズ                    │
│              (2026-02-18 ~ 2026-02-25, 7 days)                 │
│  目標: 基本的な 24/7 運用の信頼性を検証                         │
│  成果物: health_check_<date>.log, WEEK1_REPORT.md             │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                  MONTH 1: 改修デプロイテスト                     │
│              (2026-02-25 ~ 2026-03-18, 3 weeks)                │
│  目標: 初めてのコード改修を安全にデプロイするプロセスを検証      │
│  成果物: MONTH1_REPORT.md, deploy_<timestamp>.log              │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│              ONGOING: 段階的サービス追加フレームワーク            │
│               (2026-03-18 ~ indefinitely)                       │
│  目標: 新規サービスを 5 段階プロセスで安全に本番追加            │
│  成果物: Service_<name>_REPORT.md, registry.yaml updates        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Quick Start

### Week 1: 準備 (~15分)

```powershell
# 1. health_check スクリプトを Windows Task Scheduler に登録
$taskName = \"ManaOS_Health_Check_Daily\"
$scriptPath = \"C:\\Users\\mana4\\Desktop\\manaos_integrations\\tools\\daily_health_check.ps1\"

# 朝 8:00 に実行するタスクを作成
$trigger = New-ScheduledTaskTrigger -Daily -At 08:00
$action = New-ScheduledTaskAction -Execute \"powershell\" -Argument \"-File $scriptPath\"
$settings = New-ScheduledTaskSettingsSet -RunOnlyIfNetworkAvailable -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings

# 確認
Get-ScheduledTask -TaskName $taskName

# 2. ベースライン測定を実行
.\\daily_health_check.ps1

# 3. Week 1 ガイドをお読みください
explorer.exe C:\\Users\\mana4\\Desktop\\manaos_integrations\\docs\\WEEK1_OPERATIONAL_STABILITY.md
```

### Month 1: 計画 (~1時間)

```powershell
# 1. サンプルマイナー改修を選択
#    推奨: ログローテーション機能の追加
#    ファイル: D:\\ManaHome\\system\\boot\\home_update_v2.py

# 2. ステージング環境のセットアップ
$stagingPath = \"C:\\Users\\mana4\\Desktop\\manaos_integrations\\staging\\log_rotation_test\"
New-Item -ItemType Directory -Path $stagingPath -Force

# 3. Month 1 デプロイテスト計画書を確認
explorer.exe C:\\Users\\mana4\\Desktop\\manaos_integrations\\docs\\MONTH1_DEPLOYMENT_TEST.md

# 4. 改修コードを作成・ステージング環境でテスト
# (詳細は MONTH1_DEPLOYMENT_TEST.md を参照)
```

### Ongoing: 新規サービス追加 (変動)

```powershell
# 1. 新規サービスの要件定義書を作成
# テンプレート: C:\\Users\\mana4\\Desktop\\manaos_integrations\\docs\\ONGOING_SERVICE_ADDITION_FRAMEWORK.md

# 2. Stage 1 (提案・計画) から Stage 5 (運用・監視) まで進める

# 3. テストシナリオを参考に、段階的に検証
# 実装例: C:\\Users\\mana4\\Desktop\\manaos_integrations\\docs\\DEPLOYMENT_TEST_SCENARIOS.md
```

---

## 📂 ファイル構成

```
manaos_integrations/
├── tools/
│   ├── daily_health_check.ps1           ★ Week 1 で毎日実行
│   ├── deploy_to_home.ps1               ★ Month 1/Ongoing で使用
│   └── home_config.yaml
│
└── docs/
    ├── WEEK1_OPERATIONAL_STABILITY.md    ← Day 1 に熟読
    ├── MONTH1_DEPLOYMENT_TEST.md         ← Week 2 開始前に熟読
    ├── ONGOING_SERVICE_ADDITION_FRAMEWORK.md
    └── DEPLOYMENT_TEST_SCENARIOS.md      ← 参考実装例
```

---

## 📅 実行スケジュール (推奨タイムライン)

### Week 1: 2026-02-18 ~ 2026-02-25

| 日付 | タスク | 所要時間 | 担当者 |
|------|--------|---------|--------|
| 02/18 (Tue) | 初期ベースライン測定 | 15 min | Operator |
| 02/19-20 (Wed-Thu) | 毎日 2 回ヘルスチェック + ログ確認 | 5 min × 4 |  |
| 02/21-22 (Fri-Sat) | 自動再起動テスト（オプショナルサービス） | 10 min × 2 |  |
| 02/23-25 (Sun-Tue) | ログ分析・最終レポート作成 | 2 hours | Operator |

**Outcome**: WEEK1_REPORT.md + ✓ 合格基準達成

### Month 1: 2026-02-25 ~ 2026-03-18

| 期間 | フェーズ | タスク | 担当者 |
|------|---------|--------|--------|
| 02/25-03/04 (Week 2-3) | Phase A (準備) | マイナー改修コード作成 + ステージング検証 | Developer |
| 03/04-11 (Week 3-4) | Phase A (続) | デプロイチェックリスト準備 | QA |
| 03/11-12 (Week 4) | Phase B (デプロイ) | ドライラン + バックアップ確認 | Operator |
| 03/15 (Week 4) | Phase B (続) | 本番デプロイ + 検証 | Operator + Developer |
| 03/16-18 (Week 5) | Phase B (続) | ロールバック検証 + 最終レポート | QA |

**Outcome**: MONTH1_REPORT.md + ✓ 全検証合格

### Ongoing (月 1 回)

| 段階 | 所要期間 | 並行タスク |
|------|---------|----------|
| Stage 1-2: 提案・開発 | 1-2 週間 | Week 1 定期ヘルスチェック継続 |
| Stage 3: ステージング | 2 週間 | 日次監視 |
| Stage 4: 本番デプロイ | 1 日 | Monday 13:00-15:00 推奨 |
| Stage 5: 運用 | 2-4 週間 | 日次/週次メトリクス収集 |

**Outcome**: Service_<name>_REPORT.md + registry.yaml 拡張

---

## ✅ チェックリスト

### Week 1 開始前

- [ ] ManaOS Home 本番稼働を確認（16/16 core + 2/2 optional オンライン）
- [ ] WEEK1_OPERATIONAL_STABILITY.md をお読みください
- [ ] daily_health_check.ps1 が実行可能か確認
- [ ] D:\ManaHome\system\runtime\logs\ へのアクセス権確認

### Month 1 開始前

- [ ] Week 1 レポートが ✓ 合格となっていることを確認
- [ ] MONTH1_DEPLOYMENT_TEST.md をお読みください
- [ ] deploy_to_home.ps1 が実行可能か確認
- [ ] マイナー改修候補を決定（推奨: ログローテーション）

### Ongoing 開始前

- [ ] Month 1 レポートが ✓ 合格となっていることを確認
- [ ] ONGOING_SERVICE_ADDITION_FRAMEWORK.md をお読みください
- [ ] 新規サービス要件が明確か確認
- [ ] Stage 1-2 の開発体制が準備できているか確認

---

## 🔧 トラブルシューティング

### Q1: Week 1 ヘルスチェックで 16/16 が 15 以下に低下した

**A**: 以下の対応を実施
```powershell
# Step 1: どのポートが応答しないか特定
$ports = @(9502,5106,5105,5104,5126,5111,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
$failed = @()
foreach ($port in $ports) {
    if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded) {
        $failed += $port
    }
}
Write-Output \"Failed ports: $($failed -join ',')\"

# Step 2: home_update_v2.py の自動再起動を待つ（最大 3 分）
Start-Sleep -Seconds 180

# Step 3: それでも復旧しない場合は home_boot_v2.py を再実行
cd D:\\ManaHome
python system\\boot\\home_boot_v2.py --max-parallel 3
```

### Q2: Month 1 デプロイ時に 9 つの検証項目のうち 8/9 が失敗した

**A**: ロールバック + 原因調査
```powershell
# ロールバック実行
.\\deploy_to_home.ps1 -Rollback

# 直前のバックアップを確認
$backupDir = \"D:\\ManaHome\\system\\backups\\deploy\"
Get-ChildItem $backupDir | Sort-Object LastWriteTime -Descending | Select-Object -First 3

# 失敗ログを確認
Get-Content D:\\ManaHome\\system\\runtime\\logs\\home_update_v2.log | Select-String \"ERROR\" | Select-Object -Last 20

# 原因が「新しいコード」にある場合は、ステージング環境で再テストしてから再デプロイ
```

### Q3: 新規サービスが Stage 3 ステージング中に性能低下を示した

**A**: リソース制限を調整
```powershell
# registry.yaml でメモリ制限を増加
# 変更前: memory_mb: 200
# 変更後: memory_mb: 400

# ステージング環境で再テスト (1-2 日)

# 改善されたら、そのまま本番へ
```

### Q4: Ongoing で新規サービスが本番デプロイ後、オプショナルサービス (8088/8188) が応答しなくなった

**A**: 依存関係の競合を確認
```powershell
# 新規サービスがオプショナルサービスのポートを利用していないか確認
netstat -ano | Select-String \"8088|8188\"

# 新規サービスを停止
Stop-Process -Name python -Force

# オプショナルサービスが復旧したか確認
Start-Sleep -Seconds 30
$test8088 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8088 -WarningAction SilentlyContinue).TcpTestSucceeded
$test8188 = (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -WarningAction SilentlyContinue).TcpTestSucceeded

if (-not $test8088 -or -not $test8188) {
    # 新規サービスが問題：ロールバック実行
    .\\deploy_to_home.ps1 -Rollback
}
```

---

## 📊 メトリクス & 目標

### Week 1 目標

| 指標 | 目標 | 判定基準 |
|------|------|---------|
| Service Availability | >= 99.5% | ✓ 合格 / ✗ 再検査 |
| Error Count | <= 10 件/week | ✓ 合格 / ⚠ 警告 / ✗ 再検査 |
| Auto-Restart Success | 100% | ✓ 合格 / ✗ 再検査 |
| Admin Interaction | 0 回 | ✓ 合格 / ✗ 再検査 |

### Month 1 目標

| 指標 | 目標 | 判定基準 |
|------|------|---------|
| Deployment Success | 100% | ✓ 合格 / ✗ 失敗 |
| Rollback Time | < 5 分 | ✓ 合格 / ⚠ 非効率 |
| Service Recovery | 16/16 in 5 分 | ✓ 合格 / ✗ 失敗 |
| Zero Downtime | Yes | ✓ 合格 / ✗ 失敗 |

### Ongoing 目標

| 指標 | 目標 | 判定基準 |
|------|------|---------|
| New Service Staging | 2 週間エラー < 5 | ✓ 合格 / ✗ 再検査 |
| Memory Stability | < 2MB/日 | ✓ 合格 / ⚠ 留意 / ✗ 再検査 |
| Availability Target | >= 99.5% | ✓ 合格 / ✗ 再検査 |
| Load Test Success | 95% req pass | ✓ 合格 / ✗ 最適化必要 |

---

## 📞 サポート連絡先

| サポート項目 | 連絡先 | 対応時間 |
|------------|--------|--------|
| スクリプト実行エラー | [Developer] | 24/7 |
| サービスダウン | [Operations] | 24/7 |
| デプロイ失敗 | [QA + Developer] | 営業時間 |
| 新規サービス追加 | [Project Lead] | 営業時間 |

---

## 📝 実例リポジトリ

各フェーズの実装例は以下にあります:

- **Week 1 実装例**: [WEEK1_OPERATIONAL_STABILITY.md](WEEK1_OPERATIONAL_STABILITY.md)
- **Month 1 実装例**: [MONTH1_DEPLOYMENT_TEST.md](MONTH1_DEPLOYMENT_TEST.md)
- **Ongoing 実装例**: [ONGOING_SERVICE_ADDITION_FRAMEWORK.md](ONGOING_SERVICE_ADDITION_FRAMEWORK.md)
- **テストシナリオ**: [DEPLOYMENT_TEST_SCENARIOS.md](DEPLOYMENT_TEST_SCENARIOS.md)
- **監視スクリプト**: [daily_health_check.ps1](../tools/daily_health_check.ps1)

---

## 🎯 次のアクション

### すぐにやること (今日)

1. [ ] このドキュメント全体を一読する
2. [ ] WEEK1_OPERATIONAL_STABILITY.md を今週中に熟読
3. [ ] daily_health_check.ps1 を実行テスト

### Week 1 中にやること

4. [ ] 毎日 08:00, 20:00 にヘルスチェック実行
5. [ ] ログを確認し、エラーがないか確認
6. [ ] 週末にレポートを作成

### Month 1 へ進む前に

7. [ ] Week 1 レポートが ✓ となっていることを確認
8. [ ] MONTH1_DEPLOYMENT_TEST.md を熟読
9. [ ] ログローテーション改修コードを開発開始

---

**作成者**: ManaOS Development Team  
**最終更新**: 2026-02-18  
**ステータス**: ✓ 本番運用中  

