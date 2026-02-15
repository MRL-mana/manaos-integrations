# ManaOS トラブルシューティングガイド

このガイドは、ManaOS統合環境での一般的な問題とその解決方法をまとめたものです。

## 目次

1. [環境変数の問題](#環境変数の問題)
2. [サービス接続の問題](#サービス接続の問題)
3. [ポート競合の問題](#ポート競合の問題)
4. [分散デプロイメントの問題](#分散デプロイメントの問題)
5. [パフォーマンスの問題](#パフォーマンスの問題)
6. [デバッグ方法](#デバッグ方法)

---

## 環境変数の問題

### 問題: 環境変数が認識されない

#### 症状
- 環境変数を設定したのに、デフォルトのlocalhostに接続される
- リモートサービスに接続できない

#### 解決方法

**Windows PowerShell:**
```powershell
# 現在のセッションでのみ有効
$env:OLLAMA_URL = "http://100.x.x.x:11434"

# 永続的に設定（ユーザープロファイル）
[System.Environment]::SetEnvironmentVariable("OLLAMA_URL", "http://100.x.x.x:11434", "User")

# PowerShellプロファイルに追加
notepad $PROFILE
# 以下を追加:
# $env:OLLAMA_URL = "http://100.x.x.x:11434"
```

**Linux/macOS:**
```bash
# 現在のセッションでのみ有効
export OLLAMA_URL="http://100.x.x.x:11434"

# 永続的に設定
echo 'export OLLAMA_URL="http://100.x.x.x:11434"' >> ~/.bashrc
source ~/.bashrc

# または ~/.profile に追加
```

#### 確認方法

**Windows:**
```powershell
# 環境変数が設定されているか確認
$env:OLLAMA_URL
Get-ChildItem Env: | Where-Object { $_.Name -like "*_URL" }
```

**Linux/macOS:**
```bash
# 環境変数が設定されているか確認
echo $OLLAMA_URL
env | grep _URL
```

---

## サービス接続の問題

### 問題: "Connection refused" エラー

#### 症状
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=11434): 
Max retries exceeded with url: / (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x...>: 
Failed to establish a new connection: [WinError 10061] 対象のコンピューターによって拒否されたため、接続できませんでした。'))
```

#### 原因
1. サービスが起動していない
2. ポート番号が間違っている
3. ファイアウォールがブロックしている

#### 解決方法

**1. サービスの起動確認**

```powershell
# Ollamaの起動確認
Get-Process -Name ollama -ErrorAction SilentlyContinue

# サービスが起動していない場合
ollama serve

# または ManaOS統合サービスを起動
python manaos_integrations/start_vscode_cursor_services.py
```

**2. ポートが正しく開いているか確認**

```powershell
# 指定ポートでリスニングしているプロセスを確認
netstat -ano | Select-String "11434"
Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
```

**3. ファイアウォールの確認（Windows）**

```powershell
# ファイアウォールルールを確認
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*ollama*" }

# 必要に応じてルールを追加
New-NetFirewallRule -DisplayName "Ollama Server" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow
```

**4. サービスヘルスチェックの実行**

```powershell
# テストスクリプトでサービス状態を確認
python test_service_health_checks.py
```

---

### 問題: タイムアウトエラー

#### 症状
```
requests.exceptions.ReadTimeout: HTTPConnectionPool(host='100.x.x.x', port=11434): 
Read timed out. (read timeout=30)
```

#### 原因
1. ネットワーク遅延（特にWAN経由）
2. サービスが過負荷状態
3. ファイアウォール/ルーターの設定

#### 解決方法

**1. タイムアウト時間を延長**

```python
# スクリプト内でタイムアウトを延長
import requests

response = requests.get(url, timeout=60)  # 60秒に延長
```

**2. Tailscaleの接続確認（分散環境）**

```powershell
# Tailscale接続状態の確認
tailscale status

# pingテスト
ping 100.x.x.x

# 特定ポートの疎通確認
Test-NetConnection -ComputerName 100.x.x.x -Port 11434
```

**3. サービスのパフォーマンス確認**

```powershell
# CPU/メモリ使用率
Get-Process -Name ollama | Select-Object CPU, WorkingSet

# 負荷が高い場合はサービスを再起動
Stop-Process -Name ollama
ollama serve
```

---

## ポート競合の問題

### 問題: "Address already in use" エラー

#### 症状
```
OSError: [WinError 10048] 通常、各ソケット アドレスに対してプロトコル、ネットワーク アドレス、またはポートのどれか 1 つのみを使用できます。
```

#### 解決方法

**1. ポートを使用しているプロセスを特定**

```powershell
# 特定ポートを使用しているプロセスID (PID) を確認
netstat -ano | Select-String ":8188"  # ComfyUIのポート例

# PIDからプロセス名を確認
Get-Process -Id <PID>

# プロセスを終了
Stop-Process -Id <PID> -Force
```

**2. 代替ポートを使用**

`_paths.py` を編集してポート番号を変更:

```python
# _paths.py
COMFYUI_PORT = 8189  # 8188から8189に変更
```

環境変数で上書きも可能:

```powershell
$env:COMFYUI_URL = "http://127.0.0.1:8189"
```

**3. マルチインスタンスのポート管理**

複数の開発環境を動かす場合:

```powershell
# 開発環境1（デフォルトポート）
# 環境変数なし、_paths.pyのデフォルトを使用

# 開発環境2（カスタムポート）
$env:OLLAMA_URL = "http://127.0.0.1:11435"
$env:COMFYUI_URL = "http://127.0.0.1:8189"
$env:MRL_MEMORY_URL = "http://127.0.0.1:5115"
```

---

## 分散デプロイメントの問題

### 問題: Tailscale経由で接続できない

#### 症状
- ローカル (127.0.0.1) では接続できるが、Tailscale IP (100.x.x.x) では接続できない

#### 解決方法

**1. Tailscale接続の確認**

```powershell
# Tailscale状態
tailscale status

# 接続テスト
ping 100.x.x.x
Test-NetConnection -ComputerName 100.x.x.x -Port 11434
```

**2. サービスのバインドアドレス確認**

多くのサービスはデフォルトで `127.0.0.1` にのみバインドします。すべてのインターフェースで待ち受けるように設定:

```powershell
# Ollamaの起動時に0.0.0.0でバインド
$env:OLLAMA_HOST = "0.0.0.0:11434"
ollama serve

# ComfyUIの場合
python main.py --listen 0.0.0.0 --port 8188
```

**3. ファイアウォール設定**

```powershell
# Tailscaleインターフェース経由の接続を許可
New-NetFirewallRule -DisplayName "ManaOS Ollama - Tailscale" `
    -Direction Inbound -Protocol TCP -LocalPort 11434 `
    -Action Allow -Profile Private

# または、Tailscaleネットワークからの全接続を許可
New-NetFirewallRule -DisplayName "ManaOS Services - Tailscale" `
    -Direction Inbound -Protocol TCP -LocalPort 5100-5200,8188,11434 `
    -Action Allow -RemoteAddress 100.0.0.0/8
```

**4. 追加設定例（_paths.py のコメント参照）**

`_paths.py` に記載された分散デプロイメント用の設定:

```python
# X280 (メインPC) でサービスを起動
# 環境変数なし、デフォルト (localhost) を使用

# Konoha (サブPC) から接続
import os
os.environ["OLLAMA_URL"] = "http://100.x.x.x:11434"  # X280のTailscale IP
os.environ["COMFYUI_URL"] = "http://100.x.x.x:8188"
os.environ["MRL_MEMORY_URL"] = "http://100.x.x.x:5105"
```

---

## パフォーマンスの問題

### 問題: レスポンスが遅い

#### 症状
- API呼び出しに時間がかかる
- タイムアウトが頻発する

#### 解決方法

**1. ネットワーク遅延の確認**

```powershell
# ping応答時間
ping 100.x.x.x

# より詳細な統計
Test-NetConnection -ComputerName 100.x.x.x -Port 11434 -InformationLevel Detailed
```

**2. サービスリソース確認**

```powershell
# CPU/メモリ/ディスク使用率
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10

# GPU使用率 (ComfyUIなど)
nvidia-smi
```

**3. ログの確認**

```powershell
# ManaOSログ
Get-Content logs/manaos_service_*.log -Tail 50

# Ollamaログ
Get-Content $env:USERPROFILE\.ollama\logs\server.log -Tail 50
```

**4. キャッシュとメモリ管理**

```python
# メモリキャッシュのクリア
import gc
gc.collect()
```

---

## デバッグ方法

### 基本的なデバッグ手順

**1. 環境変数の確認**

```python
# Python内で確認
import os
print("OLLAMA_URL:", os.getenv("OLLAMA_URL"))
print("COMFYUI_URL:", os.getenv("COMFYUI_URL"))

# すべてのManaOS関連環境変数を表示
for key, value in os.environ.items():
    if "_URL" in key or "_PORT" in key:
        print(f"{key}: {value}")
```

**2. ネットワーク接続のテスト**

```python
import requests

# 基本的な接続テスト
try:
    response = requests.get("http://127.0.0.1:11434", timeout=5)
    print(f"✅ 接続成功: {response.status_code}")
except Exception as e:
    print(f"❌ 接続失敗: {e}")
```

**3. 詳細ログの有効化**

```python
# requestsライブラリのデバッグログ
import logging
import http.client

http.client.HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

**4. テストスクリプトの実行**

```powershell
# 環境変数テスト
python test_environment_variables.py

# サービスヘルスチェック
python test_service_health_checks.py

# 統合サービス状態確認
python check_integration_status.py
```

### 診断チェックリスト

問題が発生した場合、以下を順番に確認:

- [ ] サービスが起動しているか (`Get-Process`, `ps -ef | grep`)
- [ ] ポートが開いているか (`netstat -ano`, `lsof -i`)
- [ ] 環境変数が正しく設定されているか (`$env:VAR_NAME`, `echo $VAR_NAME`)
- [ ] ファイアウォールがブロックしていないか
- [ ] ネットワーク接続があるか (`ping`, `Test-NetConnection`)
- [ ] ログにエラーメッセージがないか
- [ ] ディスク容量/メモリは十分か

### よくある設定ミス

1. **環境変数にスペースが含まれている**
   ```powershell
   # ❌ 間違い
   $env:OLLAMA_URL = " http://127.0.0.1:11434"
   
   # ✅ 正しい
   $env:OLLAMA_URL = "http://127.0.0.1:11434"
   ```

2. **URLの末尾にスラッシュがある/ない**
   ```powershell
   # どちらでもOK（コード内で.rstrip('/')処理）
   $env:OLLAMA_URL = "http://127.0.0.1:11434"
   $env:OLLAMA_URL = "http://127.0.0.1:11434/"
   ```

3. **http/httpsの間違い**
   ```powershell
   # ❌ 多くのローカルサービスはHTTPのみ
   $env:OLLAMA_URL = "https://127.0.0.1:11434"
   
   # ✅ 正しい
   $env:OLLAMA_URL = "http://127.0.0.1:11434"
   ```

4. **ポート番号の間違い**
   ```python
   # _paths.py で定義されているポートを確認
   OLLAMA_PORT = 11434
   COMFYUI_PORT = 8188
   MRL_MEMORY_PORT = 5105
   ```

---

## サポート情報

### ログファイルの場所

```
Desktop/
├── logs/                          # メインログディレクトリ
│   ├── manaos_service_*.log      # サービス統合ログ
│   └── ollama/                    # Ollama固有ログ
└── manaos_integrations/
    └── logs/                      # 統合サービスログ
```

### 設定ファイルの場所

```
manaos_integrations/
├── _paths.py                      # ポート定数定義
├── ENVIRONMENT_VARIABLES.md       # 環境変数ガイド
└── TROUBLESHOOTING.md             # このファイル
```

### GitHub Issues

問題が解決しない場合は、以下の情報を含めてissueを作成してください:

1. エラーメッセージの全文
2. 実行したコマンド/スクリプト
3. 環境情報（OS、Pythonバージョン）
4. `test_environment_variables.py` の出力
5. `test_service_health_checks.py` の出力
6. 関連ログファイルの抜粋

---

## 関連ドキュメント

- [README.md](README.md) - プロジェクト概要
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - 環境変数詳細ガイド
- [DISTRIBUTED_DEPLOYMENT.md](DISTRIBUTED_DEPLOYMENT.md) - 分散デプロイメント設定例
