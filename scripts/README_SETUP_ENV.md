# 環境変数設定スクリプトの使い方

## 問題が発生した場合

PowerShellスクリプトでエラーが発生する場合、以下の方法を試してください。

### 方法1: エンコーディングを設定してから実行

```powershell
# PowerShellでエンコーディングを設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001

# スクリプトを実行
cd C:\Users\mana4\Desktop\manaos_integrations
.\scripts\setup_d_drive_env.ps1
```

### 方法2: バッチファイルを使用

```cmd
cd C:\Users\mana4\Desktop\manaos_integrations
scripts\setup_d_drive_env.bat
```

### 方法3: 手動で環境変数を設定

PowerShellで直接設定：

```powershell
# 現在のセッションのみ
$env:HF_HOME = "D:\huggingface_cache"
$env:TRANSFORMERS_CACHE = "D:\huggingface_cache"

# 確認
$env:HF_HOME
$env:TRANSFORMERS_CACHE
```

システム環境変数に永続化する場合（管理者権限が必要）：

```powershell
# 管理者としてPowerShellを起動してから
[Environment]::SetEnvironmentVariable("HF_HOME", "D:\huggingface_cache", "Machine")
[Environment]::SetEnvironmentVariable("TRANSFORMERS_CACHE", "D:\huggingface_cache", "Machine")
```

### 方法4: Windowsの設定から手動設定

1. Windowsキー + R → `sysdm.cpl` → Enter
2. 「詳細設定」タブ → 「環境変数」ボタン
3. 「システム環境変数」セクションで「新規」をクリック
4. 変数名: `HF_HOME`、変数値: `D:\huggingface_cache`
5. 再度「新規」をクリック
6. 変数名: `TRANSFORMERS_CACHE`、変数値: `D:\huggingface_cache`
7. 「OK」をクリック
8. PowerShell/コマンドプロンプトを再起動

## 確認方法

新しいPowerShellセッションで確認：

```powershell
$env:HF_HOME
$env:TRANSFORMERS_CACHE
```

両方とも `D:\huggingface_cache` と表示されれば成功です。
