# 🤖 ローカルLLMが画像生成ツールを使う仕組み

**質問**: ローカルLLMが画像生成のアプリとかツール使うことはできないの？

**回答**: **はい、できます！** これがまさに**Function Calling（関数呼び出し）**や**Tool Use（ツール使用）**の機能です。

---

## ✅ 実は既に実装済みです！

今回実装した**MCP APIサーバー**を通じて、ローカルLLM（Open WebUI経由）が画像生成ツール（ComfyUI）を呼び出すことができます。

---

## 🔄 動作の流れ

```
┌─────────────────┐
│   Open WebUI    │ ← ローカルLLM（LM Studio / Qwen）
│  (LLMチャット)  │
└────────┬────────┘
         │ ユーザー: "美しい風景の画像を生成して"
         ↓
         │ LLMが解析: "画像生成ツールを使おう"
         ↓
         │ Function Calling: comfyui_generate_image()
         ↓
┌─────────────────┐
│  MCP API Server │ ← Open WebUIのExternal Tools設定
│  (ポート9502)   │
└────────┬────────┘
         │ API呼び出し: POST /api/mcp/tool/comfyui_generate_image
         ↓
┌─────────────────┐
│  Unified API    │ ← manaOS統合API
│  (ポート9500)   │
└────────┬────────┘
         │ ComfyUI統合を呼び出し
         ↓
┌─────────────────┐
│  ComfyUI Server │ ← 画像生成モデル（Stable Diffusion）
│  (ポート8188)   │   生成された画像を返す
└─────────────────┘
```

---

## 🎯 実装済みの機能

### 1. **MCP APIサーバー**（ポート9502）
- Open WebUIから呼び出し可能なツールを提供
- ComfyUI画像生成ツールを含む30+のツール

### 2. **Open WebUIのExternal Tools設定**
- MCP APIサーバーを外部ツールとして登録可能
- OpenAPI仕様でツールを自動認識

### 3. **Function Calling対応**
- ローカルLLMがツールを認識して呼び出し可能
- 「画像を生成して」と言うだけで、自動的にComfyUIを呼び出す

---

## 📋 設定手順（既に実装済み）

### ステップ1: Open WebUIでExternal Toolsを設定

1. Open WebUIにアクセス: `http://localhost:3001`
2. 設定画面（右上の⚙️）を開く
3. 「**External Tools**」タブを選択
4. 「**Add Tool**」をクリック
5. 以下の情報を入力：

   - **Name**: `ManaOS統合MCP API`
   - **URL**: `http://host.docker.internal:9502`
   - **OpenAPI Spec**: `ON`
   - **OpenAPI Spec URL**: `http://host.docker.internal:9502/openapi.json`

6. 「**Save**」をクリック

### ステップ2: LLMがツールを使う

Open WebUIのチャット画面で：

```
ユーザー: "美しい風景の画像を生成してください。サイズは512x512です。"
↓
LLM: "画像生成ツールを呼び出します..."
↓
LLM: comfyui_generate_image()を呼び出す
↓
ComfyUI: 画像を生成
↓
LLM: "画像を生成しました！"
```

---

## ⚠️ 現在の問題点

**ComfyUIサーバーが起動していません**（ポート8188で応答なし）

つまり：
- ✅ LLMがツールを呼び出す仕組み: **実装済み**
- ✅ MCP APIサーバー: **起動中**（ポート9502）
- ✅ Open WebUIの設定: **設定可能**
- ❌ ComfyUIサーバー: **起動していない**（ポート8188）

---

## 🚀 解決方法

### ComfyUIサーバーを起動する

```powershell
.\start_comfyui_local.ps1
```

これで、LLMがツールを呼び出して画像を生成できるようになります。

---

## 💡 まとめ

**ローカルLLMは画像生成ツールを使うことができます！**

1. **LLM自体は画像を生成できない**
   - テキスト生成専用

2. **しかし、LLMは画像生成ツールを呼び出すことができる**
   - Function Calling / Tool Use機能
   - これがまさに今回実装したMCP APIサーバーの目的

3. **動作の流れ**
   - ユーザーが「画像を生成して」とLLMに依頼
   - LLMがcomfyui_generate_imageツールを呼び出す
   - ComfyUIサーバーが画像を生成
   - LLMが結果をユーザーに報告

4. **必要なもの**
   - ✅ Open WebUI（ローカルLLM）
   - ✅ MCP APIサーバー（ツール提供）
   - ✅ ComfyUIサーバー（画像生成）← **現在起動していない**

---

**結論**: ローカルLLMは画像生成ツール（ComfyUI）を使うことができます。ただし、ComfyUIサーバー自体が起動している必要があります。

ComfyUIサーバーを起動すれば、すぐにLLMから画像生成ツールを呼び出せます！
