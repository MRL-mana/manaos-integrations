# 🔍 RunPod MCPサーバー デバッグガイド

MCPツールが正常に動作しているか確認する方法です。

## ✅ 正常な動作

### MCPツールが認識されている場合

Cursorで以下のように入力すると：

```
「RunPodのGPU状態を確認して」
「ロゴ画像を生成して」
```

**期待される動作**:
1. MCPツールが自動的に選択される
2. `runpod_test_gpu` や `runpod_generate_image` が実行される
3. 結果が返ってくる
4. エラーが出ない

### 確認方法

Cursorの画面で：
- ツール選択時に `runpod-gpu` のツール一覧が表示される
- 実行中に「RunPod GPU MCP Server」からの応答がある

## ❌ 問題がある場合

### 1. 「ツールが見つかりません」と表示される

**原因**:
- MCPサーバーが認識されていない
- mcp_config.json の設定が間違っている

**解決策**:
```bash
# コンテナ確認
docker ps | grep runpod-mcp

# mcp_config.json確認
cat /root/mcp_config.json | grep -A 5 runpod-gpu

# Cursor再起動
```

### 2. タイムアウトエラー

**原因**:
- コンテナが応答していない
- MCPサーバーが起動していない

**解決策**:
```bash
# コンテナ状態確認
docker ps | grep runpod-mcp
docker logs runpod-mcp-server

# コンテナ再起動
docker compose -f /root/manaos_unified_system/mcp/docker-compose.yml restart
```

### 3. 接続エラー

**原因**:
- コンテナとCursorの通信問題
- stdio通信の設定が間違っている

**解決策**:
```bash
# コンテナ内で直接テスト
docker exec -it runpod-mcp-server python -c "from runpod_mcp_server import RunPodMCPServer; print('OK')"

# mcp_config.jsonのコマンドを確認
cat /root/mcp_config.json | grep -A 3 runpod-gpu
```

## 🔧 詳細デバッグ

### MCPサーバーの状態確認

```bash
# コンテナが起動しているか
docker ps | grep runpod-mcp

# コンテナのログ（リアルタイム）
docker logs runpod-mcp-server -f

# コンテナ内でPython環境確認
docker exec runpod-mcp-server python --version
docker exec runpod-mcp-server pip list | grep mcp
```

### RunPod接続確認

```bash
# コンテナ内からRunPod接続テスト
docker exec runpod-mcp-server python -c "
import sys
sys.path.insert(0, '/app')
from services.runpod_serverless_manager import RunPodServerlessManager
manager = RunPodServerlessManager()
result = manager.client.test_gpu()
print(result)
"
```

### mcp_config.json確認

```bash
# 設定内容確認
cat /root/mcp_config.json | jq '.mcpServers."runpod-gpu"'

# または
python3 -c "
import json
with open('/root/mcp_config.json') as f:
    config = json.load(f)
    print(json.dumps(config['mcpServers']['runpod-gpu'], indent=2))
"
```

## 🎯 テスト手順

### ステップ1: コンテナ確認
```bash
docker ps | grep runpod-mcp
# → 起動していれば OK
```

### ステップ2: MCPサーバーテスト
```bash
docker exec runpod-mcp-server python -c "from runpod_mcp_server import RunPodMCPServer; print('OK')"
# → エラーが出なければ OK
```

### ステップ3: Cursorでテスト
Cursorで以下を試す：
```
「RunPodのGPU状態を確認して」
```

### ステップ4: 結果確認
- ✅ ツールが実行される → 正常
- ❌ エラーが出る → 上記の解決策を試す

## 📝 よくある問題と解決策

### 問題: MCPツールが表示されない

**確認項目**:
1. Cursorが再起動されているか
2. mcp_config.jsonのパスが正しいか
3. コンテナが起動しているか

**解決策**:
```bash
# 1. コンテナ再起動
docker compose -f /root/manaos_unified_system/mcp/docker-compose.yml restart

# 2. Cursor再起動
```

### 問題: 「コマンドが見つかりません」

**原因**: docker コマンドのパス問題

**解決策**: mcp_config.jsonで絶対パスを使用
```json
{
  "runpod-gpu": {
    "command": "/usr/bin/docker",
    "args": ["exec", "-i", "runpod-mcp-server", "python", "-u", "runpod_mcp_server.py"]
  }
}
```

### 問題: タイムアウト

**解決策**: コンテナのヘルスチェックを無効化
```yaml
# docker-compose.yml で healthcheck をコメントアウト
```

## 🚀 最終確認

すべて正常なら：
1. ✅ コンテナ起動中
2. ✅ MCPサーバーがインポート可能
3. ✅ RunPod接続可能
4. ✅ Cursorでツールが表示される

これらがすべてOKなら、MCPツールは正常に動作しています！








