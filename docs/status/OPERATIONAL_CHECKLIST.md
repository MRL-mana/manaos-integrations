# manaOS運用開始チェックリスト
**作成日**: 2025-12-28  
**目的**: 運用開始前の最終確認

---

## 運用開始前の確認項目

### ✅ 1. サーバー状態確認

```bash
# サーバーが起動しているか確認
curl http://localhost:9500/health

# 初期化完了を確認
curl http://localhost:9500/ready

# 進捗確認
curl http://localhost:9500/status
```

**確認ポイント**:
- `/health`: 1秒以内で200を返す
- `/ready`: 200を返し、必須チェック5項目すべてOK
- `/status`: 200を返し、進捗情報が表示される

### ✅ 2. 3連続テストの実行

```bash
python test_3_consecutive.py
```

**確認ポイント**:
- 3回連続で5/5合格（100%）
- すべてのチェックが安定して合格

### ✅ 3. 起動通知の確認

```bash
python test_startup_notification.py
```

**確認ポイント**:
- Slackに起動レポートが送信される
- 必須チェック5項目の状態が表示される

### ✅ 4. 自動再起動の設定（Linux環境）

```bash
# systemd設定を適用
sudo cp manaos_integrations/systemd/manaos-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable manaos-api
sudo systemctl start manaos-api

# ステータス確認
sudo systemctl status manaos-api

# 自動再起動テスト
sudo systemctl stop manaos-api
# 10秒以内に自動再起動されることを確認
sudo systemctl status manaos-api
```

### ✅ 5. 監視設定（オプション）

```bash
# 5分ごとのヘルスチェック（crontab）
*/5 * * * * curl -f http://localhost:9500/health || systemctl restart manaos-api
```

---

## 運用開始後の確認

### 毎日の確認項目

1. **朝のルーチンが実行されているか**
   - Slackに朝の通知が来ているか
   - 今日の予定＋最重要3タスクが表示されているか

2. **夜のルーチンが実行されているか**
   - 日報が自動生成されているか
   - 明日の仕込みが準備されているか

3. **サーバーの状態**
   - `/health`が正常に応答しているか
   - `/ready`が200を返しているか

### 週次の確認項目

1. **監査ログの確認**
   - `logs/llm_routing/audit_YYYYMMDD.jsonl`を確認
   - fallback発動理由を分析

2. **画像ストックの統計**
   - `/api/image/statistics`で統計を確認
   - 成功パターンを分析

3. **未完了タスクの分析**
   - 秘書ルーチンで未完了タスクを確認
   - 自動分析結果を確認

---

## トラブルシューティング

### サーバーが起動しない

1. ポート9500が使用中でないか確認:
   ```bash
   netstat -ano | findstr :9500
   ```

2. ログを確認:
   ```bash
   # systemdの場合
   sudo journalctl -u manaos-api -n 100
   ```

3. 手動起動でエラーを確認:
   ```bash
   python start_server_with_notification.py
   ```

### 初期化が完了しない

1. `/status`で進捗を確認:
   ```bash
   curl http://localhost:9500/status
   ```

2. 失敗しているチェックを確認:
   - `readiness_checks`の`status`が`error`の項目を確認
   - エラーメッセージを確認

3. 個別に統合システムをテスト:
   ```bash
   python check_extension_modules.py
   ```

### 通知が送信されない

1. Slack Webhook URLを確認:
   ```bash
   # .envファイルを確認
   cat .env | grep SLACK_WEBHOOK
   ```

2. 通知システムをテスト:
   ```python
   from notification_system import NotificationSystem
   ns = NotificationSystem()
   ns.send_slack("テスト通知")
   ```

---

## 運用開始の宣言

すべてのチェックリスト項目が完了したら、運用開始を宣言します。

**運用開始条件**:
- ✅ 3連続テスト: 3/3合格
- ✅ 起動通知: 正常に動作
- ✅ 自動再起動: 設定完了（Linux環境の場合）
- ✅ 監視設定: 設定完了（オプション）

---

**チェックリスト完了**: 運用開始準備完了













