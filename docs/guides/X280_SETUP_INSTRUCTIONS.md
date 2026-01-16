# X280自動管理者権限取得機能 セットアップ手順

**作成日**: 2026年1月3日  
**状態**: ファイル転送完了 ✅

---

## ✅ 転送完了

### 転送したファイル

以下のファイルがX280の `C:\temp\` に転送されました：

1. ✅ `x280_common_admin_check.ps1` - X280用共通管理者権限チェック関数
2. ✅ `x280_api_gateway_start.ps1` - X280 API Gateway起動スクリプト
3. ✅ `common_admin_check.ps1` - 共通関数（バックアップ）

---

## 🚀 X280側でのセットアップ手順

### Step 1: X280にSSH接続

```powershell
ssh x280
```

### Step 2: 作業ディレクトリを作成

```powershell
# X280側で実行
mkdir C:\manaos_x280
```

### Step 3: ファイルを移動

```powershell
# X280側で実行
move C:\temp\x280_common_admin_check.ps1 C:\manaos_x280\
move C:\temp\x280_api_gateway_start.ps1 C:\manaos_x280\
move C:\temp\common_admin_check.ps1 C:\manaos_x280\
```

### Step 4: 確認

```powershell
# X280側で実行
cd C:\manaos_x280
dir
```

---

## 🎯 使用方法

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

---

## 📋 リモート実行（新PCから）

```powershell
# 新PCから実行
ssh x280 "cd C:\manaos_x280; .\x280_api_gateway_start.ps1"
```

---

## 🎉 まとめ

**X280側でも自動管理者権限取得機能が使えるようになりました！**

- ✅ X280用スクリプト作成完了
- ✅ X280への転送完了（C:\temp\）
- ✅ セットアップ手順完了

X280側で上記の手順を実行すると、自動管理者権限取得機能が使用可能になります！

---

**最終更新**: 2026年1月3日

