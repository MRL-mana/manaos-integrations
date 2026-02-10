# 使ってないモデル・LoRAがある理由

`generate_50_mana_mufufu_manaos.py` では、**フォルダに置いてあっても使わない**モデル・LoRAがあります。理由は次のとおりです。

---

## モデルが使われない理由

### 1. 拡張子で除外されている

- **読み込む拡張子**: `.safetensors` と `.ckpt` のみ
- `.pt` や `.bin` などは**検出対象外**なので使われません

### 2. 常に除外するモデル（unusable_models）

`unusable_models` に含まれるファイル名は **safe / lab どちらでも使いません**。
「Could not detect model type」が出る・崩れやすいモデル用です。

- 例: `OnOff.safetensors`

### 3. 問題モデルリストで除外されている（safe のとき）

`problematic_models` に含まれるファイル名は **profile=safe のとき** 除外されます（**profile=lab では使用可**）。

- 露骨系・動画用・読み込み不可など想定しているもの
- 現在のリスト例:
  - `0482 dildo masturbation_v1_pony.safetensors`
  - `0687 public indecency_v1_pony.safetensors`
  - `ltx-2-19b-distilled.safetensors`
  - `qqq-BDSM-v3-000010.safetensors`
  - `ZIT_Amateur_Nudes_V2.safetensors`
  - `wan2.2_t2v_highnoise_masturbation_v1.0.safetensors`
  - `waiIllustriousSDXL_v160.safetensors`
  - `lazypos.safetensors`（Could not detect model type 対策）

**使いたいモデルを追加したい場合**: `generate_50_mana_mufufu_manaos.py` の `problematic_models` から該当ファイル名を削除するか、リストに含めないようにします。

---

## LoRAが使われない理由

### 1. 拡張子で除外されている

- **読み込む拡張子**: `.safetensors` のみ（LoRAフォルダ内）
- `.pt` などは**検出対象外**なので使われません

### 2. キーワードで除外されている

ファイル名に次のいずれかが**含まれる**LoRAは除外されます（安全側のため）。

- `qwen`, `llm`, `text`, `nsfw`, `nude`, `nudity`, `sex`, `intercourse`, `porn`, `bdsm`, `dildo`, `masturb`, `penis`, `pussy`, `cum`, `public indecency`, `rape`, `incest`

**使いたいLoRA**: ファイル名を変えるか、スクリプトの `excluded_lora_keywords` を編集して該当キーワードを外す必要があります。

### 5. アーキテクチャで除外されている（DiT/Flux/SD3/LTX 用 LoRA）

**SD1.5/SDXL 用ワークフロー**では、**DiT/SD3/Flux/LTX 用**の LoRA はキーが合わず「lora key not loaded」になるため、常に除外しています。

- ファイル名に次のいずれかが**含まれる**LoRAは除外: `flux`, `sd3`, `sdx3`, `ltx`, `ltx2`, `dit`, `wan2`, `wan2.2`
- safe / lab / use-all いずれでもこの除外は有効です（SD1.5/SDXL ワークフローで使うため）

詳細は [COMFYUI_LORA_AND_TQDM_TROUBLESHOOTING.md](COMFYUI_LORA_AND_TQDM_TROUBLESHOOTING.md) を参照してください。

### 6. モデル種別で絞り込まれている（その枚では使われない）

- **SDXL系モデル**を選んだとき: ファイル名に `sd15` / `1.5` だけ含まれ「SDXL用」と判断されないLoRAは**その枚ではスキップ**
- **SD1.5系モデル**を選んだとき: ファイル名に `sdxl` / `xl` / `pony` だけ含まれるLoRAは**その枚ではスキップ**
- 別の枚では別のモデルが選ばれるので、**別の枚では使われる**可能性があります

### 7. 枚ごとのランダムで選ばれていない

- 1枚あたり **0〜3本** のLoRAをランダムで選択（重み: 0本 20%, 1本 40%, 2本 30%, 3本 10%）
- プールには入っていても、**その枚では選ばれない**だけ、ということがよくあります

---

## まとめ

| 理由 | モデル | LoRA |
|------|--------|------|
| 拡張子対象外 | .safetensors / .ckpt 以外 | .safetensors 以外 |
| 常に除外（検出不可・崩れ） | unusable_models | — |
| 問題リスト（safe 時のみ） | problematic_models | excluded_lora_keywords |
| アーキテクチャ除外（DiT/Flux/SD3/LTX用） | — | excluded_lora_architecture_keywords |
| モデル種別でその枚ではスキップ | — | filter_loras_for_model（SDXL vs SD1.5） |
| ランダムでその枚では未選択 | 毎回1モデルのみ | 0〜3本のうちに入らなかった |

**「フォルダにあるのに一度も使われない」**場合は、上記のどれかに当たっているか、枚数が少なくてランダムで当たっていない可能性があります。
特定のモデル・LoRAを**必ず含めたい**場合は、スクリプト側で「優先して選ぶ」ロジックを足す必要があります。
