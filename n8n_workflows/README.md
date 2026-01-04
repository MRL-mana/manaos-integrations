# n8nワークフロー テンプレート

manaOS秘書機能の3本のルーチンワークフロー

## 📋 概要

このディレクトリには、manaOS秘書機能の3本のルーチンワークフローが含まれています。

### ワークフロー一覧

1. **morning_routine.json** - 朝のルーチン
   - 実行時刻: 毎朝 8:00
   - 内容: 今日の予定＋最重要3タスク＋昨日のログ差分

2. **noon_routine.json** - 昼のルーチン
   - 実行時刻: 毎日 12:00
   - 内容: 進捗確認＋未完了の理由を1行で

3. **evening_routine.json** - 夜のルーチン
   - 実行時刻: 毎日 18:00
   - 内容: 日報自動生成＋明日の仕込み

## 🚀 セットアップ

### 1. n8nにワークフローをインポート

1. n8nを開く（http://localhost:5678）
2. ワークフロー → インポート
3. 各JSONファイルをインポート

### 2. Webhook URLを設定

各ワークフローには、manaOS APIへのWebhookが含まれています。
Webhook URLを設定してください：

- `http://localhost:9500/api/secretary/morning`
- `http://localhost:9500/api/secretary/noon`
- `http://localhost:9500/api/secretary/evening`

### 3. スケジュールを設定

各ワークフローの「Schedule Trigger」ノードで実行時刻を設定：

- 朝のルーチン: `0 8 * * *` (毎朝8時)
- 昼のルーチン: `0 12 * * *` (毎日12時)
- 夜のルーチン: `0 18 * * *` (毎日18時)

## 📝 ワークフロー構造

### 朝のルーチン

```
Schedule Trigger
  ↓
HTTP Request (manaOS API)
  ↓
Slack通知
```

### 昼のルーチン

```
Schedule Trigger
  ↓
HTTP Request (manaOS API)
  ↓
Slack通知
```

### 夜のルーチン

```
Schedule Trigger
  ↓
HTTP Request (manaOS API)
  ↓
Slack通知
```

## 🔒 凍結ルール

**重要**: この3本以外のワークフローは凍結されています。

- `core_routines/` 以外のワークフローは "disabled" にする
- 新規ワークフロー追加は **PR（レビュー）必須**

## 📚 関連ドキュメント

- `ManaOS_Extension_Phase_Roadmap.md` - ロードマップ
- `secretary_routines.py` - Python実装（バックアップ）

---

**最終更新**: 2025-12-28


















