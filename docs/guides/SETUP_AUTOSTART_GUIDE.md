# Docker自動起動設定ガイド

**作成日**: 2026-01-28

---

## 📋 設定手順

### Step 1: 管理者権限でPowerShellを開く

1. Windowsキーを押す
2. "PowerShell"と入力
3. "Windows PowerShell"を右クリック
4. **"管理者として実行"**を選択

### Step 2: プロジェクトディレクトリに移動

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
```

### Step 3: docker-compose自動起動タスクを設定

```powershell
.\setup_docker_autostart.ps1
```

### Step 4: 確認

```powershell
# 自動起動設定状況を確認
.\check_autostart_status.ps1

# または、タスクを直接確認
Get-ScheduledTask -TaskName "ManaOS-Docker-Compose-AutoStart"
```

---

## 🔍 設定される内容

### タスク名
- `ManaOS-Docker-Compose-AutoStart`

### トリガー
- ログオン時（2分遅延）
- システム起動時（2分遅延）

### 実行内容
- `docker-compose -f docker-compose.manaos-services.yml up -d`

### 遅延の理由
- Docker Desktopの起動を待つため、2分の遅延を設定

---

## ⚠️ 注意事項

1. **管理者権限が必要**
   - このスクリプトは管理者権限で実行する必要があります

2. **Docker Desktopの自動起動**
   - Docker Desktop自体も自動起動を有効化する必要があります
   - Docker Desktop → Settings → General → "Start Docker Desktop when you log in" を有効化

3. **実行順序**
   - Docker Desktopが起動してから、docker-composeが実行されます（2分遅延）

---

## 🚀 動作確認

### PC再起動後の確認

1. PCを再起動
2. 2分以上待つ（Docker Desktopの起動とコンテナの起動を待つ）
3. 以下で確認：

```powershell
# 実行中のコンテナを確認
docker ps

# または、自動起動設定状況を確認
.\check_autostart_status.ps1
```

---

## 🗑️ 削除方法

自動起動タスクを削除する場合：

```powershell
# 管理者権限でPowerShellを開く
cd C:\Users\mana4\Desktop\manaos_integrations
.\setup_docker_autostart.ps1 -Remove
```

---

## 📝 まとめ

### 現在の状態

- ✅ Docker Composeのrestart設定: 完了
- ⚠️ Docker Desktopの自動起動: 確認が必要（Docker Desktopの設定で有効化）
- ⚠️ docker-compose自動起動タスク: 設定スクリプト作成済み（実行が必要）

### 推奨される次のステップ

1. **管理者権限でPowerShellを開く**
2. **docker-compose自動起動タスクを設定**（`.\setup_docker_autostart.ps1`を実行）
3. **Docker Desktopの自動起動を有効化**（Docker Desktopの設定から）
4. **確認**（`.\check_autostart_status.ps1`を実行）

これにより、システム再起動後、自動的にすべてのコンテナが起動します。

---

**作成日**: 2026-01-28
