# 🔧 n8n接続トラブルシューティング

## 🎯 問題

n8nに接続できない（ERR_CONNECTION_REFUSED）

---

## ✅ 確認・修正手順

### Step 1: n8nプロセス確認

```powershell
# ポート5678を使用しているプロセスを確認
Get-NetTCPConnection -LocalPort 5678 -ErrorAction SilentlyContinue

# Node.jsプロセスを確認
Get-Process | Where-Object {$_.ProcessName -eq "node"}
```

**プロセスが見つからない場合**: n8nが起動していません → Step 2へ

---

### Step 2: n8nを起動

#### 方法A: PowerShellスクリプト経由

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_port5678.ps1
```

#### 方法B: 手動起動（新しいウィンドウ）

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\mana4\OneDrive\Desktop\manaos_integrations'; `$env:N8N_PORT='5678'; n8n start --port 5678"
```

#### 方法C: 直接起動

```powershell
$env:N8N_PORT = "5678"
n8n start --port 5678
```

---

### Step 3: 起動確認

**10秒待ってから**:

```powershell
Test-NetConnection -ComputerName localhost -Port 5678
```

**成功した場合**: 
- ブラウザで http://localhost:5678 を開く
- n8nのログイン画面が表示されればOK

**失敗した場合**: 
- n8nの起動ログを確認
- エラーメッセージを確認

---

## 💡 よくある問題と解決策

### 問題1: ポート5678が使用中

**確認**:
```powershell
netstat -ano | findstr :5678
```

**解決策**:
```powershell
# プロセスIDを確認して終了
Stop-Process -Id [PID] -Force
```

---

### 問題2: n8nがインストールされていない

**確認**:
```powershell
n8n --version
```

**解決策**:
```powershell
npm install -g n8n
```

---

### 問題3: 起動に時間がかかる

**解決策**:
- 起動後30秒〜1分待つ
- ブラウザをリロード

---

### 問題4: ファイアウォールがブロックしている

**解決策**:
- Windowsファイアウォール設定を確認
- ポート5678を許可

---

## 🧪 テスト手順

### Step 1: n8n起動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_port5678.ps1
```

### Step 2: 10秒待つ

### Step 3: ブラウザで確認

```
http://localhost:5678
```

---

## 📚 関連ファイル

- `start_n8n_port5678.ps1` - n8n起動スクリプト
- `N8N_START_GUIDE.md` - 起動ガイド

---

**n8nを起動してから、再度アクセスしてください！**🔥


