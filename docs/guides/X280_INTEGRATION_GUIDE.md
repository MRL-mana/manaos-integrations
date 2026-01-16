# ピクセル7 ManaOS統合ガイド

## 概要

ピクセル7をManaOSのリモートノードとして統合し、以下の機能を提供します：

- X280のリソース監視（CPU、メモリ、ディスク）
- X280でのリモートコマンド実行
- X280とのファイル転送
- X280のプロセス管理
- ManaOS PortalからのX280管理

## アーキテクチャ

```
ManaOS (このはサーバー)
  ├─ Pixel7 Node Manager (ポート 5121)
  │   ├─ リソース監視
  │   ├─ コマンド実行
  │   └─ ファイル転送
  │
  └─ Portal Integration
      └─ ピクセル7管理画面

ピクセル7
  └─ Pixel7 API Gateway (ポート 5120)
      ├─ コマンド実行API
      ├─ リソース監視API
      └─ ファイル操作API
```

## セットアップ手順

### 1. X280側のセットアップ

#### 1.1 X280 API Gatewayのインストール

X280にSSH接続して、API Gatewayをインストール：

```powershell
# X280に接続
ssh x280

# 作業ディレクトリを作成
mkdir C:\manaos_x280
cd C:\manaos_x280

# ファイルを転送（このはサーバーから）
# このはサーバー側で実行:
scp manaos_integrations/x280_api_gateway.py x280:C:/manaos_x280/
scp manaos_integrations/requirements.txt x280:C:/manaos_x280/
```

#### 1.2 Python環境のセットアップ

X280でPython環境をセットアップ：

```powershell
# Pythonがインストールされているか確認
python --version

# 仮想環境を作成（推奨）
python -m venv venv
.\venv\Scripts\Activate.ps1

# 必要なパッケージをインストール
pip install fastapi uvicorn httpx
```

#### 1.3 X280 API Gatewayの起動

```powershell
# X280で実行
cd C:\manaos_x280
python x280_api_gateway.py
```

#### 1.4 Windowsサービスとして登録（オプション）

常時起動する場合は、Windowsサービスとして登録：

```powershell
# NSSMを使用してサービス登録
# NSSMをダウンロード: https://nssm.cc/download

nssm install X280APIGateway "C:\manaos_x280\venv\Scripts\python.exe" "C:\manaos_x280\x280_api_gateway.py"
nssm set X280APIGateway AppDirectory "C:\manaos_x280"
nssm start X280APIGateway
```

### 2. ManaOS側のセットアップ

#### 2.1 X280 Node Managerの起動

このはサーバーで実行：

```bash
cd /root/manaos_integrations
python x280_node_manager.py
```

#### 2.2 systemdサービスとして登録

```bash
# サービスファイルを作成
sudo nano /etc/systemd/system/x280-node-manager.service
```

```ini
[Unit]
Description=X280 Node Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/manaos_integrations
Environment="X280_HOST=x280"
Environment="X280_USER=mana"
Environment="X280_PORT=22"
Environment="X280_API_PORT=5120"
Environment="X280_TAILSCALE_IP=100.127.121.20"
Environment="X280_NODE_MANAGER_PORT=5121"
ExecStart=/usr/bin/python3 /root/manaos_integrations/x280_node_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# サービスを有効化して起動
sudo systemctl daemon-reload
sudo systemctl enable x280-node-manager
sudo systemctl start x280-node-manager
sudo systemctl status x280-node-manager
```

### 3. 接続確認

#### 3.1 X280 API Gatewayの確認

```bash
# このはサーバーから
curl http://100.127.121.20:5120/
```

#### 3.2 X280 Node Managerの確認

```bash
# このはサーバーから
curl http://localhost:5121/api/status
```

## 使用方法

### API経由での操作

#### X280でコマンドを実行

```bash
curl -X POST http://localhost:5121/api/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "powershell.exe -Command \"Get-Process | Select-Object -First 5\"", "timeout": 30}'
```

#### X280のリソース情報を取得

```bash
curl http://localhost:5121/api/resources
```

#### ファイル転送

```bash
# ローカルからX280へアップロード
curl -X POST http://localhost:5121/api/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/root/test.txt",
    "remote_path": "C:/temp/test.txt",
    "direction": "upload"
  }'

# X280からローカルへダウンロード
curl -X POST http://localhost:5121/api/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/root/downloaded.txt",
    "remote_path": "C:/temp/test.txt",
    "direction": "download"
  }'
```

### Pythonコードからの使用

```python
import httpx

# X280 Node Managerに接続
async with httpx.AsyncClient() as client:
    # ステータス確認
    response = await client.get("http://localhost:5121/api/status")
    print(response.json())
    
    # コマンド実行
    response = await client.post(
        "http://localhost:5121/api/execute",
        json={"command": "hostname", "timeout": 10}
    )
    print(response.json())
    
    # リソース情報取得
    response = await client.get("http://localhost:5121/api/resources")
    print(response.json())
```

## ManaOS Portalへの統合

ManaOS PortalにX280管理画面を追加する場合は、`portal_integration_api.py` に以下を追加：

```python
# X280 Node Managerへの接続
X280_NODE_MANAGER_URL = "http://localhost:5121"

@app.get("/api/x280/status")
async def get_x280_status():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{X280_NODE_MANAGER_URL}/api/status")
        return response.json()
```

## トラブルシューティング

### X280に接続できない

1. **Tailscale接続の確認**
   ```bash
   # このはサーバーから
   ping 100.127.121.20
   ```

2. **SSH接続の確認**
   ```bash
   ssh x280 "echo test"
   ```

3. **X280 API Gatewayの確認**
   ```bash
   curl http://100.127.121.20:5120/api/health
   ```

### コマンド実行がタイムアウトする

- `timeout` パラメータを増やす
- X280側のリソース使用状況を確認

### ファイル転送が失敗する

- パスの確認（Windows形式: `C:/path/to/file`）
- 権限の確認
- ディレクトリの存在確認

## セキュリティ考慮事項

1. **認証の追加**
   - API Gatewayに認証トークンを追加
   - SSH鍵認証を使用

2. **ファイアウォール設定**
   - X280側でポート5120を適切に制限
   - Tailscaleネットワーク内のみアクセス可能にする

3. **ログ監視**
   - 実行されたコマンドをログに記録
   - 異常なアクセスを検出

## 今後の拡張

- [ ] X280でのスクリーンショット取得
- [ ] X280でのアプリケーション起動制御
- [ ] X280のイベントログ監視
- [ ] X280での自動化タスク実行
- [ ] ManaOS Portalへの統合UI

## 参考

- [ManaOS完全ドキュメント](./MANAOS_COMPLETE_DOCUMENTATION.md)
- [X280再起動問題調査](./X280_REBOOT_ANALYSIS.md)

