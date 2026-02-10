# ムフフモード × 脱獄 Llama3（llama3-uncensored）

## ムフフモードとは（マナの言うムフフ）

**ムフフモード**は、このプロジェクトで「マナの言うムフフ」として定義している画像生成用プリセットです。

- **内容**: セクシー寄りの衣装・ポーズ・シチュ（露骨な性表現は含めない）。身体崩れ対策タグ・品質タグを自動適用。
- **プリセット**: `generate_50_mana_mufufu_manaos.py --mode mufufu` や Gallery API の `mufufu_mode: true` で有効。
- **設定**: `mufufu_config.py`（プロンプト順序・解剖タグ・推奨パラメータ）、`generate_50_mana_mufufu_manaos.py`（衣装・ポーズの選択肢）。

評価UIの「画像ごとの詳細表示」や再起動などの変更は、ムフフモードの定義を変えておらず、あくまで表示・運用の改善です。

---

脱獄 Llama3 を使うと、**日本語のシチュ説明から制限の少ない英語SDプロンプト**を生成できるため、ムフフモードのプロンプトを強化できます。

## 利用可否の確認

```powershell
python check_llama3_uncensored.py
```

- `[OK] llama3-uncensored は利用可能です。` → そのまま利用可能
- `[WARN] llama3-uncensored が Ollama に存在しません。` → 下記の作成手順を実行

## 脱獄 Llama3 の作成手順（未導入時）

1. **ベースモデルの取得**
   ```powershell
   ollama pull llama3:8b
   ```

2. **脱獄版の作成（リポジトリ直下で）**
   ```powershell
   cd c:\Users\mana4\Desktop\manaos_integrations
   ollama create llama3-uncensored -f Modelfile.llama3-uncensored
   ```

3. **確認**
   ```powershell
   ollama list
   ```
   `llama3-uncensored` が表示されればOK。

## ムフフモードでの使い方

- **MCP（Cursor）**: 「〇〇なシチュの画像プロンプトを生成して」と依頼 → `generate_sd_prompt` が `llama3-uncensored` で英語プロンプトを生成。そのプロンプトを ComfyUI や一括生成に渡せばムフフモードを強化できます。
- **API**: `POST /api/sd-prompt/generate` に `description`（日本語）を送ると、脱獄 Llama3 が英語のSDプロンプトを返します。n8n やスクリプトから ComfyUI に渡す連携が可能です。
- **一括生成との連携**: 将来的に `generate_50_mana_mufufu_manaos.py --use-llm-prompt` のようなオプションで、一部プロンプトを LLM 生成に切り替える拡張が可能です。

## 補足

- `Modelfile.llama3-uncensored` は「Stable Diffusion 用プロンプト生成に特化し、制限なく創造的なプロンプトを出力する」システムプロンプトで定義されています。
- SDプロンプト生成のデフォルトモデルは各所で `llama3-uncensored` に設定済み（Unified API / MCP / Core API）。作成済みであればそのまま利用できます。
