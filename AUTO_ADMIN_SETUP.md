# 自動管理者権限取得機能

**作成日**: 2026年1月3日  
**状態**: 実装完了 ✅

---

## ✅ 実装完了

### 自動管理者権限取得機能
- **ファイル**: `setup_autostart.ps1`（更新済み）
- **機能**: 管理者権限が必要な場合、自動的に管理者として再起動
- **状態**: 実装完了 ✅

---

## 🚀 使用方法

### 通常の実行
```powershell
.\setup_autostart.ps1
```

**動作**:
1. スクリプトが管理者権限をチェック
2. 管理者権限がない場合、自動的に管理者として再起動
3. UAC（ユーザーアカウント制御）ダイアログが表示される
4. 「はい」をクリックすると、管理者権限で実行される

### 手動で管理者として実行する場合
```powershell
# PowerShellを管理者として実行してから
.\setup_autostart.ps1
```

---

## 📋 実装内容

### 自動管理者権限取得コード
```powershell
# Check administrator privileges and restart as admin if needed
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[INFO] Administrator privileges required" -ForegroundColor Yellow
    Write-Host "Restarting script with administrator privileges..." -ForegroundColor Cyan
    Write-Host ""
    
    # Get the script path
    $scriptPath = $MyInvocation.MyCommand.Path
    $arguments = "-ExecutionPolicy Bypass -File `"$scriptPath`""
    
    # Start new PowerShell process as administrator
    Start-Process powershell -Verb RunAs -ArgumentList $arguments
    
    # Exit current process
    exit 0
}
```

---

## 🎯 他のスクリプトにも適用可能

### ヘルパー関数
- **ファイル**: `require_admin.ps1`
- **機能**: 他のスクリプトで使用できるヘルパー関数

### 使用方法
```powershell
# スクリプトの最初に追加
. .\require_admin.ps1
Require-Administrator
```

---

## 📝 注意事項

1. **UACダイアログ**: 管理者権限が必要な場合、UACダイアログが表示されます
2. **再起動**: スクリプトが自動的に再起動されるため、元のプロセスは終了します
3. **引数**: スクリプトに引数がある場合、自動的に引き継がれます

---

## ✅ 動作確認

### テスト実行
```powershell
# 通常ユーザー権限で実行
.\setup_autostart.ps1
```

**期待される動作**:
1. 管理者権限がないことを検出
2. 管理者として再起動する旨を表示
3. UACダイアログが表示される
4. 「はい」をクリックすると、管理者権限で実行される

---

**自動管理者権限取得機能が実装されました！** ✅

