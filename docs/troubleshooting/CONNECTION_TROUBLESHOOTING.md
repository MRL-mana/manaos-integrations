# 🔥 接続トラブルシューティングガイド（完全版）

## ❌ 問題: 接続できない

OpenWebUIの「外部ツール」設定画面でTool Serverを登録しても、接続できない、またはツールが表示されない場合のトラブルシューティングガイドです。

---

## 🔍 Step 1: Tool Serverの状態確認

### 1-1. Tool Serverが起動しているか確認

```powershell
# Tool Serverのヘルスチェック
curl http://localhost:9503/health
```

**期待される結果:**
```json
{"status":"healthy","service":"manaOS Tool Server","timestamp":"..."}
```

**問題がある場合:**
- Tool Serverが起動していない → Tool Serverを起動
- ポート9503が使用中 → 別のポートを使用するか、競合するプロセスを停止

### 1-2. OpenAPI仕様が取得できるか確認

```powershell
# OpenAPI仕様の取得
curl http://localhost:9503/openapi.json
```

**期待される結果:**
- JSON形式のOpenAPI仕様が返される
- `service_status`, `check_errors`, `generate_image` が含まれている

---

## 🔍 Step 2: OpenWebUIコンテナからTool Serverへの接続確認

### 2-1. OpenWebUIコンテナ内からcurlで確認

```powershell
# OpenWebUIコンテナ名を確認
docker ps --filter "name=openwebui" --format "{{.Names}}"

# OpenWebUIコンテナ内からTool Serverに接続
docker exec open-webui curl http://host.docker.internal:9503/health
```

**期待される結果:**
```json
{"status":"healthy","service":"manaOS Tool Server","timestamp":"..."}
```

**問題がある場合:**
- `curl: (6) Could not resolve host: host.docker.internal`
  - Docker Desktopの設定を確認
  - Windowsのネットワーク設定を確認
- `curl: (7) Failed to connect to host.docker.internal port 9503`
  - Tool Serverが起動していない可能性
  - ファイアウォールがブロックしている可能性

### 2-2. 代替案: WindowsのIPアドレスを直接指定

```powershell
# WindowsのIPアドレスを確認
ipconfig

# IPv4アドレスを確認（例: 192.168.0.10）
# OpenWebUIコンテナ内から接続確認
docker exec open-webui curl http://192.168.0.10:9503/health
```

**OpenWebUIの設定画面で使用するURL:**
- `http://192.168.0.10:9503`（実際のIPアドレスに置き換える）
- `http://192.168.0.10:9503/openapi.json`

---

## 🔍 Step 3: OpenWebUIの設定確認

### 3-1. 登録情報の確認

OpenWebUIの「外部ツール」設定画面で以下を確認：

1. **URL (APIベースURL)**
   - ✅ `http://host.docker.internal:9503`
   - ❌ `http://localhost:9503`（これは間違い）
   - ❌ `http://127.0.0.1:9503`（これも間違い）

2. **OpenAPI仕様URL**
   - ✅ `http://host.docker.internal:9503/openapi.json`
   - ✅ `openapi.json`（相対パス、URLが正しく設定されている場合）
   - ❌ `http://localhost:9503/openapi.json`（これは間違い）

3. **認証 (Authentication)**
   - ✅ 「なし (None)」または「パブリック (Public)」
   - ❌ 「APIキー (API Key)」（Tool Serverは認証なし）

4. **接続状態**
   - ✅ 「Connected」
   - ❌ 「Disconnected」または「Error」

### 3-2. 接続状態が「Disconnected」または「Error」の場合

1. **URLを確認**
   - `host.docker.internal`を使用しているか確認
   - `localhost`を使用していないか確認

2. **Tool Serverが起動中か確認**
   - `curl http://localhost:9503/health`

3. **OpenWebUIコンテナから接続できるか確認**
   - `docker exec open-webui curl http://host.docker.internal:9503/health`

4. **代替案: WindowsのIPアドレスを使用**
   - WindowsのIPアドレスを確認（`ipconfig`）
   - OpenWebUIの設定画面でIPアドレスを直接指定

