# X280自動管理者権限取得機能 クイックセットアップ

**X280側で実行する手順**

---

## 🚀 X280側でのセットアップ（現在の状態）

### 現在の状態
- ✅ `C:\manaos_x280` ディレクトリが既に存在
- ✅ ファイルは `C:\temp\` に転送済み

### 次のステップ

#### Step 1: ファイルを移動

```powershell
# X280側で実行（現在のPowerShellで）
move C:\temp\x280_common_admin_check.ps1 C:\manaos_x280\
move C:\temp\x280_api_gateway_start.ps1 C:\manaos_x280\
move C:\temp\common_admin_check.ps1 C:\manaos_x280\
```

#### Step 2: 確認

```powershell
cd C:\manaos_x280
dir
```

#### Step 3: スクリプトを実行

```powershell
.\x280_api_gateway_start.ps1
```

---

## 📋 ファイル一覧確認

```powershell
# C:\temp\にあるファイルを確認
dir C:\temp\x280*.ps1

# C:\manaos_x280\にあるファイルを確認
dir C:\manaos_x280\
```

---

## 🎯 動作確認

スクリプトを実行すると：
1. 管理者権限をチェック
2. 管理者権限がない場合、自動的に管理者として再起動
3. UACダイアログが表示される
4. 「はい」をクリックすると、管理者権限で実行される

---

**X280側で上記のコマンドを実行してください！**

