# 環境変数設定ガイド

## 概要

ManaOS統合システムでは、環境変数を使用して設定を管理しています。これにより、異なる環境での実行や設定の変更が容易になります。

## 環境変数の設定方法

### Windows (PowerShell)

```powershell
# 一時的な設定（現在のセッションのみ）
$env:COMFYUI_PATH = "C:/ComfyUI"
$env:COMFYUI_URL = "http://localhost:8188"

# 永続的な設定（ユーザー環境変数）
[System.Environment]::SetEnvironmentVariable("COMFYUI_PATH", "C:/ComfyUI", "User")
```

### Windows (コマンドプロンプト)

```cmd
REM 一時的な設定
set COMFYUI_PATH=C:/ComfyUI
set COMFYUI_URL=http://localhost:8188
```

### .envファイルの使用（推奨）

プロジェクトルートに`.env`ファイルを作成：

- まず `env.example` をコピーして `.env` を作るのが簡単です
- **`.env` はローカル専用**です（Gitにコミットしない）
- CI/本番は **OS環境変数**（GitHub Actions Secrets 等）で設定してください

```env
# ComfyUI設定
COMFYUI_PATH=C:/ComfyUI
COMFYUI_URL=http://localhost:8188
COMFYUI_MODELS_DIR=C:/ComfyUI/models/checkpoints
COMFYUI_OUTPUT_DIR=C:/ComfyUI/output

# ManaOS設定
MANA_MODELS_DIR=C:/mana_workspace/models

# Gallery API設定
GALLERY_PORT=5559
GALLERY_IMAGES_DIR=gallery_images

# Ollama設定
OLLAMA_MODELS=C:/Users/username/.ollama/models

# ムフフ画像ディレクトリ
MUFUFU_IMAGES_DIR_1=C:/Users/username/OneDrive/Desktop/mufufu_cyberrealistic_10
MUFUFU_IMAGES_DIR_2=C:/Users/username/OneDrive/Desktop/output
MUFUFU_IMAGES_DIR_3=C:/Users/username/Desktop/lora_output_mana_favorite_japanese_clear_gal (1)
MUFUFU_IMAGES_DIR_4=C:/Users/username/OneDrive/Desktop/mufufu_combined_10
```

## Secrets（機密情報）の扱い（重要）

以下は **Secrets（機密情報）** です。**コードやドキュメントに実値を貼らない**でください。

- **供給元の統一**:
  - **ローカル**: `.env`（Git管理外）
  - **CI/本番**: OS環境変数（GitHub Actions Secrets / サーバーの環境変数）

### Secrets対象の主な環境変数

| 変数名 | 用途 | 例（ダミー） |
| ------ | ------ | ------ |
| `CIVITAI_API_KEY` | CivitAI API | `your_civitai_api_key_here` |
| `N8N_API_KEY` | n8n API | `your_n8n_api_key_here` |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook | `https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>` |
| `SLACK_BOT_TOKEN` | Slack Bot Token | `xoxb-<your-bot-token>` |
| `ROWS_API_KEY` | Rows API | `your_rows_api_key_here` |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Drive credentialsファイル | `path/to/credentials.json` |
| `GOOGLE_DRIVE_TOKEN` | Google Drive tokenファイル | `path/to/token.json` |

### ローカルセットアップ例

```powershell
# PowerShell（現在のセッションのみ）
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"
$env:SLACK_BOT_TOKEN = "xoxb-<your-bot-token>"
```

### 注意

- **`.env` は絶対にコミットしない**（`.gitignore`で除外されていることを確認）
- もし誤って実キーを貼った/コミットした場合は **キーをローテーション**してください（履歴改変はしない方針）

## 主要な環境変数一覧

### ComfyUI関連

| 変数名 | 説明 | デフォルト値 | 必須 |
| ------ | ------ | ------ | ------ |
| `COMFYUI_PATH` | ComfyUIのインストールパス | `C:/ComfyUI` | 推奨 |
| `COMFYUI_URL` | ComfyUIのAPI URL | `http://localhost:8188` | 推奨 |
| `COMFYUI_MODELS_DIR` | モデルディレクトリ | `C:/ComfyUI/models/checkpoints` | 推奨 |
| `COMFYUI_OUTPUT_DIR` | 出力ディレクトリ | `C:/ComfyUI/output` | 任意 |

