# 🌐 ngrokインストールガイド

## 🎯 問題

Chocolateyがインストールされていないため、`choco install ngrok`が実行できません。

---

## ✅ 解決方法（2つの選択肢）

### 方法A: ngrokを直接ダウンロード（推奨・簡単）

#### Step 1: ngrokをダウンロード

1. **ngrokの公式サイトにアクセス**: https://ngrok.com/download
2. **Windows版をダウンロード**
3. **ZIPファイルを解凍**

---

#### Step 2: ngrokを配置

1. **解凍したフォルダを開く**
2. **`ngrok.exe`をコピー**
3. **適切な場所に配置**:
   - 例: `C:\ngrok\ngrok.exe`
   - または: `C:\Users\mana4\OneDrive\Desktop\ngrok\ngrok.exe`

---

#### Step 3: パスを通す（オプション）

**ngrokをどこからでも実行できるようにする**:

1. **環境変数を開く**:
   - Windowsキー + R
   - `sysdm.cpl`と入力
   - 「詳細設定」タブ → 「環境変数」

2. **Path変数を編集**:
   - 「システム環境変数」の「Path」を選択
   - 「編集」をクリック
   - 「新規」をクリック
   - ngrok.exeがあるフォルダのパスを入力（例: `C:\ngrok`）
   - 「OK」をクリック

3. **PowerShellを再起動**

---

### 方法B: Chocolateyをインストールしてからngrokをインストール

#### Step 1: Chocolateyをインストール

1. **PowerShellを管理者として実行**
2. **以下のコマンドを実行**:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

3. **インストールが完了するまで待つ**

---

#### Step 2: ngrokをインストール

```powershell
choco install ngrok -y
```

---

## 🚀 ngrokの使い方

### Step 1: ngrokでトンネルを作成

**ngrok.exeがあるフォルダで実行**:

```powershell
cd C:\ngrok
.\ngrok.exe http 5678
```

**または、パスを通した場合**:

```powershell
ngrok http 5678
```

---

### Step 2: URLをコピー

**出力例**:
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

**このURLをコピー**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

---

### Step 3: Browse AIに設定

1. **Browse AIダッシュボードで「統合する」タブを開く**
2. **「Webhooks」または「Add Integration」をクリック**
3. **Webhook URLに上記のURLを入力**
4. **「Save」をクリック**

---

## 💡 ヒント

### ngrokのアカウント作成（推奨）

**無料アカウントを作成すると**:
- より長いURLが使用可能
- より多くの機能が利用可能

1. **ngrokの公式サイトにアクセス**: https://ngrok.com/
2. **「Sign up」をクリック**
3. **アカウントを作成**
4. **認証トークンを取得**
5. **ngrokに認証**:

```powershell
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

---

### ngrokを常時起動する場合

**バックグラウンドで実行**:

```powershell
Start-Process ngrok -ArgumentList "http 5678"
```

**または、新しいウィンドウで実行**:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ngrok http 5678"
```

---

## 📚 関連ファイル

- `BROWSE_AI_WEBHOOK_SETUP.md` - Webhook設定ガイド
- `BROWSE_AI_REVIEW_RESULTS.md` - 結果確認ガイド

---

**ngrokをダウンロードして、Browse AIにWebhookを設定してください！**🔥


