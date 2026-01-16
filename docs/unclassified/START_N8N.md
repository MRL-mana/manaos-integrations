# 🚀 n8n起動手順

## 🎯 問題

n8nに接続できない（ERR_CONNECTION_REFUSED）

---

## ✅ 起動方法

### 方法A: PowerShellスクリプト経由（推奨）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_local.ps1
```

---

### 方法B: 手動起動

#### B1: npm経由（ローカルインストールの場合）

```powershell
n8n start
```

#### B2: Docker経由（Docker使用の場合）

```powershell
docker start n8n
```

または:

```powershell
docker run -d --name n8n -p 5678:5678 n8nio/n8n
```

---

### 方法C: サービス経由（Windowsサービスとしてインストール済みの場合）

```powershell
Start-Service n8n
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

### n8nが起動しない場合

1. **Node.jsがインストールされているか確認**:
   ```powershell
   node --version
   ```

2. **n8nがインストールされているか確認**:
   ```powershell
   n8n --version
   ```

3. **ポート5678が使用中でないか確認**:
   ```powershell
   netstat -ano | findstr :5678
   ```

---

## 📚 関連ファイル

- `start_n8n_local.ps1` - n8n起動スクリプト
- `n8n_mcp_server/restart_n8n.ps1` - n8n再起動スクリプト

---

**n8nを起動してから、再度アクセスしてください！**🔥