### ManaOS関連

| 変数名 | 説明 | デフォルト値 | 必須 |
| ------ | ------ | ------ | ------ |
| `MANA_MODELS_DIR` | ManaOSモデルディレクトリ | `C:/mana_workspace/models` | 任意 |

### Gallery API関連

| 変数名 | 説明 | デフォルト値 | 必須 |
| ------ | ------ | ------ | ------ |
| `GALLERY_PORT` | Gallery APIのポート番号 | `5559` | 任意 |
| `GALLERY_IMAGES_DIR` | 画像保存ディレクトリ | `gallery_images` | 任意 |

### Ollama関連

| 変数名 | 説明 | デフォルト値 | 必須 |
| ------ | ------ | ------ | ------ |
| `OLLAMA_MODELS` | Ollamaモデルパス | `~/.ollama/models` | 任意 |

### 画像生成関連

| 変数名 | 説明 | デフォルト値 | 必須 |
| ------ | ------ | ------ | ------ |
| `MUFUFU_IMAGES_DIR_1` | ムフフ画像ディレクトリ1 | ユーザーホーム配下 | 任意 |
| `MUFUFU_IMAGES_DIR_2` | ムフフ画像ディレクトリ2 | ユーザーホーム配下 | 任意 |
| `MUFUFU_IMAGES_DIR_3` | ムフフ画像ディレクトリ3 | ユーザーホーム配下 | 任意 |
| `MUFUFU_IMAGES_DIR_4` | ムフフ画像ディレクトリ4 | ユーザーホーム配下 | 任意 |

## 使用例

### 例1: ComfyUIのパスを変更

```python
import os
from pathlib import Path

# 環境変数から取得（デフォルト値あり）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
```

### 例2: 複数のパス候補を確認

```python
import os
from pathlib import Path

# 環境変数から取得
default_path = os.getenv("COMFYUI_PATH", "C:/ComfyUI")
search_paths = [
    Path(default_path),
    Path.home() / "ComfyUI",
    Path("D:/ComfyUI")
]

# 存在するパスを探す
for path in search_paths:
    if path.exists():
        COMFYUI_PATH = path
        break
```

### 例3: 環境変数の検証

```python
import os
from pathlib import Path

COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))

if not COMFYUI_PATH.exists():
    print(f"⚠️  ComfyUIが見つかりません: {COMFYUI_PATH}")
    print("環境変数 COMFYUI_PATH を設定してください")
    sys.exit(1)
```

## ベストプラクティス

### 1. デフォルト値の提供

環境変数が設定されていない場合でも動作するように、デフォルト値を提供します：

```python
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
```

### 2. パスの検証

環境変数から取得したパスが存在するか確認します：

```python
if not COMFYUI_PATH.exists():
    print(f"⚠️  パスが見つかりません: {COMFYUI_PATH}")
```

### 3. エラーメッセージの明確化

環境変数が設定されていない場合、明確なエラーメッセージを表示します：

```python
if not os.getenv("COMFYUI_PATH"):
    print("環境変数 COMFYUI_PATH を設定してください")
    print("例: $env:COMFYUI_PATH = 'C:/ComfyUI'")
```

### 4. .envファイルの活用

`python-dotenv`を使用して`.env`ファイルを読み込みます：

```python
from dotenv import load_dotenv
from pathlib import Path

# .envファイルを読み込み
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
```

## トラブルシューティング

### 問題1: 環境変数が反映されない

**解決方法:**

- 環境変数を設定した後、ターミナルを再起動
- `.env`ファイルを使用している場合、ファイルの読み込みを確認

### 問題2: パスが見つからない

**解決方法:**

- 環境変数の値が正しいか確認
- パスが存在するか確認
- デフォルト値が適切か確認

### 問題3: 複数の環境で異なる設定が必要

**解決方法:**

- `.env`ファイルを環境ごとに作成
- 環境変数を環境ごとに設定
- 設定ファイルを使用

## まとめ

環境変数を使用することで：

- ✅ 柔軟な設定管理
- ✅ 異なる環境での実行が容易
- ✅ ハードコードされたパスの削減
- ✅ 設定の一元管理

環境変数を活用して、より柔軟で保守しやすいコードを維持しましょう。
