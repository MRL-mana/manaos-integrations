# 🚀 OH MY OPENCODE 統合APIサーバー起動手順

## ✅ サーバー起動方法

### 方法1: PowerShellスクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\start_server_simple.ps1
```

このスクリプトは新しいウィンドウでサーバーを起動します。

---

### 方法2: 手動で起動

**新しいPowerShellウィンドウを開いて：**

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python unified_api_server.py
```

サーバーが起動すると、以下のようなメッセージが表示されます：

```
ManaOS統合APIサーバーを起動中...
サーバー起動: http://0.0.0.0:9500
利用可能なエンドポイント:
  GET  /health - ヘルスチェック（軽量：プロセス生存のみ）
  GET  /ready - レディネスチェック（初期化完了確認）
  GET  /api/integrations/status - 統合システム状態
  ...
```

---

## 🔍 動作確認

### 1. ヘルスチェック（ブラウザ）

ブラウザで以下のURLにアクセス：
- http://localhost:9500/health

正常に動作していれば、JSONレスポンスが返ります。

### 2. Pythonスクリプトで確認

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python check_server_status.py
```

### 3. 統合テストを実行

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python test_oh_my_opencode_integration.py
```

---

## ⚠️ 注意事項

1. **サーバーの起動には時間がかかります**
   - 初期化処理が完了するまで10-30秒程度かかる場合があります
   - 特に初回起動時は時間がかかります

2. **ポート9500が使用中の場合**
   - 既存のプロセスを停止するか、環境変数で別のポートを指定してください
   ```powershell
   $env:MANAOS_INTEGRATION_PORT = "9501"
   python unified_api_server.py
   ```

3. **エラーが発生した場合**
   - サーバーのコンソール出力を確認してください
   - 依存関係が不足している可能性があります
   ```powershell
   pip install flask flask-cors python-dotenv pyyaml httpx requests
   ```

---

## 📊 サーバー起動後の確認項目

- ✅ ヘルスチェックが成功する
- ✅ OH MY OPENCODE統合が利用可能
- ✅ APIエンドポイントが応答する

---

## 🎉 次のステップ

サーバーが正常に起動したら：

1. ✅ ヘルスチェックで動作確認
2. ✅ OH MY OPENCODE統合状態確認
3. ✅ 実際のタスクを実行してテスト

---

**最終更新:** 2024年12月
