# SVI × Wan 2.2 動画生成 MCPサーバー

Cursorから直接SVI × Wan 2.2の動画生成を実行できるMCPサーバー

---

## ✅ 実装完了

- ✅ MCPサーバー実装完了
- ✅ 7つのツール実装完了
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

3. **SVI MCPサーバーを追加**
   ```json
   {
     "svi-video": {
       "command": "python",
       "args": ["-m", "svi_mcp_server.server"],
       "env": {
         "COMFYUI_URL": "http://127.0.0.1:8188"
       },
       "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
     }
   }
   ```

4. **Cursorを再起動**

5. **Cursorから直接呼び出し**
   ```
   svi_generate_video を使って、画像から動画を生成してください
   ```

---

## 📋 利用可能なツール

### 1. svi_check_connection
ComfyUIへの接続を確認します。

### 2. svi_generate_video
SVI × Wan 2.2で動画を生成します。
- `start_image_path`: 開始画像のパス（必須）
- `prompt`: プロンプト（日本語可、必須）
- `video_length_seconds`: 動画の長さ（秒、デフォルト: 5）
- `steps`: ステップ数（6-12推奨、デフォルト: 6）
- `motion_strength`: モーション強度（1.3-1.5推奨、デフォルト: 1.3）
- `sage_attention`: Sage Attentionを有効にするか（デフォルト: true）

### 3. svi_extend_video
既存の動画を延長します。
- `previous_video_path`: 前の動画のパス（必須）
- `prompt`: 延長部分のプロンプト（必須）
- `extend_seconds`: 延長する秒数（デフォルト: 5）
- `steps`: ステップ数（デフォルト: 6）
- `motion_strength`: モーション強度（デフォルト: 1.3）

### 4. svi_create_story_video
ストーリー性のある長編動画を作成します。
- `start_image_path`: 開始画像のパス（必須）
- `story_prompts`: ストーリープロンプトのリスト（必須）
- `segment_length_seconds`: 各セグメントの長さ（秒、デフォルト: 5）
- `steps`: ステップ数（デフォルト: 6）
- `motion_strength`: モーション強度（デフォルト: 1.3）

### 5. svi_get_queue_status
ComfyUIのキュー状態を取得します。

### 6. svi_get_history
実行履歴を取得します。
- `max_items`: 取得する最大件数（デフォルト: 10）

---

## 🔧 設定

### 環境変数

- `COMFYUI_URL`: ComfyUIのベースURL（デフォルト: http://127.0.0.1:8188）

---

## 💡 使用例

### Cursorから直接呼び出す場合

```
svi_generate_video を使って、画像 C:\path\to\image.png から「美しい風景」というプロンプトで5秒の動画を生成してください
```

```
svi_create_story_video を使って、ストーリー動画を作成してください。開始画像は image.png、ストーリーは「笑顔→悲しい顔→驚いた顔」という展開にしてください
```

Cursorが自動的にMCPツールを呼び出します。

---

## ⚠️ 注意事項

- ComfyUIサーバーが起動している必要があります
- 開始画像のパスは絶対パスで指定してください
- 実際のワークフローノードがComfyUIにインストールされている必要があります

---

## 🎯 次のステップ

1. ✅ MCPサーバー実装完了
2. ✅ ツール実装完了
3. ⚠️ CursorのMCP設定に追加
4. ⚠️ 実際のワークフローノードをインストール

**進捗:** 実装完了 → **Cursor設定で使用可能**











