# ムフフがムフフにならない時のチェックリスト（マナ環境用）

ローカルなのにムフフがムフフにならないとき、**だいたい原因は3択**に収束する。

| 原因 | 内容 |
|------|------|
| **(A) ルーティングが外れてる** | ムフフ用のフラグやエンドポイントに投げておらず、一般用で処理されている |
| **(B) フィルタで薄味になってる** | ネガティブプロンプト強すぎ / LoRA弱い / CFG・Refiner で上品寄り |
| **(C) モデル側が“そういう絵”を出せない** | チェックポイントがSFW寄り / VAE不合 / Hi-res fix でのっぺり |

以下、マナの環境に合わせた**最短で潰すチェックリスト**。

---

## 1) まず確認：そもそも“ムフフ担当”に投げられてる？

ManaOS（Gallery API / MCP）や一括生成スクリプトを噛ませているならここが最有力。

### 確認ポイント

- **実際に呼ばれてるモデル名 / ワークフロー名 / LoRA名**をログで確認
  - 例：`text2img` に行ってるはずが `safe_text2img` や `general_image` になってない？
- **ムフフ用プロンプトが“一般用に正規化/要約”されてない？**
  - プロンプト最適化（prompt optimizer）や要約が噛むと、ムフフ成分が削げることがある。

### マナ環境での具体的な確認

| 経路 | 確認するもの |
|------|----------------|
| **Gallery API 経由** | リクエストに `mufufu_mode: true` が入っているか。`gallery_api_server.py` のログで `✅ ムフフモード:` が出ているか。 |
| **一括生成（直叩きComfyUI）** | `generate_50_mana_mufufu_manaos.py` 実行時に `--mode mufufu` を付けているか。 |
| **MCP（Cursor 等）** | 画像生成ツール呼び出しで `mufufu_mode: true`（または相当の引数）を渡しているか。 |

✅ **ここで「ムフフ用に投げてない」なら、画像生成側をいじってもムフフにならない。**

---

## 2) Stable Diffusion 系（ComfyUI）なら：NSFW が“薄味化”してる典型ポイント

### A. ネガティブプロンプトが強すぎ

学習・評価の癖で、ネガに「nude」「nipples」「sex」などを入れていると当然消える。

- **マナでの該当箇所**
  - `mufufu_config.py` の `get_default_negative_prompt_safe()`
    → `child, loli, teen, underage, nude, naked, nipples, ...` を付与している。
  - `generate_50_mana_mufufu_manaos.py` の `MUFUFU_NEGATIVE_PROMPT`
    → 身体崩れ対策に加え、上記の「安全用ネガ」を結合している。
- **やること**
  - 一度、ネガを**最低限（崩壊防止だけ）**にしてテスト。
  - 例：`bad anatomy, extra fingers, lowres` 程度にして出方を比較。

### B. LoRA の重みが弱い or LoRA が刺さってない

- LoRA がロードされているか（ComfyUI の UI 表示やログで確認）。
- 重み（strength）が 0.4 などだと薄いことがある → **0.8〜1.2 でテスト**。
- **マナ**：`generate_50_mana_mufufu_manaos.py` 内で LoRA 強度を渡している箇所と、`mufufu_config.RECOMMENDED_MODEL_LORA_PAIRS` を確認。

### C. CLIP skip / Refiner / CFG が原因で“上品化”

- **CFG が高すぎ（12 以上）** → 指示が硬くなったり無難に寄ることがある。
- **Refiner が強すぎ** → “それっぽい”が攻めない絵になりがち。
- **マナ**：`gallery_api_server.py` の `guidance_scale` や `mufufu_config.OPTIMIZED_PARAMS` を確認。

---

## 3) モデルが“そもそもムフフ弱い”パターン

ローカルで使っているチェックポイントが：

- **ベースモデルが SFW 寄り**（一般向け／検閲強め／学習データが薄い）
- **VAE が合っていない**（質感が死んで色気が消える）
- **Hi-res fix / アップスケール**でディテールが消えてのっぺり化

→ **割り切りで「ムフフ用のモデル（or LoRA）」を分離した方がよい。**

---

## 4) “安全フィルタ”がローカル内で動いている（地味に罠）

- 画像の **NSFW 判定**が後段で弾いて「無難な再生成」している。
- ワークフロー内に **Safety Checker** ノードがある（ComfyUI 系）。
- フロント（WebUI 拡張／自作 API）が **禁止ワード置換**している。

**ComfyUI**：ノード名に「Safety」「NSFW」「checker」が混じっていないか検索。
**自作 API**：入力 → 正規化 → 検閲 → 生成、のような中間処理がないか確認。
**マナ**：`stable_diffusion_generator.py` では `safety_checker=None`, `requires_safety_checker=False` で無効化している。ComfyUI のワークフロー自体は別途確認。

---

## 5) 10 分で切り分ける“最短テスト”

