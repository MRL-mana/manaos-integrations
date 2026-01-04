# SVI × Wan 2.2 MCPサーバー 実装完了

## ✅ 実装完了項目

### 1. MCPサーバー実装 ✅

- **server.py**: SVI動画生成MCPサーバー
- **__main__.py**: エントリーポイント
- **__init__.py**: パッケージ初期化

### 2. 7つのツール実装 ✅

1. **svi_check_connection** - ComfyUIへの接続確認
2. **svi_generate_video** - 動画生成
3. **svi_extend_video** - 動画延長
4. **svi_create_story_video** - ストーリー動画生成
5. **svi_get_queue_status** - キュー状態取得
6. **svi_get_history** - 実行履歴取得

### 3. Cursor設定スクリプト ✅

- **add_to_cursor_mcp.ps1**: CursorのMCP設定に自動追加

### 4. ドキュメント ✅

- **README.md**: 使用方法ガイド

---

## 🚀 使用方法

### ステップ1: Cursorを再起動

MCP設定を追加したので、Cursorを再起動してください。

### ステップ2: Cursorから直接使用

Cursorのチャットで以下のように入力すると、自動的にMCPツールが呼び出されます：

```
svi_generate_video を使って、画像 C:\path\to\image.png から「美しい風景」というプロンプトで5秒の動画を生成してください
```

```
svi_check_connection でComfyUIへの接続を確認してください
```

```
svi_create_story_video を使って、ストーリー動画を作成してください。開始画像は image.png、ストーリーは「笑顔→悲しい顔→驚いた顔」という展開にしてください
```

---

## 📋 利用可能なツール

### svi_generate_video
動画を生成します。

**パラメータ:**
- `start_image_path` (必須): 開始画像のパス
- `prompt` (必須): プロンプト（日本語可）
- `video_length_seconds` (オプション): 動画の長さ（秒、デフォルト: 5）
- `steps` (オプション): ステップ数（デフォルト: 6）
- `motion_strength` (オプション): モーション強度（デフォルト: 1.3）
- `sage_attention` (オプション): Sage Attention（デフォルト: true）

### svi_extend_video
既存の動画を延長します。

**パラメータ:**
- `previous_video_path` (必須): 前の動画のパス
- `prompt` (必須): 延長部分のプロンプト
- `extend_seconds` (オプション): 延長する秒数（デフォルト: 5）

### svi_create_story_video
ストーリー性のある長編動画を作成します。

**パラメータ:**
- `start_image_path` (必須): 開始画像のパス
- `story_prompts` (必須): ストーリープロンプトのリスト
- `segment_length_seconds` (オプション): 各セグメントの長さ（デフォルト: 5）

### svi_get_queue_status
ComfyUIのキュー状態を取得します。

### svi_get_history
実行履歴を取得します。

**パラメータ:**
- `max_items` (オプション): 取得する最大件数（デフォルト: 10）

### svi_check_connection
ComfyUIへの接続を確認します。

---

## 🔧 設定

### 環境変数

- `COMFYUI_URL`: ComfyUIのベースURL（デフォルト: http://localhost:8188）

### CursorのMCP設定

設定ファイル: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "svi-video": {
      "command": "python",
      "args": ["-m", "svi_mcp_server.server"],
      "env": {
        "COMFYUI_URL": "http://localhost:8188"
      },
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
    }
  }
}
```

---

## 📚 関連ファイル

- `svi_mcp_server/server.py` - MCPサーバー実装
- `svi_mcp_server/__main__.py` - エントリーポイント
- `svi_mcp_server/add_to_cursor_mcp.ps1` - Cursor設定追加スクリプト
- `svi_mcp_server/README.md` - 使用方法ガイド

---

## 🎯 次のステップ

1. ✅ MCPサーバー実装完了
2. ✅ ツール実装完了
3. ✅ Cursor設定追加完了
4. ⚠️ **Cursorを再起動**
5. ⚠️ 実際のワークフローノードをインストール（ComfyUI Managerから）

**進捗:** 実装完了 → **Cursor再起動で使用可能**

---

*実装完了日時: 2025-01-28*











