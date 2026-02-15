# sd-prompt 運用ガイド（CLI / MCP / API）

日本語の説明から Stable Diffusion 用の英語プロンプトを生成する機能の使い方です。Ollama の `llama3-uncensored` を利用します。

## 前提

- **Ollama** が起動していること（`ollama list` で `llama3-uncensored` が表示されること）
- モデルがない場合: `ollama pull llama3:8b` のあと、リポジトリの `Modelfile.llama3-uncensored` で `ollama create llama3-uncensored -f Modelfile.llama3-uncensored` を実行

環境変数（任意）:

- `OLLAMA_URL` … デフォルト `http://127.0.0.1:11434`

---

## 1. CLI（sd-prompt）

### インストール

```powershell
# リポジトリ直下で
.\install_sd_prompt.ps1
```

PATH に `%USERPROFILE%\.manaos\bin` が追加され、どこからでも `sd-prompt` が使えます。**新しいターミナル**を開いてから使ってください。

### 使い方

```powershell
# 基本
sd-prompt "猫がベッドで寝ている"
sd-prompt "美しい夕日と海"

# ネガティブプロンプトも表示
sd-prompt -WithNegative "夜の街のネオン"

# ネガティブを LLM で生成（時間がかかることがあります）
sd-prompt -WithNegative -GenerateNegative "夜の街のネオン"

# クリップボードに Positive と Negative を両方コピー
sd-prompt -WithNegative -Clipboard both "夕焼けの海"

# モデル・温度・タイムアウト
sd-prompt -Model llama3-uncensored -Temperature 0.8 -TimeoutSec 120 "宇宙船"
```

### アンインストール

```powershell
.\uninstall_sd_prompt.ps1
```

---

## 2. MCP（Cursor から）

統合 MCP サーバーに **`generate_sd_prompt`** ツールが登録されています。

- **description**（必須）: 画像の日本語説明
- **model**: デフォルト `llama3-uncensored`
- **temperature**: 0.0〜1.0、デフォルト 0.9
- **with_negative**: `true` でデフォルトのネガティブプロンプトも返す

Cursor のチャットで「〇〇という画像の SD プロンプトを生成して」と依頼すると、このツールが使われます。

---

## 3. Core API（manaos_core_api.py）

Python から `ManaOSCoreAPI` の `act()` で呼び出します。

```python
from manaos_core_api import ManaOSCoreAPI

api = ManaOSCoreAPI()
result = api.act("generate_sd_prompt", {
    "prompt": "猫がベッドで寝ている",  # または "description"
    "model": "llama3-uncensored",
    "temperature": 0.9,
    "with_negative": True,
})
# result["prompt"] … 正規化された英語プロンプト
# result["negative_prompt"] … with_negative が True のときのみ
```

アクション名は `generate_sd_prompt` または `sd_prompt` のどちらでも可です。

---

## 4. Unified API（HTTP）

Unified API サーバーが起動している場合、次のエンドポイントが使えます。

**POST** `/api/sd-prompt/generate`

| キー | 型 | 説明 |
|------|-----|------|
| description または prompt | string | 日本語の説明（必須） |
| model | string | デフォルト `llama3-uncensored` |
| temperature | number | デフォルト 0.9 |
| with_negative | boolean | デフォルトのネガティブも返す |

例:

```bash
curl -X POST http://127.0.0.1:9502/api/sd-prompt/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "猫がベッドで寝ている", "with_negative": true}'
```

レスポンス例:

```json
{
  "success": true,
  "prompt": "a cat sleeping on a bed, ...",
  "description": "猫がベッドで寝ている",
  "model": "llama3-uncensored",
  "negative_prompt": "lowres, worst quality, ..."
}
```

---

## 運用のポイント

- **CLI**: インストール後は新しいターミナルで `sd-prompt "説明"` を実行。
- **MCP**: Cursor で「〇〇の画像プロンプトを生成して」と話しかけると `generate_sd_prompt` が使われる。
- **API**: 他サービスや n8n から `POST /api/sd-prompt/generate` でプロンプト取得 → ComfyUI などに渡す連携が可能。

生成されたプロンプトは「Create an image of...」などの定型句が自動で除去されます（CLI / MCP / Core API / Unified API 共通）。

