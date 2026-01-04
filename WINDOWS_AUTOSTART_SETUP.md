# Windows自動起動設定ガイド
**作成日**: 2025-12-29  
**対象**: Windows環境（新PC）

---

## 現在の状態

**❌ 自動起動未設定**

- サーバーは手動起動のみ
- PC再起動後は手動で起動する必要がある

---

## 自動起動設定方法

### 方法1: タスクスケジューラを使用（推奨）

#### 1. 管理者権限でPowerShellを開く

1. Windowsキーを押す
2. "PowerShell"と入力
3. 「Windows PowerShell」を右クリック
4. 「管理者として実行」を選択

#### 2. 自動起動スクリプトを実行

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\setup_windows_autostart.ps1
```

#### 3. 設定確認

```powershell
Get-ScheduledTask -TaskName "manaOS-API-Server"
```

---

### 方法2: スタートアップフォルダにショートカットを配置

#### 1. スタートアップフォルダを開く

```powershell
shell:startup
```

#### 2. ショートカットを作成

1. スタートアップフォルダで右クリック
2. 「新規作成」→「ショートカット」
3. 項目の場所:
   ```
   C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe
   ```
4. 引数:
   ```
   "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\start_server_with_notification.py"
   ```
5. 作業フォルダ:
   ```
   C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   ```

---

## 再起動時の動作

### 設定後

1. **PC再起動時**: 自動的にサーバーが起動
2. **ログオン時**: 自動的にサーバーが起動
3. **失敗時**: 最大3回再試行（1分間隔）

### 確認方法

PC再起動後、以下で確認:

```powershell
# サーバー状態確認
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python check_server_status.py

# またはブラウザで
# http://127.0.0.1:9500/health
```

---

## 自動起動の削除

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\setup_windows_autostart.ps1 -Remove
```

---

## トラブルシューティング

### タスクが実行されない

1. **タスクスケジューラで確認**:
   ```powershell
   Get-ScheduledTask -TaskName "manaOS-API-Server" | Get-ScheduledTaskInfo
   ```

2. **ログを確認**:
   - タスクスケジューラを開く
   - 「タスク スケジューラ ライブラリ」→「manaOS-API-Server」
   - 「履歴」タブでエラーを確認

### サーバーが起動しない

1. **手動起動を試す**:
   ```powershell
   python start_server_with_notification.py
   ```

2. **エラーメッセージを確認**

3. **ポートが使用中でないか確認**:
   ```powershell
   netstat -ano | findstr :9500
   ```

---

## 推奨設定

**方法1（タスクスケジューラ）を推奨**:
- より確実に動作
- 失敗時の自動再試行
- ログが記録される

---

**設定完了後**: PCを再起動して動作確認してください











