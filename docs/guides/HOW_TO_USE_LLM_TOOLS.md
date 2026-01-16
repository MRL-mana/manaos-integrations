# 🚀 ローカルLLMが画像生成ツールを使う方法

**結論**: はい、**ローカルLLMは画像生成ツール（ComfyUI）を使うことができます！**

---

## ✅ 既に実装済みです！

今回実装した**MCP APIサーバー**を通じて、Open WebUIのローカルLLMがComfyUIなどの画像生成ツールを呼び出すことができます。

---

## 🔄 動作の流れ

```
┌─────────────────────────┐
│    ユーザー（あなた）   │
└────────────┬────────────┘
             │ "美しい風景の画像を生成して"
             ↓
┌─────────────────────────┐
│    Open WebUI (LLM)     │ ← ローカルLLM（LM Studio / Qwen）
│   (ポート3001)          │    「画像生成ツールを呼び出そう」
└────────────┬────────────┘
             │ Function Calling: comfyui_generate_image()
             ↓
┌─────────────────────────┐
│   MCP API Server        │ ← Open WebUIのExternal Tools設定
│   (ポート9502)          │    POST /api/mcp/tool/comfyui_generate_image
└────────────┬────────────┘
             │ API呼び出し
             ↓
┌─────────────────────────┐
│   Unified API Server    │ ← manaOS統合API
│   (ポート9500)          │    POST /api/comfyui/generate
└────────────┬────────────┘
             │ ComfyUI統合を呼び出し
             ↓
┌─────────────────────────┐
│   ComfyUI Server        │ ← 画像生成モデル（Stable Diffusion）
│   (ポート8188)          │    🖼️ 画像を生成
└────────────┬────────────┘
             │ 生成された画像を返す
             ↓
        ✅ 画像が生成されました！
```

---

## 📋 設定手順

### ステップ1: Open WebUIでExternal Toolsを設定

1. **Open WebUIにアクセス**: `http://localhost:3001`
2. **設定画面を開く**: 右上の⚙️アイコンをクリック
3. **「External Tools」タブ**を選択
4. **「Add Tool」**をクリック
5. 以下の情報を入力：

   ```
   Name: ManaOS統合MCP API
   URL: http://host.docker.internal:9502
   OpenAPI Spec: ON
   OpenAPI Spec URL: http://host.docker.internal:9502/openapi.json
   ```

6. **「Save」**をクリック

### ステップ2: ComfyUIサーバーを起動

```powershell
.\start_comfyui_local.ps1
```

### ステップ3: LLMがツールを使う

Open WebUIのチャット画面で、以下のように入力：

```
ユーザー: "美しい風景の画像を生成してください。サイズは512x512です。"
```

LLMが自動的に以下を実行します：

1. リクエストを解析: 「画像生成が必要だ」
2. ツールを選択: `comfyui_generate_image` ツールを使おう
3. パラメータを設定: prompt="美しい風景", width=512, height=512
4. ツールを呼び出し: MCP API Serverにリクエストを送信
5. 結果を受け取る: 生成された画像の情報を取得
6. ユーザーに報告: 「画像を生成しました！」

---

## 🎯 利用可能なツール

### 画像生成
- `comfyui_generate_image` - ComfyUIで画像を生成

### ファイル管理
- `google_drive_upload` - Google Driveにファイルをアップロード
- `google_drive_list_files` - Google Driveのファイル一覧を取得

### ノート管理
- `obsidian_create_note` - Obsidianにノートを作成
- `obsidian_search_notes` - Obsidianでノートを検索

### Web検索
- `web_search` - SearXNGでWeb検索
- `brave_search` - Brave SearchでWeb検索

### Open WebUI操作
- `openwebui_create_chat` - チャット作成
- `openwebui_list_chats` - チャット一覧取得
- `openwebui_send_message` - メッセージ送信

（他にも30+のツールが利用可能）

---

## ⚠️ 現在の状態

- ✅ **MCP APIサーバー**: 起動中（ポート9502）
- ✅ **Unified APIサーバー**: 起動中（ポート9500）
- ✅ **Open WebUI**: 起動中（ポート3001）
- ✅ **LLMがツールを呼び出す仕組み**: 実装済み
- ❌ **ComfyUIサーバー**: 起動していない（ポート8188）← **これが必要！**

---

## 💡 まとめ

**ローカルLLMは画像生成ツールを使うことができます！**

1. **LLM自体は画像を生成できない**
   - テキスト生成専用モデル

2. **しかし、LLMは画像生成ツールを呼び出すことができる**
   - Function Calling / Tool Use機能
   - これがまさに今回実装したMCP APIサーバーの目的

3. **必要なもの**
   - ✅ Open WebUI（ローカルLLM）
   - ✅ MCP APIサーバー（ツール提供）
   - ✅ ComfyUIサーバー（画像生成）← **現在起動していない**

4. **動作の流れ**
   - ユーザーが「画像を生成して」とLLMに依頼
   - LLMが`comfyui_generate_image`ツールを呼び出す
   - ComfyUIサーバーが画像を生成
   - LLMが結果をユーザーに報告

---

**結論**: ローカルLLMは画像生成ツール（ComfyUI）を使うことができます。ComfyUIサーバーを起動すれば、すぐにLLMから画像生成ツールを呼び出せます！
