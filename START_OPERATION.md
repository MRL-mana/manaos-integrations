# manaOS運用開始ガイド
**作成日**: 2025-12-28

---

## 運用開始の手順

### 1. サーバー起動

```bash
cd manaos_integrations
python start_server_with_notification.py
```

**確認ポイント**:
- 起動通知がSlackに送信される
- `/health`が1秒以内で200を返す
- `/ready`が60秒以内に200になる

### 2. 初期化完了の確認

```bash
# ヘルスチェック
curl http://localhost:9500/health

# レディネスチェック
curl http://localhost:9500/ready

# 詳細状態
curl http://localhost:9500/status
```

**必須チェック5項目**:
1. ✅ memory_db: 記憶DB接続OK
2. ✅ obsidian_path: Obsidianパス確認OK
3. ✅ notification_hub: 通知ハブ初期化OK
4. ✅ llm_routing: LLMルーティングOK
5. ✅ image_stock: 画像ストックアクセスOK

### 3. 3連続テストの実行

```bash
python test_3_consecutive.py
```

**合格条件**: 3回連続で5/5合格（100%）

### 4. 運用開始の宣言

すべてのチェックが完了したら、運用開始です。

---

## 運用中の確認事項

### 毎日の確認

- 朝のルーチン: Slackに通知が来ているか
- 夜のルーチン: 日報が生成されているか
- サーバー状態: `/health`が正常に応答しているか

### 週次の確認

- 監査ログ: `logs/llm_routing/audit_*.jsonl`
- 画像ストック統計: `/api/image/statistics`
- 未完了タスク分析: 秘書ルーチンの結果

---

## トラブルシューティング

### サーバーが起動しない

1. ポート9500が使用中でないか確認
2. ログを確認（エラーメッセージを確認）
3. 手動起動でエラーを確認

### 初期化が完了しない

1. `/status`で進捗を確認
2. 失敗しているチェックを確認
3. 個別に統合システムをテスト

---

**運用開始準備完了**: 2025-12-28