5. **Tool Serverを再登録**
   - 既存の登録を削除
   - 新しいURLで再登録

---

## 🔍 Step 4: ファイアウォールの確認

### 4-1. Windowsファイアウォールの確認

Tool Serverがポート9503でリッスンしているか確認：

```powershell
# ポート9503を使用しているプロセスを確認
netstat -ano | findstr :9503
```

**問題がある場合:**
- Windowsファイアウォールがブロックしている可能性
- ファイアウォールの設定でポート9503を許可

---

## 🔍 Step 5: ログの確認

### 5-1. Tool Serverのログ確認

Tool Serverの実行中のコンソールでエラーメッセージを確認

### 5-2. OpenWebUIのログ確認

```powershell
# OpenWebUIコンテナのログを確認
docker logs open-webui --tail 100
```

**確認すべきエラー:**
- 接続エラー
- URL解決エラー
- タイムアウトエラー

---

## 🔍 Step 6: 代替接続方法

### 6-1. Dockerネットワークを使用

OpenWebUIとTool Serverを同じDockerネットワークに配置する方法：

1. **Dockerネットワークを作成**
   ```powershell
   docker network create tool-network
   ```

2. **Tool ServerをDockerコンテナとして実行**
   - Tool ServerのDockerfileを使用
   - 同じネットワークに配置

3. **OpenWebUIからコンテナ名で接続**
   - `http://tool-server:9503`

**注意:** 現在のTool Serverはホストから直接実行しているため、この方法はTool ServerをDockerコンテナとして実行する必要があります。

### 6-2. ホストネットワークモードを使用

OpenWebUIをホストネットワークモードで起動する方法：

```powershell
# docker-compose.always-ready-llm.ymlを修正
# network_mode: "host" を追加

# または、docker runコマンドで
docker run -d --network host ...
```

**注意:** この方法はDocker Desktop for Windowsでは使用できません（Linuxのみ）。

---

## 📋 確認チェックリスト

### Tool Server側

- [ ] Tool Serverが起動中（`curl http://localhost:9503/health`）
- [ ] OpenAPI仕様が取得できる（`curl http://localhost:9503/openapi.json`）
- [ ] ポート9503がリッスンしている（`netstat -ano | findstr :9503`）
- [ ] ファイアウォールがブロックしていない

### OpenWebUI側

- [ ] OpenWebUIが起動中（`docker ps --filter "name=openwebui"`）
- [ ] OpenWebUIコンテナからTool Serverに接続できる（`docker exec open-webui curl http://host.docker.internal:9503/health`）
- [ ] 設定画面で正しいURLを使用（`http://host.docker.internal:9503`）
- [ ] 接続状態が「Connected」

### 設定

- [ ] URL: `http://host.docker.internal:9503`（`localhost`ではない）
- [ ] OpenAPI URL: `http://host.docker.internal:9503/openapi.json`
- [ ] 認証: 「なし (None)」または「パブリック (Public)」
- [ ] 接続状態: 「Connected」

---

## 🔥 レミ先輩の推奨手順

### 優先度1: 基本的な確認

1. **Tool Serverが起動中か確認**
   - `curl http://localhost:9503/health`

2. **OpenWebUIコンテナから接続できるか確認**
   - `docker exec open-webui curl http://host.docker.internal:9503/health`

### 優先度2: 設定の確認

1. **OpenWebUIの設定画面でURLを確認**
   - `host.docker.internal`を使用しているか確認
   - `localhost`を使用していないか確認

2. **接続状態を確認**
   - 「Connected」になっているか確認

### 優先度3: 代替案

1. **WindowsのIPアドレスを使用**
   - `ipconfig`でIPアドレスを確認
   - OpenWebUIの設定画面でIPアドレスを直接指定

2. **Tool Serverを再登録**
   - 既存の登録を削除
   - 新しいURLで再登録

---

**レミ先輩モード**: 接続できない場合は、まずOpenWebUIコンテナからTool Serverに接続できるか確認することが最重要！🔥
