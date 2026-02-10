# ManaOS統合MCPサーバー

Cursorから直接ManaOSのすべての機能を使用できる統合MCPサーバー

---

## ✅ 実装完了

- ✅ 統合MCPサーバー実装完了
- ✅ 30+のツール実装完了
- ✅ Cursor統合準備完了

---

## 🚀 Cursorから直接使う方法

### ステップ1: CursorのMCP設定に追加

1. **Cursorの設定を開く**
   - `Ctrl + ,` で設定を開く
   - または `File → Preferences → Settings`

2. **MCP設定を開く**
   - 検索バーで「MCP」を検索
   - 「MCP Servers」を開く

3. **ManaOS統合MCPサーバーを追加**
   ```json
   {
     "manaos-unified": {
       "command": "python",
       "args": ["-m", "manaos_unified_mcp_server.server"],
       "env": {
         "COMFYUI_URL": "http://localhost:8188",
         "MANAOS_INTEGRATION_API_URL": "http://localhost:9500",
         "OBSIDIAN_VAULT_PATH": "C:\\Users\\mana4\\Documents\\Obsidian Vault"
       },
       "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
     }
   }
   ```

4. **自動設定スクリプトを実行（推奨）**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations\manaos_unified_mcp_server
   .\add_to_cursor_mcp.ps1
   ```

5. **Cursorを再起動**

---

## 📋 利用可能なツール（30+）

### 🎬 動画生成（SVI × Wan 2.2）

- `svi_generate_video` - 動画生成
- `svi_extend_video` - 動画延長
- `svi_get_queue_status` - キュー状態取得

### 🎨 画像生成（ComfyUI）

- `comfyui_generate_image` - 画像生成
- `generate_sd_prompt` - 日本語説明からStable Diffusion用英語プロンプトを生成（Ollama llama3-uncensored）

### ☁️ Google Drive

- `google_drive_upload` - ファイルアップロード
- `google_drive_list_files` - ファイル一覧取得

### 📊 Rows（スプレッドシート）

- `rows_query` - AI自然言語クエリ
- `rows_send_data` - データ送信
- `rows_list_spreadsheets` - スプレッドシート一覧

### 📝 Obsidian

- `obsidian_create_note` - ノート作成
- `obsidian_search_notes` - ノート検索

### 🖼️ 画像ストック

- `image_stock_add` - 画像追加
- `image_stock_search` - 画像検索

### 🔔 通知

- `notification_send` - 通知送信

### 🧠 記憶システム

- `memory_store` - 記憶に保存
- `memory_recall` - 記憶から検索

### 💬 LLMルーティング

- `llm_chat` - LLMチャット（最適なモデルを自動選択）

### 🔬 Phase1 自己観察実験

- `phase1_run_off_3rounds` - OFF 3往復テスト（APIが localhost:9500 で PHASE1_REFLECTION=off で起動していること）
- `phase1_run_on_rounds` - ON N往復テスト（デフォルト15往復、PHASE1_REFLECTION=on で起動）
- `phase1_run_extended` - 拡張実験（condition=on/off, rounds=30）
- `phase1_save_run` - ログを phase1_runs/ にスナップショット保存
- `phase1_aggregate` - 集計（継続率・テーマ再訪・満足度）
- `phase1_compare_on_off` - ON/OFF 比較
- `phase1_run_multi_thread` - 複数スレッドで同一テーマ再訪を計測
- `phase1_low_satisfaction` - 満足度1〜2の理由を集約

### 👔 秘書機能

- `secretary_morning_routine` - 朝のルーチン
- `secretary_noon_routine` - 昼のルーチン
- `secretary_evening_routine` - 夜のルーチン

### 📱 デバイスオーケストレーター

- `device_discover` - 全デバイス（母艦・このは・X280・Pixel7）を検出
- `device_get_status` - デバイス状態・キュー・統計を取得

### 🤖 MoltBot

- `moltbot_submit_plan` - Plan を送信（intent=list_only/read_only, path）
- `moltbot_get_result` - 実行結果を取得
- `moltbot_health` - ヘルスチェック

---

## 💡 使用例

### Cursorから直接呼び出す場合

```
svi_generate_video を使って、画像 C:\path\to\image.png から「美しい風景」というプロンプトで5秒の動画を生成してください
```

```
comfyui_generate_image を使って、「a beautiful sunset」というプロンプトで画像を生成してください
```

```
google_drive_upload を使って、ファイル C:\path\to\file.pdf をGoogle Driveにアップロードしてください
```

```
rows_query を使って、スプレッドシート spreadsheet_id に対して「売上を集計して」というクエリを実行してください
```

```
obsidian_create_note を使って、「今日の作業まとめ」というタイトルでノートを作成してください。内容は「今日はSVI動画生成機能を実装しました」
```

```
memory_store を使って、「SVI動画生成の実装が完了した」という情報を記憶に保存してください
```

```
llm_chat を使って、「Pythonでリストをソートする方法を教えて」と質問してください
```

Cursorが自動的にMCPツールを呼び出します。

---

## 🔧 設定

### 環境変数

- `COMFYUI_URL`: ComfyUIのベースURL（デフォルト: http://localhost:8188）
- `MANAOS_INTEGRATION_API_URL`: ManaOS統合APIのURL（デフォルト: http://localhost:9500）
- `PORTAL_INTEGRATION_URL`: Portal APIのURL（デフォルト: http://localhost:5108）
- `OBSIDIAN_VAULT_PATH`: Obsidian Vaultのパス
- `MCP_DOMAIN`: ツールを分割して起動（`media` | `productivity` | `ai` | `devices` | `moltbot`）。空で全ツール

---

## 📚 関連ファイル

- `manaos_unified_mcp_server/server.py` - MCPサーバー実装
- `manaos_unified_mcp_server/__main__.py` - エントリーポイント
- `manaos_unified_mcp_server/add_to_cursor_mcp.ps1` - Cursor設定追加スクリプト

---

## 🎯 次のステップ

1. ✅ 統合MCPサーバー実装完了
2. ✅ 30+のツール実装完了
3. ⚠️ **CursorのMCP設定に追加**
4. ⚠️ **Cursorを再起動**

**進捗:** 実装完了 → **Cursor設定で使用可能**

---

*実装完了日時: 2025-01-28*