同じシードで条件だけ変えて原因を特定する。

1. **ルータ無しで直叩き**
   - ManaOS/Gallery API を経由せず、**ComfyUI に直接**投げる。
   - 例：`python generate_50_mana_mufufu_manaos.py -n 1 --mode mufufu`
2. **ネガティブ最小化**（上記 A の通り）
3. **LoRA 強め（例 1.0）**
4. **Safety っぽいノード／設定を一時 OFF**
5. 出力の差を比較する。

- **直叩きだとムフフになる** → **ManaOS／中間処理が犯人**
- **直叩きでもダメ** → **モデル／設定が犯人** で確定できる。

---

## ここから先：貼ってもらえれば即断するための 3 点

質問ではなく、**以下の 3 つを貼ってもらえれば「どこでムフフが消えているか」を特定し、直し方をピンポイントで指示しやすい。**

1. **使っている経路**
   - **WebUI？ComfyUI？それとも自作 API（ManaOS / Gallery API 経由）？**
2. **「生成に実際に使われた」モデル名（checkpoint）と LoRA 名**
   - マナ環境なら **評価 UI（localhost:9601）の「この画像」／「詳細」** で確認できる。
   - または **`C:\ComfyUI\input\mana_favorites\generation_metadata.json`** の該当生成の `model` / `loras` をコピー。
3. **生成ログの該当部分**
   - **モデルロード行**と、**プロンプトが最終的にどうなったか**が分かる部分。
   - 例：
     - Gallery API 経由なら `gallery_api_server.py` を起動しているターミナルのログ（`✅ ムフフモード:` の有無など）
     - 一括生成なら `generate_50_mana_mufufu_manaos.py` の標準出力
     - ComfyUI のコンソール出力（使用モデル・LoRA・プロンプト）

この 3 つがあれば、「どこでムフフが消えているか」を特定して、**直し方をピンポイントで指示**しやすい。
ムフフがムフフじゃないのはバグなので、一緒に潰していこう。

---

## 一括生成（`generate_50_mana_mufufu_manaos.py -n 100`）で「失敗」が出る場合

最後に表示される **「失敗 X 件」** は、次のいずれかでカウントされています。

| ログに出るメッセージ | 想定原因 | 対処 |
|----------------------|----------|------|
| `[ERROR] ComfyUI: ...` | ComfyUI が 200 で返したが JSON 内に `error` がある | メッセージ内容を確認。**チェックポイント／LoRA が見つからない**、**ノードの入力不正**、**キューあふれ**など |
| `[ERROR] プロンプトIDが取得できませんでした` | 200 だが `prompt_id` も `error` も無い異常応答 | 稀。ComfyUI のバージョンやワークフロー互換を確認 |
| `[ERROR] HTTP 500` など | ComfyUI がエラー status を返した | ComfyUI のコンソール／ログでクラッシュや OOM を確認 |
| `[ERROR] ... Connection refused` など | リクエスト時の例外（接続失敗・タイムアウト） | ComfyUI が起動しているか、`COMFYUI_URL`（既定は `http://127.0.0.1:8188`）が正しいか確認。POST は既定 90 秒タイムアウト（`COMFYUI_POST_TIMEOUT`）。接続・タイムアウト・5xx は自動リトライ（既定 2 回）あり |

**確認のコツ**

- 実行したターミナルに、失敗した枚の直前に **`[ERROR] ...`** が 1 行ずつ出ています。その行が原因です。
- `[ERROR] ComfyUI: Could not find checkpoint ...` → そのチェックポイントが ComfyUI のモデルフォルダに無い／名前不一致。
- `[ERROR] ComfyUI: ... node ...` → ワークフロー内のノード（モデル名・LoRA 名など）が環境と合っていない。
- 一定枚数ごとに失敗する → **キューが詰まっている**か、**メモリ不足で ComfyUI が落ちている**可能性。ComfyUI のコンソールを確認。

なお、**「出力待ちタイムアウト」**（`[WARN] 出力待ちタイムアウト（300秒）`）は **失敗件数には含まれません**。リクエストは成功しているが、画像ファイル名の取得だけがタイムアウトした状態です。画像は ComfyUI の出力フォルダに出ていることが多いので、そこで確認できます。

**スクリプト側の対策（実装済み）**

- **リトライ**: 接続エラー・タイムアウト・HTTP 5xx の場合、最大 2 回まで自動リトライ（間隔 3s, 6s）。回数は環境変数 `COMFYUI_MAX_RETRIES` で変更可。
- **タイムアウト**: POST のタイムアウトは既定 90 秒（`COMFYUI_POST_TIMEOUT` で変更可）。
- **エラー詳細**: ComfyUI が返す `error` に `node_id` や `details` があればログに出力。チェックポイント／LoRA 未検出っぽいメッセージには「モデル/LoRA が ComfyUI の models フォルダに存在するか・ファイル名を確認してください」のヒントを付与。
