# 🐳 Docker Desktop 起動ガイド

**問題**: Open WebUIが開かない → Dockerが起動していない可能性があります

---

## 🔍 確認方法

### Docker Desktopが起動しているか確認

1. **タスクバーを確認**
   - タスクバーの右下（システムトレイ）にDockerのアイコンがあるか確認
   - アイコンが表示されていれば起動中

2. **タスクマネージャーで確認**
   - `Ctrl + Shift + Esc` でタスクマネージャーを開く
   - 「プロセス」タブで「Docker Desktop」を探す

---

## 🚀 Docker Desktopを起動する方法

### 方法1: スタートメニューから起動

1. **Windowsキー**を押す
2. 「**Docker Desktop**」と検索
3. **Docker Desktop**をクリックして起動

### 方法2: ショートカットから起動

1. デスクトップまたはスタートメニューから**Docker Desktop**を起動
2. 起動に1-2分かかる場合があります

### 方法3: PowerShellから起動

```powershell
# Docker Desktopのパスを確認
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerPath) {
    Start-Process $dockerPath
} else {
    Write-Host "Docker Desktopが見つかりません"
}
```

---

## ⏳ 起動後の確認

Docker Desktopが起動したら：

1. **タスクバーのDockerアイコンを確認**
   - アイコンが緑色になれば起動完了

2. **Open WebUIを再起動**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
   ```

3. **ブラウザでアクセス**
   ```
   http://localhost:3001
   ```

---

## 🔧 トラブルシューティング

### 問題1: Docker Desktopが起動しない

**解決策**:
1. コンピューターを再起動
2. Docker Desktopを最新版に更新
3. Windowsの再起動が必要な場合があります

### 問題2: Docker Desktopは起動しているが、コンテナが動いていない

**解決策**:
```powershell
# コンテナの状態を確認
docker ps -a

# Open WebUIを起動
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui

# ログを確認
docker logs open-webui
```

### 問題3: ポート3001が使用中

**解決策**:
```powershell
# ポート3001を使用しているプロセスを確認
netstat -ano | Select-String ":3001"

# 必要に応じて、docker-compose.ymlでポートを変更
# 例: 3002:8080 に変更
```

---

## 📋 起動確認コマンド

```powershell
# Dockerが起動しているか確認
docker ps

# Open WebUIコンテナの状態確認
docker ps | Select-String "open-webui"

# Open WebUIを起動
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui

# ログ確認
docker logs open-webui --tail 50
```

---

## ✅ 正常な状態

Docker Desktopが正常に起動している場合：

- ✅ タスクバーにDockerアイコンが表示される
- ✅ `docker ps` コマンドが実行できる
- ✅ Open WebUIコンテナが起動している
- ✅ `http://localhost:3001` にアクセスできる

---

**Docker Desktopを起動してから、再度 `http://localhost:3001` にアクセスしてください！**
