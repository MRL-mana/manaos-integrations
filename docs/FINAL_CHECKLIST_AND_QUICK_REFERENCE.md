# ManaOS Home: 3フェーズ運用実行計画 - 最終チェックリスト

**準備完了日**: 2026-02-18  
**実行開始**: 本日から Week 1 開始可能  
**総ドキュメント数**: 6 ファイル  
**自動化スクリプト**: 3 個準備済み  

---

## ✅ 本日 (2026-02-18) 実施完了項目

### ドキュメント準備
- [x] WEEK1_OPERATIONAL_STABILITY.md - 7日間の詳細ガイド
- [x] MONTH1_DEPLOYMENT_TEST.md - デプロイテスト計画（3週間）
- [x] ONGOING_SERVICE_ADDITION_FRAMEWORK.md - 新規サービス5段階プロセス
- [x] DEPLOYMENT_TEST_SCENARIOS.md - 実装例とシナリオ集
- [x] NEXT_STEPS_EXECUTION_GUIDE.md - 統合実行ガイド
- [x] WEEK1_READY_FOR_EXECUTION.md - 準備完了レポート（本ファイル）

### システム検証
- [x] 16/16 コアサービス確認: **ONLINE**
- [x] 8088 (Gateway) 確認: **ONLINE**
- [x] 8188 (ComfyUI) 確認: **ONLINE**
- [x] Windows Startup 登録: **ACTIVE**
- [x] ディスク容量確認: **133GB FREE**

### 自動化セットアップ
- [x] daily_health_check_v2.ps1 作成・テスト実行済み
- [x] Windows Task Scheduler 登録: **08:00 毎日実行**
- [x] deploy_to_home.ps1 動作確認
- [x] home_config.yaml 設定確認
- [x] バックアップディレクトリ作成: **D:\ManaHome\system\backups\deploy\**

---

## 📅 Week 1 運用安定性確認 (2026-02-18 ~ 2026-02-25)

### 日次実行タスク

**毎日 08:00**: 自動実行 (Task Scheduler)
```
✓ 自動実行されます - 手動操作不要
```

**毎日 20:00**: 手動実行推奨
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\mana4\Desktop\manaos_integrations\tools\daily_health_check_v2.ps1"
```

### 週別タスク

#### **Week 1: Day 1-3 (02/18-20)**
- [x] Day 1: ベースライン測定 ✅ 本日完了
- [ ] Day 2-3: 毎日 2回ヘルスチェック ⏳ 実施中

**チェック内容** (9項目):
1. Home ディレクトリ利用可能
2. Core Services (16/16) オンライン
3. Optional Services (8088, 8188) 応答
4. ログファイル存在確認
5. state.json 更新状態
6. ディスク容量 (>10GB)
7. 最近のエラー数 (<5件)
8. Pythonプロセスメモリ (<500MB)
9. Windows Startup 登録確認

#### **Week 1: Day 4-5 (02/21-22)**
- [ ] オプショナルサービス自動再起動テスト
- [ ] ログファイル増長監視

**テスト内容**:
```powershell
# Port 8088 を停止してテスト
$process = Get-Process | Where-Object { $_.Name -like "*gateway*" }
if ($process) {
    Stop-Process -Id $process.Id -Force
    Start-Sleep -Seconds 300
    # 5分後に自動復旧されたか確認
}
```

#### **Week 1: Day 6-7 (02/23-25)**
- [ ] ログファイル分析
- [ ] エラーパターン確認
- [ ] 最終レポート作成 (WEEK1_REPORT.md)

---

## 🔵 Week 1 合格基準

```
✅ PASS 条件 (すべて満たす必要あり):

1. Service Availability: >= 99.5%
   現在: 16/16 (100%) ✓

2. Error Count: <= 10 件/week
   現在: 21 件 (Day 1 のため要注視) ⚠

3. Auto-Restart Success: 100%
   現在: テスト待機 ⏳

4. Admin Interaction: 0 回
   現在: 0 回 ✓

5. Windows Startup: Active
   現在: 登録済み ✓
```

**判定方法**:
- すべて ✓: **Go → Month 1**
- ⚠ が 1-2個: **Extended Week 1** (1週間追加)
- ❌ が 1個以上: **Re-assess** (原因調査)

---

## 🟡 Month 1: 初めての改修デプロイテスト

### 準備状況
- [x] デプロイメントパイプライン完成
- [x] マイナー改修候補: **ログローテーション機能**
- [x] ステージング環境: **準備待機**
- [x] デプロイ前チェックリスト: **ドキュメント内に表記**

### 実行予定
1. **Week 2-3 (02/25 ~ 03/04)**: Phase A 準備
   - マイナー改修コード開発
   - ステージング環境でテスト

2. **Week 3-4 (03/04 ~ 03/11)**: Phase A 完了
   - デプロイメント前チェックリスト準備
   - 9つの検証項目準備

3. **Week 4 (03/11 ~ 03/15)**: Phase B デプロイ
   - ドライラン実行 (03/11-12)
   - 本番デプロイ (03/15)
   - デプロイ後検証 (03/15-16)

4. **Week 5 (03/16 ~ 03/18)**: Phase B 完了
   - ロールバック検証
   - 最終レポート作成 (MONTH1_REPORT.md)

### 必要な進捗確認

Week 1 終了時に以下が確認できたら Month 1 へ進可:
- [ ] Week 1 レポート: ✓ PASS 判定
- [ ] システム状態: 安定稼働 16/16
- [ ] エラー: 5件以下
- [ ] ドキュメント: 完全に読了

---

## 🟢 Ongoing: 新規サービス段階的追加

### 準備状況
- [x] 5段階プロセス: **ドキュメント完成**
- [x] ポート予約管理: **5131-5200 範囲準備**
- [x] 新規サービステンプレート: **ONGOING_SERVICE_ADDITION_FRAMEWORK.md に記載**

### 実行開始時期
**2026-03-18 以降** (Month 1 完了後)

### 月 1 回の実行パターン

```
Stage 1: 提案 (1-3 日)
  ↓
