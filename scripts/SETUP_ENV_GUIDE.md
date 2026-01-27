# 環境変数設定ガイド

## 概要

Dドライブ移行用の環境変数（`HF_HOME`、`TRANSFORMERS_CACHE`）を設定する方法です。

## 方法1: PowerShellスクリプトを使用（推奨）

### 現在のセッションのみに設定

```powershell
# プロジェクトディレクトリに移動
cd C:\Users\mana4\Desktop\manaos_integrations

# スクリプトを実行
.\scripts\setup_d_drive_env.ps1
```

### システム環境変数に永続化（管理者権限が必要）

1. **PowerShellを管理者として起動**
   - Windowsキーを押す
   - "PowerShell"と入力
   - "Windows PowerShell"を右クリック
   - "管理者として実行"を選択

2. **スクリプトを実行**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\scripts\setup_d_drive_env.ps1
   ```

## 方法2: バッチファイルを使用

### 現在のセッションのみに設定

```cmd
cd C:\Users\mana4\Desktop\manaos_integrations
scripts\setup_d_drive_env.bat
```

### システム環境変数に永続化（管理者権限が必要）

1. **コマンドプロンプトを管理者として起動**
   - Windowsキーを押す
   - "cmd"と入力
   - "コマンドプロンプト"を右クリック
   - "管理者として実行"を選択

2. **バッチファイルを実行**
   ```cmd
   cd C:\Users\mana4\Desktop\manaos_integrations
   scripts\setup_d_drive_env.bat
   ```

## 方法3: 手動で設定

### Windowsの設定から設定

1. **システムのプロパティを開く**
   - Windowsキー + R
   - `sysdm.cpl`と入力してEnter

2. **環境変数を開く**
   - "詳細設定"タブ
   - "環境変数"ボタンをクリック

3. **システム環境変数を追加**
   - "システム環境変数"セクションで"新規"をクリック
   - 変数名: `HF_HOME`
   - 変数値: `D:\huggingface_cache`
   - "OK"をクリック

   - 再度"新規"をクリック
   - 変数名: `TRANSFORMERS_CACHE`
   - 変数値: `D:\huggingface_cache`
   - "OK"をクリック

4. **PowerShell/コマンドプロンプトを再起動**

## 設定の確認

設定後、新しいPowerShell/コマンドプロンプトセッションで確認：

```powershell
# PowerShell
$env:HF_HOME
$env:TRANSFORMERS_CACHE
```

```cmd
REM コマンドプロンプト
echo %HF_HOME%
echo %TRANSFORMERS_CACHE%
```

## トラブルシューティング

### 文字化けが発生する場合

PowerShellのエンコーディング設定を変更：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

### 管理者権限がない場合

現在のセッションのみに環境変数が設定されます。新しいセッションでは再度設定が必要です。

### ディレクトリが作成されない場合

手動でディレクトリを作成：

```powershell
New-Item -ItemType Directory -Path "D:\huggingface_cache" -Force
```

## 注意事項

- システム環境変数に設定すると、すべてのユーザーに影響します
- 新しいセッションで環境変数が有効になります
- 既存のセッションでは、再起動が必要な場合があります
