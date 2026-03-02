# ピクセル7（Android端末）ManaOS統合ガイド

## クイックスタート: 5122 を Pixel 7 で使う

### 方法A: 母艦で ADB ブリッジ（USB 接続時）

Pixel 7 を USB で接続した状態で、母艦で以下を実行すると **localhost:5122** で Pixel 7 用 API が使えます（Termux 不要）。

```powershell
.\start_pixel7_bridge.ps1
# または ダブルクリック: start_pixel7_bridge.bat
```

オプション一覧（`start_all_optionals.ps1`）の **6. Pixel 7 ADB ブリッジ** でも起動できます。

### 方法A': Tailscale 経由（無線）でブリッジを使う

**初回だけ** USB で接続した状態で:

```powershell
.\scripts\setup_pixel7_tailscale_adb.ps1
```

その後、**ケーブルを外して** Tailscale がオンなら:

```powershell
.\start_pixel7_bridge_tailscale.ps1
```

- Pixel 7a の Tailscale IP は `100.84.2.125`（変更時は `$env:PIXEL7_TAILSCALE_IP` で指定）。
- 再起動後は再度 USB で一度 `setup_pixel7_tailscale_adb.ps1` を実行すると Tailscale ADB が復活します。

### 方法A'': Wireless debugging（USB なし・再起動後もセットアップ不要）

**Android 11 以降**の「Wireless debugging」を使うと、**USB 不要・再起動後も再接続だけで使えます**（ペアリングは初回のみ）。

**一括セットアップ（推奨）**:

```powershell
.\scripts\setup_pixel7_usb_free.ps1
```

上記で「端末で Wireless debugging を有効化 → ペアリング → ログオン時自動起動（任意）」まで案内されます。

**手順だけ行う場合**:

1. **Pixel 7 側（1回だけ）**: 設定 > 開発者向けオプション > **Wireless debugging** を ON。同画面で「ペアリングコードでデバイスとペア設定」の **IP:ポート** と **6桁コード** をメモ（Tailscale 利用時は接続先 IP は Tailscale IP を使用）。
2. **母艦で初回セットアップ（USB 不要）**: `.\scripts\setup_pixel7_wireless_debugging.ps1` を実行し、ペアリング用ポートとコードを入力。
3. **以降（再起動後も）**: `.\start_pixel7_bridge_tailscale.ps1` でブリッジ起動。ログオン時自動起動を入れておけば PC 再起動後も自動で接続されます。

- 再起動後も端末の「Wireless debugging」は ON のままなので、**再度セットアップは不要**です。
- 接続用ポートが 5555 でない場合は `$env:PIXEL7_ADB_PORT='ポート'` を指定してください。

### 方法B: Pixel 7 の Termux で 5122 を起動する

**Pixel 7a の Tailscale IP**: `100.84.2.125`（デバイスオーケストレーター・Node Manager の設定済み）

1. **Pixel 7 に Termux をインストール**（F-Droid 推奨）
2. **Termux で依存関係を入れる**
   ```bash
   pkg update && pkg install python
   pip install fastapi uvicorn
   ```
3. **母艦から `pixel7_api_gateway.py` を転送**
   ```bash
   adb push pixel7_api_gateway.py /sdcard/Download/
   ```
   Termux 側: `cp /sdcard/Download/pixel7_api_gateway.py ~/ && cd ~`
4. **5122 で起動**（Tailscale オンにした状態で）
   ```bash
   export PIXEL7_API_PROFILE=core
   python pixel7_api_gateway.py
   ```
   （デフォルトで `0.0.0.0:5122` で待ち受け。バックグラウンド: `nohup python pixel7_api_gateway.py > /dev/null 2>&1 &`）

> `PIXEL7_API_PROFILE=core` は安全デフォルトです（読み取り系中心）。
> 端末操作系（`/api/open/*`, `/api/macro/broadcast`, `/api/execute`）を使う時だけ `full` に切り替えてください。

起動後、母艦から `http://100.84.2.125:5122/health` にアクセスできればオーケストレーターに「Pixel 7 オンライン」と表示されます。

### 運用を楽にする（自動起動）

- **ログオン時に自動起動**: `scripts\install_pixel7_bridge_autostart.ps1` を**管理者として実行**すると、タスクスケジューラに「ログオン時に Pixel 7 ブリッジを起動」するタスクを登録します。権限不足の場合は手動で `.\start_pixel7_bridge.ps1` または start_all_optionals.ps1 の 6 を利用してください。
- **手動**: `.\start_pixel7_bridge.ps1` または **start_all_optionals.ps1** の **6**。
- **自動切替（Tailscale 優先）**: `.\start_pixel7_bridge_auto.ps1` で、Tailscale がつながっていれば無線、なければ USB で起動。
- **再起動後もセットアップ不要**: 方法A''（Wireless debugging）で初回ペアリングしておくと、再起動後は `start_pixel7_bridge_tailscale.ps1` を実行するだけでよい。
- **Pixel 7 を実際に使うテスト**: `python scripts\test_pixel7_usage.py`（システム情報・リソース・コマンド実行を確認）。
- **全デバイス接続確認**: `.\scripts\check_devices_online.ps1`。他デバイスの起動手順は [DEVICES_ONLINE_SETUP.md](./DEVICES_ONLINE_SETUP.md) を参照。
- **MCP ツール**: Cursor から `pixel7_execute`（コマンド実行）・`pixel7_get_resources`（リソース取得）・`pixel7_screenshot`（スクリーンショット）・`pixel7_get_apps`（アプリ一覧）が利用可能です。
- **クイック起動**: `quick_start_devices.bat` で Pixel 7 ブリッジを起動できます。
- **最小CLI**: `python scripts/pixel7/manaos_pixel7_cli.py health|status|open-url <url>`
- **5分セキュア導線**: [PIXEL7_MINIMAL_SECURE_MODE.md](./PIXEL7_MINIMAL_SECURE_MODE.md)

