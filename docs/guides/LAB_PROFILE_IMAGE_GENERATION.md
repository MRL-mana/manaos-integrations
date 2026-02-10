# 闇の実験室（lab）プロファイル — 刺激的・裸など画像生成

「裸」「もっと刺激的な画像」を出したい場合、**闇の実験室（lab）** プロファイルを使います。
通常世界（safe）ではネガティブプロンプトに「nude, naked, nipples...」などの**安全タグ**が入り表現が抑制されますが、lab では**ネガは崩壊防止のみ**で、表現の上限は**モデル・LoRA**に委ねます。

---

## 1. Gallery API（推奨）

**lab_mode: true** を付けて生成します。

```json
POST /generate
{
  "prompt": "1girl, ...",
  "lab_mode": true
}
```

- ネガティブは `mufufu_config_lab.LAB_NEGATIVE_PROMPT` のみ（解剖・品質の崩れ防止、露骨抑制タグなし）
- 出力は `output/lab` に保存されます
- プロンプトに「lab」「実験室」「闇」「露骨」などが含まれると `use_intent_routing: true` 時に自動で lab_mode になる場合があります

---

## 2. Unified API（ComfyUI 生成）

**profile: "lab"** または **lab_mode: true** を付けてください。

```json
POST /api/comfyui/generate
{
  "prompt": "1girl, ...",
  "profile": "lab"
}
```

または

```json
{
  "prompt": "1girl, ...",
  "lab_mode": true
}
```

- ネガは崩壊防止のみになり、安全タグは付きません

---

## 3. 一括生成（generate_50_mana_mufufu_manaos.py）

**--profile lab** で実行します。

```bash
python generate_50_mana_mufufu_manaos.py --profile lab -n 10
```

- ネガは `mufufu_config_lab.LAB_NEGATIVE_PROMPT` のみ
- 出力は `output/lab` に保存されます

---

## 4. LTX-2 Infinity（動画）

動画生成で NSFW を許可する場合は **nsfw_allowed: true** を渡します。

```json
POST /api/ltx2-infinity/generate
{
  "image_path": "...",
  "base_prompt": "...",
  "nsfw_allowed": true
}
```

---

## 5. モデル・LoRA について

- **使いたい露骨系モデル／LoRA** が `generate_50_mana_mufufu_manaos.py` の `problematic_models` に入っていると除外されます。
- 使う場合は `generate_50_mana_mufufu_manaos.py` 内の `problematic_models` から該当ファイル名を削除するか、リストに含めないようにしてください。
  詳細は [WHY_SOME_MODELS_LORAS_UNUSED.md](WHY_SOME_MODELS_LORAS_UNUSED.md) を参照。

---

## まとめ

| 用途           | 設定 |
|----------------|------|
| Gallery API    | `lab_mode: true` |
| Unified API    | `profile: "lab"` または `lab_mode: true` |
| 一括生成       | `--profile lab` |
| LTX-2 Infinity | `nsfw_allowed: true` |

「過去にはできた」「実験室モードができる前にもやってた」のは、当時は**ネガに安全タグ（nude, naked...）を足していなかった**ためです。今でも同じ挙動にする方法は次のとおりです。

### 毎回指定しないで「昔のデフォルト」にしたい場合

環境変数 **MANAOS_IMAGE_DEFAULT_PROFILE=lab** を設定すると、**指定がないときは lab（ネガ最小限）** になります。

- **一括生成**: `--profile` を付けないと lab がデフォルト
- **Gallery API**: `lab_mode` を付けないリクエストでも lab 扱い
- **Unified API**: `profile` / `lab_mode` を付けないリクエストでも lab 扱い

```bash
# .env またはシェルで
MANAOS_IMAGE_DEFAULT_PROFILE=lab
```

明示的に safe にしたいときは、従来どおり `profile: "safe"` や `--profile safe` を指定してください。