Stage 2: 開発・テスト (1-2 週)
  ↓
Stage 3: ステージング (2 週)
  ↓
Stage 4: 本番登録 (1 日)
  ↓
Stage 5: 運用・監視 (2-4 週)
```

---

## 📚 参照ドキュメント

### Quick Reference
| 用途 | ファイル | 場所 |
|------|---------|------|
| Week 1 実施 | WEEK1_OPERATIONAL_STABILITY.md | docs/ |
| Month 1 計画 | MONTH1_DEPLOYMENT_TEST.md | docs/ |
| 継続追加 | ONGOING_SERVICE_ADDITION_FRAMEWORK.md | docs/ |
| 全体ガイド | NEXT_STEPS_EXECUTION_GUIDE.md | docs/ |
| テスト例 | DEPLOYMENT_TEST_SCENARIOS.md | docs/ |

### ログファイル位置
```
Daily logs: D:\ManaHome\system\runtime\logs\health_check_YYYY-MM-DD.log
Boot logs:  D:\ManaHome\system\runtime\logs\home_boot_v2.log
Update logs: D:\ManaHome\system\runtime\logs\home_update_v2.log
```

---

## 🛠️ トラブル時の対応

### よくある問題と解決方法

#### 問題1: 16/16 が達成できない
```powershell
# 再起動コマンド
cd D:\ManaHome
python system\boot\home_boot_v2.py --max-parallel 3
```

#### 問題2: ヘルスチェック実行忘れ
```powershell
# 任意の時刻に手動実行可能
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\mana4\Desktop\manaos_integrations\tools\daily_health_check_v2.ps1"
```

#### 問題3: Task Scheduler の確認
```powershell
# タスクが登録されているか確認
Get-ScheduledTask -TaskName "ManaOS_Health_Check_Daily"

# タスク実行履歴を確認
Get-ScheduledTaskInfo -TaskName "ManaOS_Health_Check_Daily"
```

#### 問題4: ログファイルが肥大化
```powershell
# ログサイズ確認
Get-Item "D:\ManaHome\system\runtime\logs\home_*.log" | Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB)}}
```

---

## 📊 進捗ダッシュボード

### 現在のステータス (2026-02-18 06:44)

```
┌─────────────────────────────────────────────────────┐
│ Week 1: 運用安定性確認                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                    │
│ Day 1/7:     ████░░░░░░░░░░░░░░░░  14%            │
│ Baseline:    ✓ Complete                            │
│ Automation:  ✓ Task Scheduler Ready                │
│ Documentation: ✓ All Complete                      │
│                                                    │
│ Health Status: 7/9 ✓ (78%)                        │
│ Core Services: 16/16 ✓ (100%)                     │
│ Optional: 8088✓ 8188✓ (100%)                      │
│                                                    │
├─────────────────────────────────────────────────────┤
│ Month 1: デプロイテスト             NEXT            │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Status: ⏳ Waiting for Week 1 completion           │
│ Target: 2026-02-25 Start                          │
│                                                    │
├─────────────────────────────────────────────────────┤
│ Ongoing: 新規サービス追加         Q2以降           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Status: ⏳ Waiting for Month 1 completion          │
│ Target: 2026-03-18 Start                          │
│                                                    │
└─────────────────────────────────────────────────────┘
```

---

## 📞 サポート連絡先

| 項目 | 連絡先 | 対応時間 |
|------|--------|--------|
| スクリプトエラー | [Developer] | 24/7 |
| システムダウン | [Operations] | 24/7 |
| デプロイ失敗 | [QA + Dev] | 営業時間 |
| 新規サービス | [Project Lead] | 営業時間 |

---

## 🎯 まとめ: 今からやること

### 🔴 今すぐ (今日中)
1. [ ] このチェックリストを確認 ✅
2. [ ] 夜 20:00 に手動でヘルスチェック実行
3. [ ] ログが記録されているか確認

### 🟡 明日から (Week 1)
1. [ ] 毎日 08:00 自動実行を確認
2. [ ] Day 4-5: 再起動テストを実施
3. [ ] Day 6-7: ログ分析と最終レポート作成

### 🟢 2月末 (Month 1 へ移行)
1. [ ] Week 1 レポート提出
2. [ ] Month 1 デプロイ開始準備

---

## ✨ 完成度チェック

- [x] ドキュメント: **100%** (6 ファイル完成)
- [x] スクリプト: **100%** (3 個準備済み)
- [x] システム検証: **78%** (7/9 項目 PASS)
- [x] 自動化: **100%** (Task Scheduler 登録済み)
- [x] 実行環境: **100%** (すべて準備完了)

---

**準備状況**: ✅ **すべて完了 - Week 1 実行開始可能**

このチェックリストを保存して、Week 1 期間中に参照してください。

