# Skills全自動化ガイド

## 📋 概要

現在のSkillsは「半自動」です。全自動化するには、以下の方法があります：

1. **AI自動実行スクリプト**: AIにYAML生成を依頼し、自動的に処理する
2. **スケジューラー**: 定期的に自動実行（例：毎日の日報）
3. **イベント駆動**: 特定のイベント（例：Gitコミット後）で自動実行

## 🤖 方法1: AI自動実行スクリプト

### 使い方

```bash
# daily_opsを自動実行
python scripts/auto_skill_runner.py daily_ops

# 引数を指定
python scripts/auto_skill_runner.py daily_ops --date 2026-01-13
python scripts/auto_skill_runner.py log_analysis --log_file logs/app.log
```

### 動作フロー

1. AIにYAML生成を依頼（LLM API呼び出し）
2. YAMLファイルを自動生成
3. Skillスクリプトを自動実行
4. 結果を表示

### 実装状況

- ✅ 基本構造は実装済み
- ⚠️ LLM API呼び出し部分はTODO（現在はテンプレートベース）

### 今後の改善

- LLM API統合（OpenAI、Claude、Ollamaなど）
- エラーハンドリング強化
- リトライ機能
- ログ記録

## ⏰ 方法2: スケジューラー

### 使い方

```bash
# スケジューラーを起動
python scripts/skill_scheduler.py
```

### 設定ファイル

`data/skill_scheduler_config.json`:

```json
{
  "enabled": true,
  "tasks": [
    {
      "skill_name": "daily_ops",
      "schedule": "daily",
      "time": "09:00",
      "enabled": true,
      "kwargs": {}
    },
    {
      "skill_name": "log_analysis",
      "schedule": "hourly",
      "enabled": true,
      "kwargs": {
        "log_file": "logs/app.log"
      }
    }
  ]
}
```

### スケジュールタイプ

- `daily`: 毎日指定時刻に実行
- `hourly`: 毎時実行
- `weekly`: 毎週指定曜日・時刻に実行

### 実装状況

- ✅ 基本構造は実装済み
- ✅ scheduleライブラリを使用
- ⚠️ LLM API呼び出し部分はTODO

## 🎯 方法3: イベント駆動（今後実装予定）

### 想定されるイベント

- Gitコミット後: 自動的にgit_opsを実行
- ログファイル更新後: 自動的にlog_analysisを実行
- ファイル追加後: 自動的にfile_organizeを実行
- サーバーエラー検出後: 自動的にserver_monitorを実行

### 実装方法

- ファイル監視（watchdog）
- Gitフック
- Webhook
- ポーリング

## 🚀 全自動化の実装手順

### Step 1: LLM API統合

`scripts/auto_skill_runner.py`の`generate_yaml_with_ai`関数を実装：

```python
def generate_yaml_with_ai(skill_name: str, **kwargs) -> Optional[Path]:
    """AIにYAML生成を依頼"""
    # LLM APIを呼び出し
    # 例: OpenAI API、Claude API、Ollama APIなど
    response = llm_api.generate(prompt)
    yaml_content = extract_yaml_from_response(response)
    # ...
```

### Step 2: スケジューラーを常駐化

Windowsの場合、タスクスケジューラーに登録：

```powershell
# タスクスケジューラーに登録
$action = New-ScheduledTaskAction -Execute "python" -Argument "scripts/skill_scheduler.py"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "ManaOS Skills Scheduler" -Action $action -Trigger $trigger
```

### Step 3: イベント駆動の実装

ファイル監視やGitフックを実装：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SkillEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.log'):
            auto_run_skill("log_analysis", log_file=event.src_path)
```

## 📊 現在の状態

### ✅ 実装済み

- Skills自動実行スクリプトの基本構造
- スケジューラーの基本構造
- 設定ファイル管理

### ⚠️ TODO

- LLM API統合（実際のAI呼び出し）
- エラーハンドリング強化
- ログ記録
- イベント駆動の実装
- テスト

## 💡 推奨事項

1. **まずは半自動で運用**: 現在の方法（AIにYAML生成→手動実行）で運用を開始
2. **LLM API統合**: 実際のAI呼び出しを実装して全自動化
3. **スケジューラー活用**: 定期的なタスク（日報など）はスケジューラーで自動化
4. **段階的に拡張**: イベント駆動などは必要に応じて追加

## 🎉 まとめ

現在のSkillsは「半自動」ですが、全自動化の基盤は整っています。

- **今すぐ使える**: 半自動（AIにYAML生成→手動実行）
- **今後実装**: 全自動（LLM API統合→自動実行）

準備が整い次第、全自動化を実装できます！
