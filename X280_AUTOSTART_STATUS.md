# X280自動起動設定の状態確認

## 現在の状況

スクリプトが管理者権限で再起動されました。以下のいずれかの状況です：

1. **管理者権限の昇格ダイアログが表示されている**
   - 「はい」をクリックして続行してください

2. **新しいPowerShellウィンドウが開いている**
   - 管理者権限で実行中のスクリプトの出力を確認してください

3. **スクリプトが完了している**
   - タスクスケジューラに登録されているか確認してください

---

## 確認方法

### 方法1: タスクスケジューラで確認

```powershell
# X280側で実行
Get-ScheduledTask -TaskName "ManaOS_X280_API_Gateway" -ErrorAction SilentlyContinue
```

### 方法2: 手動で再実行

管理者権限でPowerShellを開いて実行：

```powershell
cd C:\manaos_x280
.\x280_setup_autostart.ps1
```

### 方法3: スクリプトを改善版で実行

より詳細な出力を表示するバージョン：

```powershell
cd C:\manaos_x280

# 管理者権限で直接実行
Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File C:\manaos_x280\x280_setup_autostart.ps1"
```

---

## トラブルシューティング

### 管理者権限の昇格ダイアログが表示されない場合

1. **手動で管理者権限のPowerShellを開く**
   - スタートメニューで「PowerShell」を検索
   - 右クリック → 「管理者として実行」

2. **スクリプトを直接実行**
   ```powershell
   cd C:\manaos_x280
   .\x280_setup_autostart.ps1
   ```

### タスクが登録されていない場合

スクリプトを再度実行してください。エラーメッセージを確認してください。

---

**新しいPowerShellウィンドウが開いている場合は、そのウィンドウの出力を確認してください！**

