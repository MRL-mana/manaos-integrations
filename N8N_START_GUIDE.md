# 🚀 n8n起動ガイド

## 🎯 問題

n8nに接続できない（ERR_CONNECTION_REFUSED）

---

## ✅ 起動方法

### 方法A: PowerShellスクリプト経由（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_port5678.ps1
```

**または新しいウィンドウで起動**:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\mana4\OneDrive\Desktop\manaos_integrations'; `$env:N8N_PORT='5678'; n8n start --port 5678"
```

---

### 方法B: 手動起動

```powershell
$env:N8N_PORT = "5678"
n8n start --port 5678
```

---

### 方法C: Docker経由（Docker使用の場合）

```powershell
docker start n8n
```

または:

```powershell
docker run -d --name n8n -p 5678:5678 n8nio/n8n
```

---

## 🔍 確認方法

### Step 1: ポート確認

```powershell
Test-NetConnection -ComputerName localhost -Port 5678
```

**成功した場合**: n8nが起動しています
**失敗した場合**: n8nを起動してください

---

### Step 2: ブラウザで確認

1. **ブラウザで開く**: http://localhost:5678
2. **ログイン画面が表示されればOK**

---

## 💡 トラブルシューティング

### n8nがインストールされていない場合

```powershell
npm install -g n8n
```

---

### ポート5678が使用中の場合

```powershell
# 使用中のプロセスを確認
netstat -ano | findstr :5678

# プロセスを終了（必要に応じて）
Stop-Process -Id [PID] -Force
```

---

## 📚 関連ファイル

- `start_n8n_port5678.ps1` - n8n起動スクリプト（ポート5678）
- `start_n8n_local.ps1` - n8n起動スクリプト（ポート5679）

---

**n8nを起動してから、再度アクセスしてください！**🔥


