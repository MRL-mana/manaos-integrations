# 🧪 OH MY OPENCODE クイックテストガイド

## ✅ サーバー起動確認

サーバーが起動したら、以下のコマンドでテストを実行：

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python wait_and_test.py
```

このスクリプトは：
1. サーバーが起動するまで待機（最大60秒）
2. OH MY OPENCODE統合状態を確認
3. 簡単なタスクを実行してテスト

---

## 🚀 手動テスト

### 1. ヘルスチェック

**ブラウザで:**
- http://localhost:9500/health

**またはcurlで:**
```powershell
curl http://localhost:9500/health
```

### 2. OH MY OPENCODE実行テスト

```powershell
curl -X POST http://localhost:9500/api/oh_my_opencode/execute `
  -H "Content-Type: application/json" `
  -d '{\"task_description\": \"PythonでHello Worldを出力するコードを生成してください\", \"mode\": \"normal\", \"task_type\": \"code_generation\"}'
```

---

## 📊 期待される結果

### 正常な場合

- ✅ ヘルスチェックが200 OKを返す
- ✅ OH MY OPENCODE統合が利用可能
- ✅ タスクが正常に実行される

### エラーの場合

- ❌ サーバーに接続できない → サーバーが起動していない
- ❌ OH MY OPENCODE統合が利用不可 → モジュールのインポートエラー
- ❌ タスク実行失敗 → APIキーまたは設定の問題

---

## 🔍 トラブルシューティング

### サーバーが起動しない

1. **ポート9500が使用中か確認**
   ```powershell
   netstat -ano | findstr :9500
   ```

2. **依存関係を確認**
   ```powershell
   pip install flask flask-cors python-dotenv pyyaml httpx requests
   ```

3. **サーバーのログを確認**
   - サーバーウィンドウのコンソール出力を確認

### OH MY OPENCODEが初期化されない

1. **モジュールの確認**
   ```powershell
   python -c "from oh_my_opencode_integration import OHMyOpenCodeIntegration; print('OK')"
   ```

2. **APIキーの確認**
   ```powershell
   python -c "import os; from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('.env')); print('API Key:', 'OK' if os.getenv('OPENROUTER_API_KEY') else 'NG')"
   ```

---

## 🎉 成功したら

すべてのテストが成功したら、OH MY OPENCODEが正常に動作しています！

次のステップ：
- 実際のタスクを実行してみる
- より複雑なタスクを試す
- Trinity統合を使用する

---

**最終更新:** 2024年12月
