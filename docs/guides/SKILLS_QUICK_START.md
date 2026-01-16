# Skills クイックスタートガイド

Cursorを再起動してSkillsファイルが認識されたら、すぐに使い始められます！

## 🎯 すぐに試せる：daily_ops Skill

最も簡単で、すぐに使える `daily_ops` Skillから始めましょう。

### Step 1: AIにYAML形式で日報を出力させる

Cursorのチャットで以下のように指示してください：

```
今日の日報をYAML形式で出力してください。
以下のフォーマットに従ってください：

```yaml
kind: daily_ops
date: 2026-01-13
title: "日報"
tags: ["ops", "manaos"]
summary: |
  今日の要点を3行くらいで。
tasks:
  - title: "バックアップ確認"
    status: todo
    priority: high
  - title: "n8nワークフロー整理"
    status: doing
notes:
  - "気づき1"
  - "気づき2"
notify:
  slack: false
  obsidian: true
idempotency_key: "daily_ops_2026-01-13"
```
```

### Step 2: YAMLファイルを保存

AIが出力したYAMLを `artifacts/daily_ops_2026-01-13.yaml` として保存してください。

### Step 3: スクリプトで処理

```bash
python scripts/apply_skill_daily_ops.py artifacts/daily_ops_2026-01-13.yaml
```

**結果:**
- ✅ Obsidianに `Daily/2026-01-13_日報.md` が作成されます
- ✅ 処理履歴に記録され、再実行しても重複しません（冪等性）

## 🔀 Git操作も試してみる

Gitリポジトリがあるなら、`git_ops` Skillもすぐに使えます。

### Git状態確認

```yaml
kind: git_ops
action: status
repository_path: "."
idempotency_key: "git_status_2026-01-13"
```

```bash
python scripts/apply_skill_git_ops.py artifacts/git_status_2026-01-13.yaml
```

## 💡 Tips

### Skillsファイルが認識されているか確認

CursorでSkillsファイルの内容を参照できるか確認してください。例えば：

- `/daily-ops` や `/git-ops` などのSkill名で参照できる
- Skillsファイルの内容がAIのコンテキストに含まれている

### 冪等性キーについて

同じ `idempotency_key` で再実行しても重複しません。日付やタイムスタンプを含めることを推奨します：

- `"daily_ops_2026-01-13"`
- `"git_commit_2026-01-13_001"`
- `"n8n_activate_2026-01-13_001"`

### 環境変数の設定（オプション）

Slack通知を使う場合：

```powershell
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/..."
```

n8nワークフロー操作を使う場合：

```powershell
$env:N8N_BASE_URL = "http://localhost:5678"
$env:N8N_API_KEY = "your-api-key"
```

## 📚 参考

- [Skills README](../skills/README.md) - 全Skillsの詳細
- [実装ガイド](SKILLS_IMPLEMENTATION_GUIDE.md) - 実装の詳細
- [運用開始チェックリスト](SKILLS_SETUP_CHECKLIST.md) - 環境チェック

## 🎉 運用開始！

準備は完了しています。AIに「YAML形式で日報を出力して」と指示するだけです！
