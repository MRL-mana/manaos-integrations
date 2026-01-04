# 自動起動設定の再設定手順

## 現状
- PC再起動後、manaOS統合APIサーバーが自動起動していない
- 自動起動タスクが登録されていない可能性

## 解決方法

### ステップ1: 管理者権限でPowerShellを開く

### ステップ2: 自動起動設定を再実行

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
& ".\setup_recommended_autostart.ps1"
```

### ステップ3: 確認

```powershell
# タスクスケジューラの確認
Get-ScheduledTask -TaskName "manaOS-API-Server"

# n8nサービスの確認
Get-Service n8n
```

## 手動起動（今すぐ使いたい場合）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python start_server_with_notification.py
```










