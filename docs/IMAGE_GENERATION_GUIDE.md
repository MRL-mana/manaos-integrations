# ManaOS 画像生成ガイド（Cursor / VS Code 共通）

画像生成の入口・前提条件・Cursor/VS Code での使い方をまとめます。

## 概要

| 方式 | Cursor | VS Code | 説明 |
|------|--------|---------|------|
| **Cursor 組み込み** | ✅ | ❌ | Cursor エージェントの「画像を生成」ツール（AI がプロンプトから画像生成） |
| **ComfyUI（MCP）** | ✅ | ✅ | MCP ツール `comfyui_generate_image`（ComfyUI が 8188 で起動していること） |
| **タスク / CLI** | ✅ | ✅ | VS Code タスク「ManaOS: Generate Image」または `scripts/generate_image_cli.py` |
| **API 直接** | - | - | `POST /api/comfyui/generate`（統合API 9502）または Tool Server `/generate_image`（9503） |
| **Gallery API MCP** | ✅ | ✅ | `gallery_generate_image`（ムフフ・裏モード・意図推定対応、要 Gallery API 5559） |

---

## ムフフモード・闇の実験室（lab）モード

| モード | 説明 | 利用箇所 |
|--------|------|----------|
| **ムフフモード** | セクシー寄り・身体崩れ対策強化（ネガ・ポジタグ追加、steps 最適化） | `mufufu_mode: true` / `--mufufu` |
| **裏モード（lab）** | ネガ最小限・表現はモデルに委ねる（崩壊防止のみ） | `lab_mode: true` / `--lab` / `profile: "lab"` |

- **統合API**・**comfyui_generate_image**・**CLI**・**Tool Server** すべてで `mufufu_mode` / `lab_mode` に対応済み。
- **Gallery API** (`gallery_generate_image`) は `mufufu_mode`・`lab_mode`・`use_intent_routing`（プロンプトから自動推定）に対応。
- 環境変数 `MANAOS_IMAGE_DEFAULT_PROFILE=lab` でデフォルトを lab に変更可能。

---

## プロンプト生成（日本語→SD英語）

| 入口 | 説明 |
|------|------|
| **generate_sd_prompt** (MCP) | 日本語説明から SD 用英語プロンプトを生成（Ollama llama3-uncensored） |
| **CLI --jp** | プロンプトを日本語として扱い、変換後に画像生成 |
| **タスク (JP→EN)** | VS Code タスクで日本語入力→変換→画像生成 |
| **API** | `POST /api/sd-prompt/generate` |

**フロー**: 日本語で「猫がベッドで寝ている」→ `generate_sd_prompt` → 英語プロンプト → `comfyui_generate_image`  
**前提**: Ollama 起動、`llama3-uncensored`（`ollama pull llama3:8b` 等）

---

## 前提条件

1. **ComfyUI** を `http://127.0.0.1:8188` で起動する（画像生成の実体）。
2. **統合API** を起動する（デフォルト `http://127.0.0.1:9502`）。  
   - 例: `python unified_api_server.py` または `start_vscode_cursor_services.py` で起動。
3. （任意）**Tool Server** を使う場合は `http://127.0.0.1:9503` で起動。
4. （任意）**Gallery API MCP**（`gallery_generate_image`・ムフフ・裏モード）を使う場合は `python gallery_api_server.py` で Gallery API を `http://127.0.0.1:5559` で起動。

---

## Cursor で使う

### 1. Cursor 組み込みの画像生成

- チャットで「〇〇の画像を生成して」と依頼すると、Cursor が組み込みの画像生成ツールを使う場合があります（プロダクト側の提供機能）。

### 2. ComfyUI 経由（MCP）

- **MCP ツール**: `comfyui_generate_image`
- **設定**: `~/.cursor/mcp.json` に `manaos-unified-api`（または `unified_api_mcp_server`）が登録されていれば利用可能。
- **使い方**: チャットで「ComfyUI で〇〇の画像を生成して」などと依頼すると、エージェントが `comfyui_generate_image` を呼びます。
- **パラメータ例**: `prompt`（必須）, `negative_prompt`, `width`, `height`, `steps`, `seed`, `mufufu_mode`, `lab_mode`, `profile` など。

---

## VS Code で使う

VS Code には Cursor のような組み込み画像生成はないため、次のいずれかで同じ ComfyUI 画像生成を使います。

### 1. Cline + MCP（推奨）

