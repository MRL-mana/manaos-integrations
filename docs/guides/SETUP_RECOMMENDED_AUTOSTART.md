# 標準構成（推奨）自動起動設定ガイド
**作成日**: 2025-12-29

---

## 📋 標準構成（推奨）の内容

1. ✅ **manaOS統合APIサーバー** (ポート9500)
   - 状態: 既に自動起動設定済み

2. ⚠️ **n8nワークフローエンジン** (ポート5679)
   - 状態: 手動起動のみ
   - 設定が必要

---

## 🚀 設定手順

### ステップ1: 管理者権限でPowerShellを開く

1. Windowsキーを押す
2. "PowerShell"と入力
3. 「Windows PowerShell」を右クリック
4. 「管理者として実行」を選択

### ステップ2: n8nをWindowsサービスとしてインストール

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\install_n8n_service_simple.ps1
```

**注意**: 
- n8nがインストールされている必要があります
- インストールされていない場合: `npm install -g n8n`

### ステップ3: 設定確認

```powershell
# n8nサービスの状態確認
Get-Service n8n

# manaOS統合APIサーバーの状態確認
Get-ScheduledTask -TaskName "manaOS-API-Server"
```

---

## ✅ 設定完了後の確認

### PC再起動後の動作確認

1. **PCを再起動**

2. **manaOS統合APIサーバーの確認**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   python check_server_status.py
   ```
   またはブラウザで: http://127.0.0.1:9502/health

3. **n8nの確認**
   ```powershell
   Get-Service n8n
   ```
   またはブラウザで: http://127.0.0.1:5679

---

## 🔧 サービス管理コマンド

### n8nサービス管理

```powershell
# 開始
Start-Service n8n

# 停止
Stop-Service n8n

# 再起動
Restart-Service n8n

# 状態確認
Get-Service n8n

# 自動起動を無効化
Set-Service n8n -StartupType Disabled

# 自動起動を有効化
Set-Service n8n -StartupType Automatic
```

### manaOS統合APIサーバー管理

```powershell
# タスク状態確認
Get-ScheduledTask -TaskName "manaOS-API-Server"

# タスクを実行
Start-ScheduledTask -TaskName "manaOS-API-Server"

# タスクを停止
Stop-ScheduledTask -TaskName "manaOS-API-Server"
```

---

## 📊 設定されるサービス一覧

| サービス | ポート | 自動起動 | 状態 |
|---------|--------|---------|------|
| manaOS統合APIサーバー | 9500 | ✅ 有効 | 設定済み |
| n8nワークフローエンジン | 5679 | ⚠️ 設定必要 | 未設定 |

---

## 🎯 次のステップ

設定完了後:

1. **PCを再起動**して動作確認
2. **各サービスの状態を確認**
3. **必要に応じて追加サービスを設定**（リアルタイムダッシュボード、マスターコントロールパネルなど）

---

**設定完了**: 標準構成（推奨）の自動起動設定が完了しました












