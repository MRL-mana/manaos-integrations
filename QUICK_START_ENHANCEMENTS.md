# 新ツール・新システム クイックスタートガイド

**作成日**: 2026年1月3日

---

## 🚀 導入完了ツール一覧

### ✅ 実装完了・動作確認済み

1. **Device Health Monitor** - デバイス健康状態監視
2. **Google Drive Sync Agent** - ファイル自動同期
3. **Notification Hub Enhanced** - 統合通知システム
4. **Device Monitor with Notifications** - 通知機能付き監視

---

## 📖 クイックスタート

### 1. Device Health Monitor

**起動方法**:
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python device_health_monitor.py
```

**設定ファイル**: `device_health_config.json`（初回実行時に自動作成）

**機能**:
- 全デバイスの健康状態を監視
- CPU、メモリ、ディスク使用率の監視
- アラート生成

### 2. Device Monitor with Notifications（推奨）

**起動方法**:
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_device_monitoring.ps1
```

または:
```powershell
python device_monitor_with_notifications.py
```

**機能**:
- Device Health Monitorの全機能
- 自動通知機能（Slack/Telegram/メール）
- アラート発生時の自動通知

**設定ファイル**: 
- `device_health_config.json`（デバイス設定）
- `notification_hub_enhanced_config.json`（通知設定）

### 3. Google Drive Sync Agent

**起動方法**:
```powershell
python google_drive_sync_agent.py
```

**初回設定**:
1. `google_drive_sync_config.json`が自動作成されます
2. 同期ルールを設定してください
3. Google Drive認証情報を設定してください

**機能**:
- ファイル変更の自動検知
- Google Driveへの自動同期
- 同期状態の管理

---

## ⚙️ 設定方法

### Device Health Monitor設定

`device_health_config.json`を編集:

```json
{
  "devices": [
    {
      "name": "ManaOS",
      "type": "manaos",
      "api_endpoint": "http://localhost:5106/health"
    },
    {
      "name": "Mothership",
      "type": "mothership",
      "api_endpoint": null
    }
  ],
  "check_interval": 30,
  "alert_thresholds": {
    "cpu_warning": 80.0,
    "cpu_critical": 95.0,
    "memory_warning": 85.0,
    "memory_critical": 95.0,
    "disk_warning": 85.0,
    "disk_critical": 95.0
  }
}
```

### Notification Hub Enhanced設定

`notification_hub_enhanced_config.json`を編集:

```json
{
  "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "password": "your_password",
    "from_address": "your_email@gmail.com",
    "to_addresses": ["recipient@example.com"]
  }
}
```

### Google Drive Sync Agent設定

`google_drive_sync_config.json`を編集:

```json
{
  "credentials_path": "credentials.json",
  "token_path": "token.json",
  "sync_rules": [
    {
      "local_path": "./backups",
      "drive_folder": "ManaOS_Backups",
      "sync_mode": "bidirectional",
      "include_patterns": ["*"],
      "exclude_patterns": [".git", "__pycache__", "*.pyc"]
    }
  ],
  "sync_interval": 60,
  "auto_sync": true
}
```

---

## 🔧 トラブルシューティング

### Device Health Monitorがリモートデバイスに接続できない

**原因**: API Gatewayが起動していない

**解決方法**:
1. 各デバイスのAPI Gatewayを起動
2. Tailscale接続を確認
3. ファイアウォール設定を確認

### Google Drive Sync Agentが動作しない

**原因**: 認証情報が設定されていない

**解決方法**:
1. Google Cloud Consoleで認証情報を取得
2. `credentials.json`を配置
3. 初回実行時に認証を完了

### 通知が送信されない

**原因**: 通知設定が不完全

**解決方法**:
1. `notification_hub_enhanced_config.json`を確認
2. Webhook URLやBot Tokenが正しいか確認
3. ログを確認してエラーを特定

---

## 📊 動作確認

### Device Health Monitorテスト
```powershell
python device_health_monitor.py
```

期待される出力:
- デバイスの健康状態がJSON形式で表示される
- 正常なデバイスは"healthy"ステータス
- オフラインのデバイスは"offline"ステータス

### Notification Hub Enhancedテスト
```powershell
python notification_hub_enhanced.py
```

期待される動作:
- テスト通知が送信される
- 統計情報が表示される

### 統合テスト
```powershell
python device_monitor_with_notifications.py
```

期待される動作:
- 監視が開始される
- アラート発生時に通知が送信される

---

## 🎯 次のステップ

1. **通知設定の完了**
   - Slack Webhook URLを設定
   - Telegram Bot Tokenを設定（オプション）
   - メール設定を設定（オプション）

2. **Google Drive認証の設定**
   - Google Cloud Consoleで認証情報を取得
   - `credentials.json`を配置

3. **自動起動設定（オプション）**
   - Windowsタスクスケジューラーに登録
   - システム起動時に自動起動

4. **デバイスAPI Gateway起動**
   - X280 API Gateway起動
   - Konoha Server API Gateway起動
   - Pixel 7 API Gateway起動

---

## 📝 注意事項

1. **Google Drive認証**: Google Drive Sync Agentを使用するには、Google Cloud Consoleで認証情報を取得する必要があります
2. **ネットワーク接続**: リモートデバイスの監視には、Tailscale経由の接続が必要です
3. **API Gateway**: 各デバイスのAPI Gatewayが起動している必要があります

---

**最終更新**: 2026年1月3日