- **Cline** 拡張を入れたうえで、`vscode_cursor_integration.py` を実行すると **Cline 用 MCP** に `manaos-unified-api` が登録されます。
- Cline の AI に「ComfyUI で〇〇の画像を生成して」と依頼すると、`comfyui_generate_image` が使われます。
- **manaos-gallery-api** も登録されるため、`gallery_generate_image`（ムフフ・裏モード・意図推定対応）も利用可能。
- **設定ファイル**:  
  - Windows: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`  
  - （Code - Insiders / VSCodium の場合は対応する product フォルダ）

### 2. VS Code タスク

- **ManaOS: Generate Image** … 通常モード
- **ManaOS: Generate Image (Mufufu)** … ムフフモード
- **ManaOS: Generate Image (Lab)** … 闇の実験室モード
- **ManaOS: Generate Image (JP→EN)** … 日本語→英語変換後に画像生成
- **手順**:
  1. `Ctrl+Shift+P` → 「Tasks: Run Task」
  2. 「ManaOS: Generate Image」を選択
  3. プロンプトを入力（英語推奨）
- 内部で `scripts/generate_image_cli.py` が実行され、統合API の `POST /api/comfyui/generate` を呼びます。

### 3. CLI で直接実行

```bash
# 通常
python scripts/generate_image_cli.py "a beautiful sunset"

# ムフフモード
python scripts/generate_image_cli.py --mufufu "1girl, sexy lingerie"

# 裏モード（lab）
python scripts/generate_image_cli.py --lab "1girl, nude"

# 日本語→英語変換後に画像生成（Ollama要）
python scripts/generate_image_cli.py --jp "猫がベッドで寝ている"

# 対話モード
python scripts/generate_image_cli.py
```

- 統合API が起動しており、ComfyUI が 8188 で動いていれば、そのまま画像生成がキックされます。

---

## API 参照

### 統合API（推奨）

- **URL**: `POST http://127.0.0.1:9502/api/comfyui/generate`
- **Body 例**:
  ```json
  {
    "prompt": "a beautiful landscape",
    "negative_prompt": "blurry",
    "width": 512,
    "height": 512,
    "steps": 20,
    "seed": -1,
    "mufufu_mode": false,
    "lab_mode": false,
    "profile": "safe"
  }
  ```
- **応答**: `{"prompt_id": "xxx", "status": "success"}`  
  - 実際の画像は ComfyUI の出力ディレクトリ（および Gallery API 連携時はギャラリー）で確認。

### Tool Server

- **URL**: `POST http://127.0.0.1:9503/generate_image`
- **Body**: `prompt`, `width`, `height`, `steps`, `negative_prompt`, `mufufu_mode`, `lab_mode` など。
- 内部で統合API の `/api/comfyui/generate` を呼びます。

### MCP ツール（unified_api_mcp_server）

- **ツール名**: `comfyui_generate_image`
- **引数**: `prompt`（必須）, `negative_prompt`, `width`, `height`, `steps`, `seed`, `mufufu_mode`, `lab_mode`, `profile` など。
- Cursor / Cline から利用可能。

### generate_sd_prompt（プロンプト生成）

- **ツール名**: `generate_sd_prompt`
- **引数**: `description` または `prompt`（日本語説明）, `model`, `temperature`, `with_negative`
- 日本語→SD用英語プロンプトを生成。画像生成前に `comfyui_generate_image` に渡すプロンプトとして利用。

### Gallery API MCP（ムフフ・裏モード・意図推定）

- **ツール名**: `gallery_generate_image`
- **URL**: Gallery API（デフォルト `http://127.0.0.1:5559`）を利用。`python gallery_api_server.py` で起動。
- **引数**: `prompt`, `mufufu_mode`, `lab_mode`, `use_intent_routing`（プロンプトからムフフ/実験室を自動推定）など。
- **前提**: `vscode_cursor_integration.py` で `manaos-gallery-api` が MCP に登録されていること。

---

## トラブルシュート

1. **ComfyUI に接続できない**  
   - `http://127.0.0.1:8188/system_stats` にブラウザや curl でアクセスして応答を確認。

2. **統合API が動かない**  
   - `http://127.0.0.1:9502/health` で生存確認。  
   - ポートは環境変数 `UNIFIED_API_PORT` または `MANAOS_UNIFIED_API_PORT` で変更可能（例: 9510）。

3. **VS Code で MCP ツールが出ない**  
   - Cline を使っている場合: `vscode_cursor_integration.py` を再実行し、Cline の MCP 設定を更新したうえで「Developer: Reload Window」。

4. **日本語プロンプトで期待どおりにならない**  
   - `generate_sd_prompt`（日本語→SD向け英語）で翻訳してから `comfyui_generate_image` に渡す。  
   - CLI: `--jp` オプション（例: `python scripts/generate_image_cli.py --jp "猫がベッドで寝ている"`）  
   - タスク: 「ManaOS: Generate Image (JP→EN)」  
   - 前提: Ollama 起動、`llama3-uncensored` 利用（`ollama pull llama3:8b` 等）

---

## 関連ファイル

- **MCP 定義**: `unified_api_mcp_server/server.py`（`comfyui_generate_image`）
- **統合API**: `unified_api_server.py`（`/api/comfyui/generate`）
- **Tool Server**: `tool_server/main.py`（`/generate_image`）
- **ComfyUI 連携**: `comfyui_integration.py`（`generate_image`）
- **スキル**: `.cursor/rules/manaos-media-skill.mdc`
