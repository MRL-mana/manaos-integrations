# 🚀 ManaOSシステム起動手順

**作成日**: 2026-01-07

---

## ⚠️ 現在の状態

**システムは未起動です**。以下の手順で起動してください。

---

## 📋 起動方法

### 方法1: 統合APIサーバーを起動（推奨）

**新しいターミナルウィンドウを開いて**、以下を実行してください:

```bash
cd C:\Users\mana4\Desktop\manaos_integrations
python start_server_with_notification.py
```

**確認ポイント**:
- サーバーが `http://127.0.0.1:9500` で起動
- 起動通知がSlackに送信される（設定されている場合）
- `/health` エンドポイントが応答する

**注意**: サーバーは起動したままにしてください（Ctrl+Cで停止します）

---

### 方法2: 直接起動スクリプトを使用

```bash
cd C:\Users\mana4\Desktop\manaos_integrations
python start_server_direct.py
```

---

### 方法3: 統合オーケストレーターを直接使用

```bash
cd C:\Users\mana4\Desktop\manaos_integrations
python manaos_integration_orchestrator.py
```

---

## ✅ 起動確認

### 1. サーバー状態確認

**別のターミナルウィンドウを開いて**、以下を実行:

```bash
cd C:\Users\mana4\Desktop\manaos_integrations
python check_server_status.py
```

### 2. サービス状態確認

```bash
python check_service_status.py
```

### 3. ヘルスチェック

```bash
# 統合APIサーバー
curl http://localhost:9500/health

# 詳細状態
curl http://localhost:9500/status
```

---

## 📊 運用開始チェックリスト

- [ ] 統合APIサーバーが起動している
- [ ] `/health` エンドポイントが応答する
- [ ] `/ready` エンドポイントが200を返す（初期化完了後）
- [ ] 主要サービスが起動している

---

## 🔍 トラブルシューティング

### サーバーが起動しない場合

1. **ポート9500が使用中でないか確認**:
   ```bash
   netstat -ano | findstr :9500
   ```

2. **エラーログを確認**:
   - 起動時のエラーメッセージを確認
   - `logs/` ディレクトリのログファイルを確認

3. **依存関係を確認**:
   ```bash
   pip install -r requirements.txt
   ```

### 初期化が完了しない場合

1. `/status` で進捗を確認:
   ```bash
   curl http://localhost:9500/status
   ```

2. 失敗しているチェックを確認:
   - `readiness_checks` の `status` が `error` の項目を確認
   - エラーメッセージを確認

---

## 📝 運用中の確認事項

### 毎日の確認

- 朝のルーチン: Slackに通知が来ているか
- 夜のルーチン: 日報が生成されているか
- サーバー状態: `/health` が正常に応答しているか

### 週次の確認

- 監査ログ: `logs/llm_routing/audit_*.jsonl`
- 画像ストック統計: `/api/image/statistics`
- 未完了タスク分析: 秘書ルーチンの結果

---

## ⚠️ 停止方法

サーバーを停止するには、起動したターミナルで `Ctrl+C` を押してください。

---

**重要**: システムを起動するには、**新しいターミナルウィンドウを開いて**上記のコマンドを実行してください。








