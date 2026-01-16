# ピクセル7（Android端末）ManaOS統合ガイド

## 概要

ピクセル7（Android端末）をManaOSのリモートノードとして統合し、以下の機能を提供します：

- ピクセル7のリソース監視（メモリ、ストレージ、バッテリー）
- Android shellコマンドの実行
- ピクセル7とのファイル転送（ADB経由）
- アプリケーション管理
- ManaOS Portalからのピクセル7管理

## 注意事項

**重要**: 
- **ピクセル7 = Android端末（スマートフォン）**
- **X280 = Windows PC（ThinkPad）**

これらは別々のデバイスです。X280用の統合は `X280_INTEGRATION_GUIDE.md` を参照してください。

## アーキテクチャ

```
ManaOS (このはサーバー)
  ├─ Pixel7 Node Manager (ポート 5123)
  │   ├─ リソース監視
  │   ├─ Androidコマンド実行
  │   └─ ファイル転送（ADB）
  │
  └─ Portal Integration
      └─ ピクセル7管理画面

ピクセル7 (Android端末)
  └─ Pixel7 API Gateway (ポート 5122)
      ├─ Android shellコマンド実行API
      ├─ リソース監視API
      └─ アプリ管理API
```

## セットアップ手順

### 1. ピクセル7側のセットアップ

#### 1.1 Termuxのインストール

ピクセル7にTermuxをインストール：

1. F-DroidからTermuxをインストール
   - https://f-droid.org/packages/com.termux/
2. Termuxを起動して初期設定

#### 1.2 TermuxでPython環境をセットアップ

```bash
# Termuxで実行
pkg update
pkg install python
pip install fastapi uvicorn httpx
```

#### 1.3 API Gatewayファイルを転送

このはサーバーからピクセル7にファイルを転送：

```bash
# このはサーバーで実行
# ADB経由で転送（ピクセル7がUSB接続されている場合）
adb push manaos_integrations/pixel7_api_gateway.py /sdcard/Download/

# または、Tailscale経由でSSH接続できる場合
scp manaos_integrations/pixel7_api_gateway.py pixel7:/sdcard/Download/
```

Termuxでファイルを移動：

```bash
# Termuxで実行
cp /sdcard/Download/pixel7_api_gateway.py ~/
cd ~
```

#### 1.4 API Gatewayの起動

```bash
# Termuxで実行
python pixel7_api_gateway.py
```

#### 1.5 バックグラウンド実行（Termux:Taskerを使用）

Termux:Taskerをインストールして、バックグラウンドで実行：

```bash
# Termuxで実行
pkg install termux-api
```

または、`nohup`を使用：

```bash
nohup python pixel7_api_gateway.py > /dev/null 2>&1 &
```

### 2. ADB接続の設定

#### 2.1 USB接続の場合

```bash
# このはサーバーで実行
adb devices
adb tcpip 5555
adb connect 100.127.121.20:5555
```

#### 2.2 ワイヤレスADB接続

ピクセル7で開発者オプションを有効化：
1. 設定 > デバイス情報 > ビルド番号を7回タップ
2. 設定 > 開発者オプション > USBデバッグを有効化
3. ワイヤレスデバッグを有効化

```bash
# このはサーバーで実行
adb connect 100.127.121.20:5555
```

### 3. ManaOS側のセットアップ

#### 3.1 Pixel7 Node Managerの起動

このはサーバーで実行：

```bash
cd /root/manaos_integrations
python pixel7_node_manager.py
```

#### 3.2 systemdサービスとして登録

```bash
# サービスファイルを作成
sudo nano /etc/systemd/system/pixel7-node-manager.service
```

```ini
[Unit]
Description=Pixel7 Node Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/manaos_integrations
Environment="PIXEL7_HOST=100.127.121.20"
Environment="PIXEL7_API_PORT=5122"
Environment="PIXEL7_ADB_PORT=5555"
Environment="PIXEL7_NODE_MANAGER_PORT=5123"
ExecStart=/usr/bin/python3 /root/manaos_integrations/pixel7_node_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# サービスを有効化して起動
sudo systemctl daemon-reload
sudo systemctl enable pixel7-node-manager
sudo systemctl start pixel7-node-manager
sudo systemctl status pixel7-node-manager
```

## 使用方法

### API経由での操作

#### ピクセル7でコマンドを実行

