# n8n 常時起動設定ガイド

## 現在の状況

現在、n8nは手動起動スクリプト（`start_n8n_local.ps1`）のみで、常時起動の設定はされていません。

## 常時起動の方法

### 方法1: Windowsサービスとして登録（推奨）

**メリット:**
- システム起動時に自動起動
- バックグラウンドで常時実行
- サービス管理が簡単

**手順:**

1. **管理者権限でPowerShellを開く**
   - Windowsキー → "PowerShell" を検索
   - 右クリック → "管理者として実行"

2. **サービスをインストール**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   .\install_n8n_as_service.ps1
   ```

3. **確認**
   ```powershell
   Get-Service n8n
   ```

**サービス管理コマンド:**
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

### 方法2: タスクスケジューラで登録

**メリット:**
- 管理者権限が不要（ユーザー権限で実行可能）
- ログイン時に自動起動

**手順:**

1. **タスクスケジューラを開く**
   - Windowsキー → "タスクスケジューラ" を検索

2. **基本タスクの作成**
   - 右側の「基本タスクの作成」をクリック
   - 名前: "n8n Auto Start"
   - トリガー: "ログオン時"
   - 操作: "プログラムの開始"
   - プログラム: `n8n`
   - 引数: `start --port 5679`
   - 開始場所: `$env:USERPROFILE\.n8n`

3. **詳細設定**
   - 「タスクのプロパティを開く」をチェック
   - 「最上位の特権で実行する」をチェック（オプション）
   - 「ユーザーがログオンしているかどうかにかかわらず実行する」を選択

### 方法3: スタートアップフォルダに配置（簡易版）

**メリット:**
- 最も簡単
- ログイン時に自動起動

**手順:**

1. **バッチファイルを作成**
   ```batch
   @echo off
   cd /d %USERPROFILE%\.n8n
   n8n start --port 5679
   ```

2. **スタートアップフォルダに配置**
   - Windowsキー + R → `shell:startup` を入力
   - バッチファイルをコピー

**注意:** この方法では、ログアウトするとn8nも停止します。

## 推奨設定

**Windowsサービスとして登録（方法1）を推奨します。**

理由:
- システム起動時に自動起動
- ユーザーログイン不要
- バックグラウンドで確実に実行
- サービス管理が簡単

## 現在の起動方法

現在は手動起動のみ：
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_local.ps1
```

## 確認方法

n8nが起動しているか確認：
```powershell
# ポート確認
Get-NetTCPConnection -LocalPort 5679

# プロセス確認
Get-Process | Where-Object { $_.ProcessName -eq "node" } | Where-Object { $_.CommandLine -like "*n8n*" }

# Web UI確認
Start-Process "http://localhost:5679"
```











