# 🔧 ngrokトラブルシューティングガイド

## ❌ よくある問題と解決方法

### 問題1: ngrokが起動しない

**症状**:
- ngrokウィンドウが表示されない
- エラーメッセージが表示される

**解決方法**:

#### Step 1: ngrokの場所を確認

```powershell
cd C:\Users\mana4\Desktop\ngrok
dir ngrok.exe
```

#### Step 2: 手動で起動

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

#### Step 3: エラーメッセージを確認

**authtokenエラーの場合**:
```
ERR_NGROK_4018: authentication failed
```

**解決方法**:
```powershell
.\ngrok.exe config add-authtoken YOUR_AUTHTOKEN_HERE
```

---

### 問題2: ngrokのURLが表示されない

**症状**:
- ngrokウィンドウは開いているが、URLが表示されない
- "Forwarding" の行が見えない

**解決方法**:

#### Step 1: ngrokのWeb UIを確認

**ブラウザで開く**:
```
http://localhost:4040
```

**表示内容**:
- Forwarding URL
- リクエスト履歴
- レスポンス詳細

#### Step 2: APIでURLを取得

**PowerShellで実行**:
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -Method Get
$response.tunnels[0].public_url
```

**出力例**:
```
https://abc123-def456.ngrok-free.app
```

---

### 問題3: Browse AIから接続できない

**症状**:
- Browse AIからWebhookを送信しても、n8nに届かない
- ngrokのWeb UIにリクエストが表示されない

**解決方法**:

#### Step 1: n8nが起動しているか確認

```powershell
Test-NetConnection -ComputerName localhost -Port 5678 -InformationLevel Quiet
```

**起動していない場合**:
```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_port5678.ps1
```

#### Step 2: n8nのWebhook URLを確認

**n8nのワークフローで**:
1. **Webhookノードを開く**
2. **「Listen for Test Event」をクリック**
3. **Webhook URLをコピー**

**例**:
```
http://localhost:5678/webhook/browse-ai-webhook
```

#### Step 3: ngrokのURLと組み合わせる

**ngrokのURL**:
```
https://abc123-def456.ngrok-free.app
```

**Browse AIに設定するURL**:
```
https://abc123-def456.ngrok-free.app/webhook/browse-ai-webhook
```

---

### 問題4: ngrokが2時間で切断される

**症状**:
- ngrokが2時間後に自動的に切断される
- Browse AIから接続できなくなる

**原因**:
- ngrok無料プランの制限（セッション時間: 2時間）

**解決方法**:

#### 方法1: ngrokを再起動

```powershell
# ngrokを停止
Get-Process ngrok | Stop-Process

# ngrokを再起動
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

#### 方法2: 自動再起動スクリプトを作成

**`restart_ngrok.ps1`**:
```powershell
# ngrokを停止
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process

# 5秒待機
Start-Sleep -Seconds 5

# ngrokを再起動
cd C:\Users\mana4\Desktop\ngrok
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\mana4\Desktop\ngrok; .\ngrok.exe http 5678"
```

#### 方法3: ngrok有料プランにアップグレード

- **URL**: https://dashboard.ngrok.com/billing
- **メリット**: 
  - セッション時間制限なし
  - 複数のトンネル同時実行
  - カスタムドメイン

---

### 問題5: ngrokのWeb UIにアクセスできない

**症状**:
- `http://localhost:4040` にアクセスできない
- エラーメッセージが表示される

**解決方法**:

#### Step 1: ngrokが起動しているか確認

```powershell
Get-Process ngrok -ErrorAction SilentlyContinue
```

#### Step 2: ポート4040が使用されているか確認

```powershell
netstat -ano | findstr :4040
```

#### Step 3: ファイアウォールを確認

**Windowsファイアウォールでポート4040を許可**:
1. **Windowsセキュリティ** → **ファイアウォールとネットワーク保護**
2. **詳細設定**
3. **受信の規則** → **新しい規則**
4. **ポート** → **TCP** → **特定のローカルポート: 4040**
5. **接続を許可する**

---

## 🧪 テスト手順

### Step 1: ngrokの状態確認

```powershell
# ngrokプロセス確認
Get-Process ngrok -ErrorAction SilentlyContinue

# ngrokのWeb UI確認
Start-Process "http://localhost:4040"
```

### Step 2: URL取得

```powershell
# APIでURLを取得
$response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -Method Get
$publicUrl = $response.tunnels[0].public_url
Write-Host "Public URL: $publicUrl" -ForegroundColor Green
```

### Step 3: n8nのWebhookをテスト

```powershell
# Browse AIのWebhook URL
$webhookUrl = "$publicUrl/webhook/browse-ai-webhook"

# テストリクエストを送信
$testData = @{
    robotName = "test"
    url = "https://example.com"
    extractedData = @{
        test = "data"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $testData -ContentType "application/json"
```

---

## 📚 関連ファイル

- `NGROK_AUTH_SETUP.md` - ngrok認証トークン設定ガイド
- `NGROK_AUTH_COMPLETE.md` - ngrok認証トークン設定完了ガイド
- `START_NGROK.md` - ngrok起動ガイド

---

## 💡 ヒント

### ngrokを常時起動する

**タスクスケジューラで設定**:
1. **タスクスケジューラ**を開く
2. **基本タスクの作成**
3. **名前**: `ngrokトンネル`
4. **トリガー**: **コンピューターの起動時**
5. **操作**: **プログラムの開始**
6. **プログラム**: `powershell.exe`
7. **引数**: `-NoExit -Command "cd C:\Users\mana4\Desktop\ngrok; .\ngrok.exe http 5678"`

---

### ngrokのログを確認

**ngrokのログファイル**:
```
C:\Users\mana4\AppData\Local\ngrok\ngrok.log
```

**ログを確認**:
```powershell
Get-Content C:\Users\mana4\AppData\Local\ngrok\ngrok.log -Tail 50
```

---

## 🆘 それでも解決しない場合

1. **ngrokを再インストール**
2. **authtokenを再設定**
3. **ngrokのバージョンを確認** (`ngrok.exe version`)
4. **ngrokのサポートに問い合わせ**: https://ngrok.com/support


