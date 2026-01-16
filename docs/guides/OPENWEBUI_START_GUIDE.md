# 🚀 OpenWebUI 起動ガイド

## 📋 前提条件

1. **Docker Desktopが起動していること**
   - タスクバーまたはスタートメニューから起動
   - 起動完了まで数秒～数分かかります

## 🔧 起動手順

### Step 1: Docker Desktopを起動

1. Windowsのタスクバーまたはスタートメニューから「Docker Desktop」を起動
2. 起動完了まで待機（タスクトレイのDockerアイコンが緑色になるまで）

### Step 2: プロジェクトディレクトリに移動

PowerShellまたはコマンドプロンプトで：

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
```

### Step 3: OpenWebUIコンテナを起動

```powershell
docker-compose -f docker-compose.always-ready-llm.yml up -d openwebui
```

### Step 4: 起動確認

ブラウザで以下のURLにアクセス：

```
http://localhost:3001
```

## 🐛 トラブルシューティング

### エラー: "The system cannot find the file specified"

**原因**: 現在のディレクトリがプロジェクトディレクトリではない

**解決方法**:
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
```

### エラー: "open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified"

**原因**: Docker Desktopが起動していない

**解決方法**:
1. Docker Desktopを起動
2. 起動完了まで待機
3. 再度コマンドを実行

### エラー: "unable to get image"

**原因**: インターネット接続の問題、またはDocker Desktopが完全に起動していない

**解決方法**:
1. Docker Desktopが完全に起動しているか確認
2. インターネット接続を確認
3. 少し待ってから再度実行

## 📋 便利なコマンド

### ログを確認

```powershell
docker-compose -f docker-compose.always-ready-llm.yml logs openwebui
```

### コンテナの状態を確認

```powershell
docker-compose -f docker-compose.always-ready-llm.yml ps openwebui
```

### コンテナを停止

```powershell
docker-compose -f docker-compose.always-ready-llm.yml stop openwebui
```

### コンテナを再起動

```powershell
docker-compose -f docker-compose.always-ready-llm.yml restart openwebui
```

## 🎯 次のステップ

OpenWebUIが起動したら：

1. **External Tools設定**
   - 詳細: `OPENWEBUI_EXTERNAL_TOOLS_SETUP.md` を参照

2. **Tool Serverの設定**
   - Tool Serverは既に起動中（ポート9503）
   - OpenWebUIからTool Serverを登録

---

**レミ先輩モード**: Docker Desktopを起動してから、正しいディレクトリでコマンドを実行するだけ！🔥
