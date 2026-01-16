# SVI自動化ガイド

## 概要

SVI自動化モジュールにより、以下の自動化機能が利用できます：

- **フォルダ監視**: 新しい画像が追加されたら自動生成
- **スケジュール実行**: 指定時刻に自動生成
- **バッチ処理**: フォルダ内の画像を一括処理
- **通知機能**: 生成完了時にWebhook通知

## 機能

### 1. フォルダ監視

指定したフォルダを監視し、新しい画像が追加されると自動的に動画を生成します。

#### CLIから使用
```bash
python svi_automation_cli.py watch /path/to/folder --auto-generate --prompt "beautiful scene"
```

#### APIから使用
```http
POST /api/svi/automation/watch
Content-Type: application/json

{
  "folder_path": "/path/to/folder",
  "auto_generate": true,
  "default_prompt": "beautiful scene, cinematic"
}
```

#### Pythonから使用
```python
from svi_automation import SVIAutomation

automation = SVIAutomation()
automation.watch_folder(
    folder_path="/path/to/folder",
    auto_generate=True,
    default_prompt="beautiful scene"
)
automation.start_scheduler()
```

### 2. スケジュール実行

指定した時刻に自動的に動画を生成します。

#### CLIから使用
```bash
# 今日の15:00に実行
python svi_automation_cli.py schedule \
  --image /path/to/image.png \
  --prompt "beautiful landscape" \
  --time "15:00"

# 繰り返し実行（毎日15:00）
python svi_automation_cli.py schedule \
  --image /path/to/image.png \
  --prompt "beautiful landscape" \
  --time "15:00" \
  --repeat \
  --repeat-interval 24
```

#### APIから使用
```http
POST /api/svi/automation/schedule
Content-Type: application/json

{
  "task_name": "daily_video",
  "schedule_time": "2025-01-29T15:00:00",
  "image_path": "/path/to/image.png",
  "prompt": "beautiful landscape",
  "video_length_seconds": 5,
  "repeat": true,
  "repeat_interval_seconds": 86400
}
```

### 3. バッチ処理

フォルダ内のすべての画像を一括処理します。

#### CLIから使用
```bash
python svi_automation_cli.py batch /path/to/folder --prompt "beautiful scene" --max-files 10
```

#### APIから使用
```http
POST /api/svi/automation/batch
Content-Type: application/json

{
  "folder_path": "/path/to/folder",
  "prompt": "beautiful scene",
  "max_files": 10
}
```

#### Pythonから使用
```python
from svi_automation import SVIAutomation

automation = SVIAutomation()
execution_ids = automation.batch_process_folder(
    folder_path="/path/to/folder",
    prompt="beautiful scene",
    max_files=10
)
```

## 設定ファイル

自動化の設定は `svi_automation_config.json` に保存されます。

```json
{
  "watch_folders": [
    {
      "path": "/path/to/folder",
      "auto_generate": true,
      "default_prompt": "beautiful scene"
    }
  ],
  "scheduled_tasks": [
    {
      "name": "daily_video",
      "schedule_time": "2025-01-29T15:00:00",
      "image_path": "/path/to/image.png",
      "prompt": "beautiful landscape",
      "video_length_seconds": 5,
      "repeat": true,
      "repeat_interval": 86400,
      "enabled": true
    }
  ],
  "auto_generate": {
    "enabled": true,
    "default_prompt": "beautiful scene, cinematic, smooth motion",
    "video_length_seconds": 5,
    "steps": 6,
    "motion_strength": 1.3
  },
  "notifications": {
    "enabled": false,
    "webhook_url": null
  }
}
```

## 通知機能

生成完了時にWebhook通知を送信できます。

### 設定方法

1. 設定ファイルを編集:
```json
{
  "notifications": {
    "enabled": true,
    "webhook_url": "http://localhost:5678/webhook/svi-notification"
  }
}
```

2. または、環境変数で設定:
```bash
export SVI_NOTIFICATION_WEBHOOK_URL="http://localhost:5678/webhook/svi-notification"
```

## 使用例

### 例1: 画像フォルダを監視して自動生成

```python
from svi_automation import SVIAutomation

automation = SVIAutomation()
automation.watch_folder(
    folder_path="./images",
    auto_generate=True,
    default_prompt="beautiful scene, cinematic"
)
automation.start_scheduler()

# バックグラウンドで実行中
# 新しい画像が追加されると自動生成
```

### 例2: 毎日定時に動画生成

```python
from svi_automation import SVIAutomation
from datetime import datetime, timedelta

automation = SVIAutomation()
automation.schedule_task(
    task_name="daily_morning_video",
    schedule_time=datetime.now().replace(hour=9, minute=0),
    image_path="./morning_image.png",
    prompt="peaceful morning, beautiful sunrise",
    video_length_seconds=5,
    repeat=True,
    repeat_interval=timedelta(days=1)
)
automation.start_scheduler()
```

### 例3: フォルダ内の画像を一括処理

```python
from svi_automation import SVIAutomation

automation = SVIAutomation()
execution_ids = automation.batch_process_folder(
    folder_path="./images",
    prompt="beautiful scene",
    max_files=20
)

print(f"処理開始: {len(execution_ids)}件")
```

## トラブルシューティング

### フォルダ監視が動作しない

- フォルダパスが正しいか確認
- ファイル権限を確認
- watchdogライブラリがインストールされているか確認: `pip install watchdog`

### スケジュールタスクが実行されない

- スケジューラーが起動しているか確認: `automation.start_scheduler()`
- 設定ファイルの `enabled` が `true` か確認
- 実行時刻が過去になっていないか確認

### 通知が送信されない

- 設定ファイルの `notifications.enabled` が `true` か確認
- Webhook URLが正しいか確認
- ネットワーク接続を確認

## 関連ドキュメント

- [SVI統合ガイド](./SVI_INTEGRATION_GUIDE.md)
- [セットアップ完了ガイド](./SVI_WAN22_SETUP_COMPLETE.md)











