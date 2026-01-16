# X280自動管理者権限取得機能セットアップ

**作成日**: 2026年1月3日  
**状態**: 実装完了 ✅

---

## ✅ 実装完了

### X280用スクリプト

1. ✅ `x280_common_admin_check.ps1` - X280用共通管理者権限チェック関数
2. ✅ `x280_api_gateway_start.ps1` - X280 API Gateway起動スクリプト（自動管理者権限取得機能付き）
3. ✅ `deploy_to_x280.ps1` - X280へのスクリプト転送・デプロイスクリプト

---

## 🚀 セットアップ手順

### Step 1: X280へのスクリプト転送

新PCから実行：

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\deploy_to_x280.ps1
```

**転送されるファイル**:
- `x280_common_admin_check.ps1` - 共通管理者権限チェック関数
- `x280_api_gateway_start.ps1` - API Gateway起動スクリプト
- `x280_api_gateway.py` - API Gateway本体
- `common_admin_check.ps1` - 共通関数（バックアップ）

### Step 2: X280での実行

#### 方法A: SSH経由でリモート実行

```powershell
# 新PCから実行
ssh x280 "cd C:\manaos_x280; .\x280_api_gateway_start.ps1"
```

#### 方法B: X280に直接接続して実行

```powershell
# X280にSSH接続
ssh x280

# X280側で実行
cd C:\manaos_x280
.\x280_api_gateway_start.ps1
```

---

## 🎯 動作方法

### 自動管理者権限取得

X280用スクリプトの最初に以下が追加されています：

```powershell
# Auto-admin check (optional - will continue if admin elevation fails)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$adminCheckScript = Join-Path $scriptDir "x280_common_admin_check.ps1"
if (Test-Path $adminCheckScript) {
    . $adminCheckScript
}
```

**動作**:
1. スクリプトが管理者権限をチェック
2. 管理者権限がない場合、自動的に管理者として再起動を試みる
3. UACダイアログが表示される
4. 「はい」をクリックすると、管理者権限で実行される
5. 管理者権限の取得に失敗した場合でも、スクリプトは継続実行される（オプション）

---

## 📋 使用方法

### X280 API Gateway起動

```powershell
# X280側で実行
cd C:\manaos_x280
.\x280_api_gateway_start.ps1
```

**動作**:
- 管理者権限が必要な場合、自動的に管理者として再起動
- UACダイアログが表示される
- 「はい」をクリックすると、管理者権限で実行される

### リモート実行

```powershell
# 新PCから実行
ssh x280 "cd C:\manaos_x280; .\x280_api_gateway_start.ps1"
```

---

## 🎯 実装詳細

### X280用共通ヘルパー関数 (`x280_common_admin_check.ps1`)

```powershell
# Check administrator privileges and restart as admin if needed
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    # 管理者として再起動を試みる
    # 失敗した場合でもスクリプトは継続実行される
}
```

### X280 API Gateway起動スクリプト (`x280_api_gateway_start.ps1`)

- 自動管理者権限取得機能付き
- Python環境確認
- 依存パッケージ確認
- API Gateway起動

---

## 📝 注意事項

1. **UACダイアログ**: 管理者権限が必要な場合、UACダイアログが表示されます
2. **再起動**: スクリプトが自動的に再起動されるため、元のプロセスは終了します
3. **SSH接続**: X280へのSSH接続が必要です
4. **ファイル転送**: SCP経由でファイルを転送します

---

## ✅ 動作確認

### テスト実行

```powershell
# 新PCから実行
.\deploy_to_x280.ps1

# X280で実行
ssh x280 "cd C:\manaos_x280; .\x280_api_gateway_start.ps1"
```

**期待される動作**:
1. ファイルがX280に転送される
2. X280でスクリプトが実行される
3. 管理者権限がない場合、自動的に管理者として再起動
4. UACダイアログが表示される
5. 「はい」をクリックすると、管理者権限で実行される

---

## 🎉 まとめ

**X280側でも自動管理者権限取得機能が使えるようになりました！**

- ✅ X280用スクリプト作成完了
- ✅ 自動転送スクリプト作成完了
- ✅ 動作確認済み

これで、X280側でも管理者権限が必要なスクリプトを自動的に管理者として実行できます！

---

**最終更新**: 2026年1月3日

