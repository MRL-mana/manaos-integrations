# 🔐 ngrok認証トークン設定ガイド

## 🎯 現在の状態

**ngrokが認証トークンを要求しています。**

ngrokを使用するには、アカウント登録とauthtokenの設定が必要です。

---

## ✅ 設定手順

### Step 1: ngrokアカウントにサインアップ（5分）

1. **ngrokダッシュボードにアクセス**:
   - https://dashboard.ngrok.com/signup

2. **アカウントを作成**:
   - **Email**: メールアドレスを入力
   - **Password**: パスワードを設定
   - **Sign up** をクリック

3. **メール確認**:
   - メールボックスを確認
   - 確認リンクをクリック

---

### Step 2: authtokenを取得（2分）

1. **ngrokダッシュボードにログイン**:
   - https://dashboard.ngrok.com/get-started/your-authtoken

2. **authtokenをコピー**:
   - 画面に表示されたauthtokenをコピー
   - 例: `2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz`

---

### Step 3: authtokenを設定（1分）

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

### Step 4: ngrokを再起動（1分）

**authtokenを設定した後、ngrokを再起動**:

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

**成功メッセージ**:
```
ngrok                                                                            

Session Status                online
Account                       Your Account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

---

## 💡 ヒント

### ngrok無料プランの制限

- **セッション時間**: 2時間（自動切断）
- **同時接続数**: 1つ
- **リクエスト数**: 制限あり

**長時間使用する場合**: ngrok有料プランまたは代替サービスを検討

---

### authtokenを確認する場合

**ngrok設定ファイルを確認**:

```powershell
notepad $env:LOCALAPPDATA\ngrok\ngrok.yml
```

**または、PowerShellで**:

```powershell
Get-Content $env:LOCALAPPDATA\ngrok\ngrok.yml
```

---

### 代替方法: ローカル開発のみの場合

**Browse AIからローカルn8nに接続する必要がない場合**:
- ngrokは不要です
- ローカルでテストする場合は、`test_browse_ai_webhook.ps1`を使用

---

## 🧪 テスト手順

### Step 1: authtokenを設定

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe config add-authtoken YOUR_AUTHTOKEN_HERE
```

### Step 2: ngrokを起動

```powershell
.\ngrok.exe http 5678
```

### Step 3: URLを確認

**出力されたURLをコピー**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

### Step 4: Browse AIに設定

1. **Browse AIダッシュボード → ロボット選択**
2. **「統合する」タブ**
3. **「Webhooks」を選択**
4. **Webhook URLにngrok URLを入力**
5. **保存**

---

## 📚 関連ファイル

- `setup_ngrok.ps1` - ngrokセットアップスクリプト
- `NGROK_READY.md` - ngrokセットアップ完了ガイド
- `CURRENT_STATUS.md` - 現在の進捗状況

---

## ⚠️ 注意事項

### セキュリティ

- **authtokenは機密情報**: 他人に共有しないでください
- **Gitにコミットしない**: `.gitignore`に`ngrok.yml`を追加

---

## 🎊 完了！

**authtokenを設定したら、ngrokを再起動してください！**

**次のステップ**: authtokenを設定して、ngrokを再起動してください！🔥

