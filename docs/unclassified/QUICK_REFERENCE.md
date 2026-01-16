# クイックリファレンス

**最終更新**: 2026年1月3日

---

## 🚀 起動コマンド

### 監視システム起動
```powershell
.\start_device_monitoring.ps1
```

### 全システム起動（対話型）
```powershell
.\start_all_systems.ps1
```

### オプションシステム起動
```powershell
.\start_all_optionals.ps1
```

---

## ⚙️ 設定コマンド

### 通知設定
```powershell
.\setup_notifications.ps1
```

### 自動起動設定（管理者権限必要）
```powershell
.\setup_autostart.ps1
```

### Slack設定適用
```powershell
python apply_slack_config.py
```

---

## 🔍 確認コマンド

### API Gateway確認
```powershell
.\check_api_gateways.ps1
```

### 通知テスト
```powershell
python test_notification.py
```

### 自動起動タスク確認
```powershell
Get-ScheduledTask -TaskName "ManaOS_DeviceMonitoring"
```

---

## 📊 システム状態確認

### 起動中のシステム確認
```powershell
Get-Process python | Where-Object {$_.Path -like "*manaos_integrations*"}
```

### ポート使用状況確認
```powershell
netstat -ano | findstr "5106 5120 5122"
```

---

## 📝 設定ファイル場所

- `notification_hub_enhanced_config.json` - 通知設定
- `device_health_config.json` - 監視設定
- `google_drive_sync_config.json` - Google Drive設定
- `unified_backup_config.json` - バックアップ設定

---

## 🎯 よく使う操作

### システム再起動
```powershell
# 監視システム再起動
.\start_device_monitoring.ps1
```

### ログ確認
各システムのログは標準出力に表示されます。

### 停止方法
Ctrl+Cで各システムを停止できます。

---

**全システムが正常に動作中です！** ✅

