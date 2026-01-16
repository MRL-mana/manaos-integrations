# 🧠 LLMルーティングMCPサーバー

**Cursorから直接ManaOSのLLMルーティング機能を使用可能にするMCPサーバー**

---

## 🎯 概要

このMCPサーバーにより、Cursorから直接ManaOSのLLMルーティング機能を使用できます。

- **難易度分析**: プロンプトの難易度を分析して推奨モデルを返す
- **自動ルーティング**: 難易度に応じて適切なモデルを自動選択して実行
- **モデル一覧**: 利用可能なモデル一覧を取得

---

## 🚀 セットアップ

### 1. 依存関係のインストール

```powershell
pip install mcp requests
```

### 2. CursorのMCP設定に追加

```powershell
cd llm_routing_mcp_server
.\add_to_cursor_mcp.ps1
```

または手動で設定：

```json
{
  "mcpServers": {
    "llm-routing": {
      "command": "python",
      "args": ["-m", "llm_routing_mcp_server.server"],
      "env": {
        "MANAOS_INTEGRATION_API_URL": "http://localhost:9500",
        "LLM_ROUTING_API_URL": "http://localhost:9501"
      },
      "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
    }
  }
}
```

### 3. Cursorを再起動

---

## 📋 利用可能なツール

### 1. `analyze_llm_difficulty`

プロンプトの難易度を分析して、推奨モデルを返す（LLM呼び出しなし）

**パラメータ**:
- `prompt` (必須): ユーザーのプロンプト
- `code_context` (オプション): 関連コード

**使用例**:
```
Cursorのチャットで:
"この関数のタイポを修正して" というプロンプトの難易度を分析して
```

---

### 2. `route_llm_request`

LLMリクエストをルーティングして実行（難易度に応じて適切なモデルを自動選択）

**パラメータ**:
- `prompt` (必須): ユーザーのプロンプト
- `code_context` (オプション): 関連コード
- `prefer_speed` (オプション): 速度優先（デフォルト: true）
- `prefer_quality` (オプション): 品質優先（デフォルト: false）

**使用例**:
```
Cursorのチャットで:
"この関数のタイポを修正して" というプロンプトでLLMルーティングを実行して
```

---

### 3. `get_available_models`

利用可能なLLMモデル一覧を取得

**パラメータ**: なし

**使用例**:
```
Cursorのチャットで:
利用可能なLLMモデル一覧を取得して
```

---

## 💡 使用例

### 例1: 難易度分析

```
Cursorのチャットで:
"このコードをリファクタリングして" というプロンプトの難易度を分析して
```

**結果**:
```json
{
  "difficulty_score": 15.5,
  "difficulty_level": "medium",
  "recommended_model": "Qwen2.5-Coder-14B-Instruct"
}
```

---

### 例2: ルーティング実行

```
Cursorのチャットで:
"この関数のタイポを修正して" というプロンプトでLLMルーティングを実行して
```

**結果**:
```json
{
  "model": "Qwen2.5-Coder-7B-Instruct",
  "difficulty_score": 5.0,
  "difficulty_level": "low",
  "reasoning": "プロンプトが短く、単純なタスクのため軽量モデルを選択",
  "response": "修正後のコード...",
  "response_time_ms": 250,
  "success": true
}
```

---

## 🔧 設定

### 環境変数

- `MANAOS_INTEGRATION_API_URL`: 統合APIサーバーのURL（デフォルト: http://localhost:9500）
- `LLM_ROUTING_API_URL`: LLMルーティングAPIサーバーのURL（デフォルト: http://localhost:9501）

---

## 🚨 トラブルシューティング

### MCPサーバーが起動しない

1. **依存関係を確認**
   ```powershell
   pip install mcp requests
   ```

2. **APIサーバーが起動しているか確認**
   ```powershell
   .\check_llm_setup.ps1
   ```

### ツールが呼び出せない

1. **Cursorを再起動**
2. **MCP設定を確認**
   - `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

---

## 🔗 関連ドキュメント

- `README_CURSOR_LOCAL_LLM.md` - メインREADME
- `LLM_ROUTING_README.md` - API使い方ガイド
- `MANAOS_LLM_ROUTING.md` - 統合設計書

---

**これでCursorから直接LLMルーティング機能を使用可能！🔥**



















