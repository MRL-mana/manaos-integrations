# 🔧 ngrok authtoken修正ガイド

## ❌ 問題

**エラーメッセージ**:
```
ERROR: authentication failed: The authtoken you specified does not look like a proper ngrok authtoken.
ERROR: ERR_NGROK_105
```

**原因**: authtokenの形式が正しくありません。

---

## ✅ 解決方法

### Step 1: ngrokダッシュボードにアクセス

**URL**: https://dashboard.ngrok.com/get-started/your-authtoken

**または**:
1. **ngrokダッシュボードにログイン**: https://dashboard.ngrok.com
2. **「Get Started」タブをクリック**
3. **「Your Authtoken」セクションを確認**

---

### Step 2: 正しいauthtokenをコピー

**ngrokダッシュボードで表示されるauthtoken**:
- **形式**: 通常、ハイフンで区切られた長い文字列
- **例**: `2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz`
- **長さ**: 約40文字以上

**⚠️ 重要**: 
- **10行の文字列ではなく、1つの長い文字列をコピー**
- **スペースや改行を含めない**
- **完全にコピーする**

---

### Step 3: authtokenを設定

**PowerShellで実行**:

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe config add-authtoken YOUR_AUTHTOKEN_HERE
```

**例**:
```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe config add-authtoken 2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

**成功メッセージ**:
```
Authtoken saved to configuration file: C:\Users\mana4\AppData\Local\ngrok\ngrok.yml
```

---

### Step 4: ngrokを起動

**PowerShellで実行**:

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

**または、スクリプトを使用**:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_ngrok_simple.ps1
```

---

## 🧪 確認方法

### authtokenが正しく設定されているか確認

**ngrokの設定ファイルを確認**:

```powershell
Get-Content C:\Users\mana4\AppData\Local\ngrok\ngrok.yml
```

**表示内容**:
```yaml
version: "2"
authtoken: YOUR_AUTHTOKEN_HERE
```

---

### ngrokを起動して確認

**ngrokを起動**:

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

**成功メッセージ**:
```
Session Status                online
Account                       YOUR_ACCOUNT (Plan: Free)
Version                       3.34.1
Region                        United States (us)
Latency                       50ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

**エラーメッセージが出る場合**:
- authtokenが正しくない
- ngrokアカウントが未確認
- インターネット接続の問題

---

## 💡 ヒント

### ngrokアカウントが未確認の場合

**ngrokダッシュボードで確認**:
1. **ダッシュボードにログイン**: https://dashboard.ngrok.com
2. **「Account」タブを確認**
3. **メールアドレスが確認済みか確認**
4. **未確認の場合**: メールボックスを確認して確認リンクをクリック

---

### authtokenを再生成する場合

**ngrokダッシュボードで**:
1. **「Your Authtoken」セクションを開く**
2. **「Reset Authtoken」をクリック**
3. **新しいauthtokenをコピー**
4. **設定を更新**

---

## 📚 関連ファイル

- `NGROK_AUTH_SETUP.md` - ngrok認証トークン設定ガイド
- `NGROK_TROUBLESHOOTING.md` - ngrokトラブルシューティングガイド
- `start_ngrok_simple.ps1` - ngrok簡単起動スクリプト

---

## 🆘 それでも解決しない場合

1. **ngrokアカウントを再確認**: https://dashboard.ngrok.com
2. **authtokenを再生成**: ダッシュボードで「Reset Authtoken」
3. **ngrokのバージョンを確認**: `ngrok.exe version`
4. **ngrokのサポートに問い合わせ**: https://ngrok.com/support

---

## 🎯 次のステップ

1. **ngrokダッシュボードから正しいauthtokenを取得**
2. **authtokenを設定**
3. **ngrokを起動**
4. **URLを確認してBrowse AIに設定**


