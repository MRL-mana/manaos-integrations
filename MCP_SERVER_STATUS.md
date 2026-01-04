# ManaOS統合MCPサーバー 動作状況

## 実装状況

✅ **MCPサーバーは実装済みです**

`manaos_integrations/manaos_unified_mcp_server/` に実装されており、Cursorに設定済みです。

## 利用可能なツール一覧

### 1. SVI動画生成
- `svi_generate_video` - SVI × Wan 2.2で動画を生成
- `svi_extend_video` - 動画を延長
- `svi_get_queue_status` - キュー状態を取得

**状態**: ⚠️ ComfyUIが起動している必要があります

### 2. ComfyUI画像生成
- `comfyui_generate_image` - ComfyUIで画像を生成

**状態**: ⚠️ ComfyUIが起動している必要があります

### 3. Google Drive
- `google_drive_upload` - ファイルをアップロード ✅ **動作確認済み**
- `google_drive_list_files` - ファイル一覧を取得

**状態**: ✅ 動作中

### 4. Rows
- `rows_query` - AIクエリを実行
- `rows_send_data` - データを送信
- `rows_list_spreadsheets` - スプレッドシート一覧を取得

**状態**: ⚠️ Rows APIの認証が必要です

### 5. Obsidian
- `obsidian_create_note` - ノートを作成 ✅ **動作確認済み**
- `obsidian_search_notes` - ノートを検索

**状態**: ✅ 動作中

### 6. 画像ストック
- `image_stock_add` - 画像をストックに追加
- `image_stock_search` - 画像を検索

**状態**: ✅ 実装済み

### 7. 通知
- `notification_send` - 通知を送信

**状態**: ✅ 実装済み

### 8. 記憶システム
- `memory_store` - 記憶に情報を保存
- `memory_recall` - 記憶から情報を検索

**状態**: ✅ 実装済み（Dict形式でcontentを渡す必要があります）

### 9. LLMルーティング
- `llm_chat` - LLMとチャット（最適なモデルを自動選択）

**状態**: ⚠️ LLMモデルが利用可能である必要があります

### 10. 秘書機能
- `secretary_morning_routine` - 朝のルーチンを実行
- `secretary_noon_routine` - 昼のルーチンを実行
- `secretary_evening_routine` - 夕方のルーチンを実行

**状態**: ✅ 実装済み

## 使用方法

CursorでMCPサーバーが有効になっている場合、以下のように使用できます：

```
svi_generate_videoを使って動画を生成してください
comfyui_generate_imageを使って画像を生成してください
google_drive_uploadを使ってファイルをアップロードしてください
rows_queryを使ってスプレッドシートをクエリしてください
obsidian_create_noteを使ってノートを作成してください
memory_storeを使って情報を記憶に保存してください
llm_chatを使ってLLMとチャットしてください
```

## 動作確認済み機能

✅ Obsidianノート作成
✅ Google Driveアップロード

## 設定が必要な機能

⚠️ ComfyUI/SVI - ComfyUIを起動する必要があります
⚠️ Rows - API認証が必要です
⚠️ LLM - LLMモデルが利用可能である必要があります

## MCPサーバーの設定

Cursorの設定に既に追加済みです。`add_to_cursor_mcp.ps1`を実行することで設定できます。

設定ファイルの場所：
- Windows: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`









