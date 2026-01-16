# manaOS運用開始ガイド
**作成日**: 2025-12-29

---

## 運用開始の手順

### ステップ1: サーバーを起動

**新しいターミナルウィンドウを開いて**、以下を実行してください:

```bash
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python start_server_with_notification.py
```

**確認ポイント**:
- サーバーが起動し、`http://127.0.0.1:9500`でリッスンしている
- 起動通知がSlackに送信される（設定されている場合）
- エラーメッセージが表示されない

**注意**: サーバーは起動したままにしてください（Ctrl+Cで停止します）

---

### ステップ2: サーバー状態を確認

**別のターミナルウィンドウを開いて**、以下を実行:

```bash
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python check_server_status.py
```

**確認ポイント**:
- `/health`: HTTP 200（1秒以内）
- `/status`: HTTP 200（初期化進捗が表示される）
- `/ready`: HTTP 200（必須チェック5項目すべてOK）

---

### ステップ3: 3連続テストを実行

サーバーが正常に起動していることを確認したら、以下を実行:

```bash
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python test_3_consecutive.py
```

**合格条件**: 3回連続で5/5合格（100%）

---

## 運用開始の確認

すべてのチェックが完了したら、運用開始です。

### 毎日の確認事項

1. **朝のルーチン**: Slackに通知が来ているか
2. **夜のルーチン**: 日報が生成されているか
3. **サーバー状態**: `/health`が正常に応答しているか

### 週次の確認事項

1. **監査ログ**: `logs/llm_routing/audit_*.jsonl`
2. **画像ストック統計**: `/api/image/statistics`
3. **未完了タスク分析**: 秘書ルーチンの結果

---

## トラブルシューティング

### サーバーが起動しない

1. ポート9500が使用中でないか確認:
   ```bash
   netstat -ano | findstr :9500
   ```

2. 使用中のプロセスを終了:
   ```bash
   taskkill /PID <プロセスID> /F
   ```

3. エラーログを確認:
   - サーバー起動時のターミナル出力を確認
   - エラーメッセージを確認

### 初期化が完了しない

1. `/status`で進捗を確認:
   ```bash
   curl http://localhost:9500/status
   ```

2. 失敗しているチェックを確認:
   - `readiness_checks`の`status`が`error`の項目を確認
   - エラーメッセージを確認

---

## 運用開始の宣言

すべてのチェックが完了したら、運用開始です。

**運用開始条件**:
- ✅ サーバー起動: 正常に動作
- ✅ 3連続テスト: 3/3合格
- ✅ 起動通知: 正常に動作（設定されている場合）

---

**準備完了**: 2025-12-29