```bash
curl -X POST http://localhost:5123/api/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "getprop ro.product.model", "timeout": 10}'
```

#### ピクセル7のリソース情報を取得

```bash
curl http://localhost:5123/api/resources
```

#### ファイル転送

```bash
# ローカルからピクセル7へアップロード
curl -X POST http://localhost:5123/api/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/root/test.txt",
    "remote_path": "/sdcard/Download/test.txt",
    "direction": "upload"
  }'

# ピクセル7からローカルへダウンロード
curl -X POST http://localhost:5123/api/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/root/downloaded.txt",
    "remote_path": "/sdcard/Download/test.txt",
    "direction": "download"
  }'
```

### Pythonコードからの使用

```python
import httpx

# Pixel7 Node Managerに接続
async with httpx.AsyncClient() as client:
    # ステータス確認
    response = await client.get("http://localhost:5123/api/status")
    print(response.json())
    
    # Androidコマンド実行
    response = await client.post(
        "http://localhost:5123/api/execute",
        json={"command": "getprop ro.product.model", "timeout": 10}
    )
    print(response.json())
    
    # リソース情報取得
    response = await client.get("http://localhost:5123/api/resources")
    print(response.json())
```

## Androidコマンドの例

### システム情報取得

```bash
# デバイスモデル
getprop ro.product.model

# Androidバージョン
getprop ro.build.version.release

# メモリ情報
cat /proc/meminfo

# バッテリー情報
dumpsys battery
```

### アプリケーション管理

```bash
# インストール済みアプリ一覧
pm list packages

# アプリ起動
am start -n com.example.app/.MainActivity

# アプリ停止
am force-stop com.example.app
```

### ファイル操作

```bash
# ファイル一覧
ls /sdcard/Download

# ファイルコピー
cp /sdcard/Download/file.txt /sdcard/DCIM/

# ファイル削除
rm /sdcard/Download/file.txt
```

## トラブルシューティング

### ADB接続できない

1. **USBデバッグの確認**
   - 設定 > 開発者オプション > USBデバッグが有効か確認

2. **ADB接続確認**
   ```bash
   adb devices
   ```

3. **ワイヤレスADB接続**
   ```bash
   adb connect 100.127.121.20:5555
   ```

### API Gatewayに接続できない

1. **TermuxでAPI Gatewayが起動しているか確認**
   ```bash
   # Termuxで実行
   ps aux | grep pixel7_api_gateway
   ```

2. **ポートが開いているか確認**
   ```bash
   # Termuxで実行
   netstat -an | grep 5122
   ```

3. **ファイアウォール設定**
   - Termuxのファイアウォール設定を確認
   - Tailscaleネットワーク内からのアクセスを許可

### コマンド実行が失敗する

- Androidの権限が必要なコマンドは実行できない場合があります
- `su`権限が必要な場合は、root化が必要です

## セキュリティ考慮事項

1. **ADB接続の保護**
   - ワイヤレスADB接続はセキュアなネットワーク（Tailscale）でのみ使用
   - 不要な場合はUSB接続のみを使用

2. **API Gatewayの認証**
   - 本番環境では認証トークンを追加
   - Tailscaleネットワーク内のみアクセス可能にする

3. **権限管理**
   - 実行するコマンドを制限
   - 危険なコマンドは実行前に確認

## X280との違い

| 項目 | ピクセル7（Android） | X280（Windows） |
|------|---------------------|-----------------|
| OS | Android | Windows |
| コマンド | Android shell | PowerShell/CMD |
| ファイル転送 | ADB | SCP |
| API Gateway | Termux上で実行 | Windows上で実行 |
| ポート | 5122 | 5120 |
| Node Manager | 5123 | 5121 |

## 今後の拡張

- [ ] ピクセル7でのスクリーンショット取得
- [ ] アプリケーションの自動起動制御
- [ ] 通知の送信・受信
- [ ] センサーデータの取得
- [ ] カメラ制御
- [ ] ManaOS Portalへの統合UI

## 参考

- [X280統合ガイド](./X280_INTEGRATION_GUIDE.md) - Windows PC用
- [ManaOS完全ドキュメント](./MANAOS_COMPLETE_DOCUMENTATION.md)
- [Termux公式サイト](https://termux.com/)
- [ADB公式ドキュメント](https://developer.android.com/studio/command-line/adb)

