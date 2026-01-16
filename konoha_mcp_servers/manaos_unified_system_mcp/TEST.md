# 🧪 RunPod MCPサーバー 動作テスト

再起動後、以下のテストを試してみてください。

## ✅ 基本テスト

### 1. GPU状態確認
```
「RunPodのGPU状態を確認して」
```

### 2. 画像生成
```
「シンプルなロゴ画像を生成して」
「モダンなテック企業のロゴを作って」
```

### 3. テキスト生成
```
「PythonでHello Worldプログラムを生成して」
```

### 4. チャット
```
「このコードをレビューして: [コード]」
```

## 🔍 確認ポイント

### 正常に動作している場合
- ✅ MCPツールが自動的に実行される
- ✅ 結果が返ってくる
- ✅ エラーが出ない

### 問題がある場合
- ❌ 「ツールが見つかりません」と表示される
- ❌ タイムアウトエラー
- ❌ 接続エラー

## 🐛 トラブルシューティング

### MCPサーバーが認識されない場合

1. **コンテナ確認**
   ```bash
   docker ps | grep runpod-mcp
   ```

2. **手動テスト**
   ```bash
   docker exec runpod-mcp-server python -c "from runpod_mcp_server import RunPodMCPServer; print('OK')"
   ```

3. **mcp_config.json 確認**
   - パスが正しいか
   - コンテナ名が一致しているか

### エラーが出る場合

1. **ログ確認**
   ```bash
   docker logs runpod-mcp-server
   ```

2. **コンテナ再起動**
   ```bash
   docker compose -f /root/manaos_unified_system/mcp/docker-compose.yml restart
   ```

## 🎯 期待される動作

Cursorで「ロゴ画像を生成して」と言うと：
1. MCPサーバーが `runpod_generate_image` ツールを呼び出し
2. RunPod APIにリクエスト送信
3. 画像生成（15-30秒）
4. 結果がCursorに返却

試してみてください！








