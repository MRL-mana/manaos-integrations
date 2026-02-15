# 画像生成スクリプト 問題点・改善点

`generate_50_mana_mufufu_manaos.py` および関連設定の確認結果と対応内容です。

---

## 対応済み（実装した改善）

### 1. モデル0件でクラッシュ
- **問題**: `available_models` が空のときに `random.choice(available_models)` で IndexError
- **対応**: ループ前にチェックし、0件ならメッセージを出して `sys.exit(1)`

### 2. ComfyUIエラー内容が分からない
- **問題**: HTTP 非200や ComfyUI の `error` ボディを表示していなかった
- **対応**:
  - 200 でも `result.error` があれば表示して失敗扱い
  - 非200のときは `response.text` の先頭500文字を表示

### 3. 出力待ちで何も表示されない
- **問題**: `wait_for_output_filenames` が最大5分待つが、タイムアウト・進捗が分からない
- **対応**:
  - 30秒ごとに「... 出力待ち N秒」を表示
  - タイムアウト時に「[WARN] 出力待ちタイムアウト（300秒）」を表示

### 4. パス・URLの固定
- **問題**: ComfyUI のパス・URLが `C:/ComfyUI` 固定
- **対応**: 環境変数で上書き可能に
  - `COMFYUI_URL` … API URL（既定: http://127.0.0.1:8188）
  - `COMFYUI_BASE` … ベースパス（既定: C:/ComfyUI）
  - `COMFYUI_MODELS` … checkpoints フォルダ
  - `COMFYUI_LORAS` … loras フォルダ

### 5. バックグラウンド実行でログが溜まってから出る
- **対応**: 重要ログに `flush=True` を付与（既に対応済み）

---

## 追加対応済み（2026年）

### 1. ComfyUI 起動確認
- 生成開始前に `/system_stats` で接続確認
- 失敗時は明確なメッセージで即終了

### 2. リトライ・タイムアウト
- POST /prompt の一時失敗時に最大2回リトライ（接続・タイムアウト・5xx）
- POST タイムアウト 90秒（環境変数で変更可）

### 3. 評価UI フィルタ・ソート
- `/api/images` でバックエンド側にフィルタ・ソート適用
  - フィルタ: 未評価/評価済み/高評価、プロファイル、モデル
  - ソート: 新着/古い/評価高い/低い順

### 4. 評価UI UX
- 読み込み中表示
- キーボードショートカット: 1〜4でスコア、Ctrl+Enterで保存
- ダークモード切り替え（localStorage で保持）
- モバイル対応（600px以下で1カラム表示）

### 5. 学習データ不足時の案内
- 評価データやメタデータがない場合に「評価UIで評価すると」「一括生成で作成すると」と案内

---

## 残している課題・今後の改善案

### 1. 並列送信
- 現状は1枚ずつ「送信 → 出力待ち」の直列。ComfyUI のキューに複数投入して並列化すると時間短縮の余地あり（キュー飽和には注意）

### 4. OPTIMIZED_PARAMS の未使用
- `mufufu_config.OPTIMIZED_PARAMS`（steps, sampler 等）をスクリプト側で参照していない。学習結果が無いときのデフォルトとして使うと品質が安定しやすい

### 5. サンプラー名の互換
- ComfyUI のノード名（例: `euler_ancestral`, `dpmpp_2m`）がバージョンで変わる可能性。存在チェックやフォールバックがあると安全

### 6. 評価DB・メタDBの読み込み失敗
- `learn_from_evaluations` で JSON 読み込みに失敗しても続行しているが、ログに「評価データをスキップしました」などを出すと原因追いがしやすい

---

## 使い方（再掲）

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations

# 1枚・ムフフ・新規優先
python -u generate_50_mana_mufufu_manaos.py -n 1 --mode mufufu --prefer-new

# 10枚・ムフフ・新規優先
python -u generate_50_mana_mufufu_manaos.py -n 10 --mode mufufu --prefer-new
```

環境変数で ComfyUI の場所を変える例:

```powershell
$env:COMFYUI_BASE = "D:\ComfyUI"
python -u generate_50_mana_mufufu_manaos.py -n 5 --mode mufufu
```