### ManaOS への取り込み（統合API・意図分類）

- **統合API（Unified API Server）**: 次のエンドポイントが利用可能です（ブリッジ 5122 起動時）。
  - `GET /api/devices/status` … 全デバイス状態（オーケストレーター経由）
  - `GET /api/pixel7/resources` … Pixel 7 のバッテリー・メモリ等
  - `POST /api/pixel7/execute` … Pixel 7 でコマンド実行（body: `{"command": "..."}`）
  - **音声出力（TTS）**: `POST /api/pixel7/tts` … テキストをサーバーで合成し、端末に転送して再生。音声統合（TTS）要。
  - **音声入力（文字起こし）**: `POST /api/pixel7/transcribe` … 端末上の録音ファイル（`remote_path`）を取得してサーバーでSTT。音声統合（STT）要。録音は端末のボイスレコーダー等で行い、保存先パス（例: `/sdcard/Download/rec.wav`）を指定。
- **音声のリアルタイム（Pixel 7 ＋ 母艦）**: リアルタイムの「話す→認識→応答→再生」は**母艦をサーバー・Pixel 7 をクライアント**とする構成で利用できます（単体の Pixel 7 ではなく、母艦も使う想定）。
  1. **母艦で** `scripts\voice\start_pixel7_realtime_voice.bat` を実行して WebSocket 8765 と HTTP 8766 を一括起動（推奨）。または手動で `voice_realtime_streaming.py` と `python scripts/voice/serve_voice_client.py` を起動する。
  2. **Pixel 7 のブラウザで** `http://<母艦のIP>:8766` を開く。
  3. 画面の「母艦 WebSocket URL」に `ws://<母艦のIP>:8765` を入力して「開始」し、マイク許可後に「レミ」のあとで話しかける。
  - 母艦は `VOICE_WEBSOCKET_HOST=0.0.0.0` で起動すること（同一 LAN や Tailscale で Pixel 7 からアクセス可能にする）。
  - バッチ運用のみ使う場合は `POST /api/pixel7/tts` と `POST /api/pixel7/transcribe` を利用。詳しくは [voice_advanced_features.md](../voice_advanced_features.md) を参照。
- **コンパニオンモード（X風UI）**: テキスト＋音声＋TTS を統合した常設UI。
  1. **母艦で** 統合API（9500）を起動。
  2. **音声入力を使う場合** `scripts\voice\start_pixel7_realtime_voice.bat` で WebSocket 8765 を起動。
  3. **Pixel 7 のブラウザで** `http://<母艦のIP>:9502/companion` を開く。
  4. テキスト入力・マイクボタン（音声）で会話し、応答を Pixel 7 で読み上げ可能。
- **意図分類（Intent Router）**: 「Pixel 7 のバッテリー教えて」「デバイス状態」などは `device_status` 意図に分類されます。キーワード: Pixel 7、ピクセル7、バッテリー、デバイス、オンライン、スマホ、端末、リソース。
- **OpenAPI**: `unified_api/openapi.py` に上記パスが定義されており、Open WebUI External Tools 等から呼び出せます。
- **母艦の操作**: 統合API で `GET /api/mothership/resources`（CPU・メモリ・ディスク）と `POST /api/mothership/execute`（ローカルコマンド実行）が利用可能です。MCP では `mothership_get_resources`・`mothership_execute` で同じ機能を呼び出せます。母艦のマウス/キーボード/スクショは Pico HID の `pico_hid_*` ツールで操作できます。

---

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
adb connect 100.84.2.125:5555
```

#### 2.2 ワイヤレスADB接続

ピクセル7で開発者オプションを有効化：
1. 設定 > デバイス情報 > ビルド番号を7回タップ
2. 設定 > 開発者オプション > USBデバッグを有効化
3. ワイヤレスデバッグを有効化

```bash
# このはサーバーで実行
adb connect 100.84.2.125:5555
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
Environment="PIXEL7_HOST=100.84.2.125"
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
curl -X POST http://127.0.0.1:5123/api/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "getprop ro.product.model", "timeout": 10}'
```

#### ピクセル7のリソース情報を取得

```bash
curl http://127.0.0.1:5123/api/resources
```

#### ファイル転送

```bash
# ローカルからピクセル7へアップロード
curl -X POST http://127.0.0.1:5123/api/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/root/test.txt",
    "remote_path": "/sdcard/Download/test.txt",
    "direction": "upload"
  }'

# ピクセル7からローカルへダウンロード
curl -X POST http://127.0.0.1:5123/api/transfer \
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
    response = await client.get("http://127.0.0.1:5123/api/status")
    print(response.json())

    # Androidコマンド実行
    response = await client.post(
        "http://127.0.0.1:5123/api/execute",
        json={"command": "getprop ro.product.model", "timeout": 10}
    )
    print(response.json())

    # リソース情報取得
    response = await client.get("http://127.0.0.1:5123/api/resources")
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
   adb connect 100.84.2.125:5555
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
