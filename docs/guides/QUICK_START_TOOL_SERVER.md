# 🚀 Tool Server クイックスタートガイド

## 📋 概要

OpenWebUI、Tool Server、ComfyUIの統合システムのクイックスタートガイドです。

---

## ✅ 前提条件

- Windows 10/11
- Python 3.8以上
- Docker Desktop（OpenWebUI用）
- ComfyUIインストール済み（`C:\ComfyUI`）

---

## 🚀 起動手順

### 1. 全サービスの状態確認

```powershell
.\check_all_services_status.ps1
```

**期待される結果:**
- Tool Server (Port 9503): [OK] Running
- ComfyUI (Port 8188): [OK] Running
- OpenWebUI (Port 3001): [OK] Running

### 2. サービスが起動していない場合

#### Tool Serverを起動

```powershell
.\START_TOOL_SERVER_HOST.ps1
```

#### ComfyUIを起動

```powershell
.\start_comfyui_svi.ps1 -Background
```

#### OpenWebUIを起動

```powershell
docker-compose up -d
```

---

## 🔧 自動起動設定

### Tool Serverの自動起動設定

```powershell
# 管理者権限で実行
.\setup_tool_server_auto_start.ps1
```

### ComfyUIの自動起動設定

```powershell
# 管理者権限で実行
.\setup_comfyui_auto_start.ps1
```

---

## 🌐 OpenWebUIでのTool Server使用

### 1. OpenWebUIにアクセス

```
http://127.0.0.1:3001
```

### 2. Tool Serverの登録確認

1. **左サイドバー → 設定（⚙️）**
2. **「外部ツール」をクリック**
3. **Tool Serverが登録されていることを確認**:
   - **URL**: `http://host.docker.internal:9503`
   - **OpenAPI URL**: `http://host.docker.internal:9503/openapi.json`
   - **状態**: Connected

### 3. ツールの使用

1. **チャット画面で「ツールの選択」をクリック**
2. **利用可能なツールを選択**:
   - `service_status` - Dockerコンテナの状態確認
   - `check_errors` - エラーログ確認
   - `generate_image` - ComfyUI経由で画像生成
3. **ツールを使用してリクエストを送信**

---

## 🧪 テスト

### 統合テスト実行

```powershell
python test_tool_server_integration.py
```

**期待される結果:**
```
[OK] すべてのテストが成功しました！
結果: 5 / 5 テストが成功
```

---

## 🔍 トラブルシューティング

### Tool Serverに接続できない場合

1. **Tool Serverが起動しているか確認**:
   ```powershell
   Invoke-WebRequest -Uri "http://127.0.0.1:9503/health"
   ```

2. **Tool Serverを再起動**:
   ```powershell
   .\START_TOOL_SERVER_HOST.ps1
   ```

### ComfyUIに接続できない場合

1. **ComfyUIが起動しているか確認**:
   ```powershell
   Invoke-WebRequest -Uri "http://127.0.0.1:8188"
   ```

2. **ComfyUIを起動**:
   ```powershell
   .\start_comfyui_svi.ps1 -Background
   ```

### OpenWebUIでツールが表示されない場合

1. **Tool Serverの登録状態を確認**
2. **OpenAPI仕様が取得できるか確認**:
   ```powershell
   Invoke-WebRequest -Uri "http://host.docker.internal:9503/openapi.json"
   ```

3. **OpenWebUIを再起動**:
   ```powershell
   docker-compose restart
   ```

---

## 📊 サービス情報

### Tool Server

- **ポート**: 9503
- **URL**: http://127.0.0.1:9503
- **OpenAPI**: http://127.0.0.1:9503/openapi.json
- **起動スクリプト**: `START_TOOL_SERVER_HOST.ps1`
- **自動起動設定**: `setup_tool_server_auto_start.ps1`

### ComfyUI

- **ポート**: 8188
- **URL**: http://127.0.0.1:8188
- **起動スクリプト**: `start_comfyui_svi.ps1`
- **自動起動設定**: `setup_comfyui_auto_start.ps1`

### OpenWebUI

- **ポート**: 3001
- **URL**: http://127.0.0.1:3001
- **起動方法**: `docker-compose up -d`

---

## 🔗 関連ドキュメント

- `TOOL_SERVER_INTEGRATION_COMPLETE.md` - 統合完了レポート
- `COMFYUI_AUTO_START_SUCCESS.md` - ComfyUI自動起動設定
- `OPENWEBUI_TOOL_SERVER_CONNECTION_GUIDE.md` - OpenWebUI接続ガイド

---

**レミ先輩モード**: クイックスタートガイド完成！これで簡単にシステム全体を起動できます！🔥
