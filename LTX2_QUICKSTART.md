# LTX-2 動画生成クイックスタート

## いちどだけやること（Export API）

ComfyUI でワークフローを開き、**File → Export (API)** で保存する（1回だけ）。

- **保存先を選べる場合**: `ltx2_workflows` フォルダに **`ltx2_i2v_from_ui.json`** という名前で保存。
- **保存先を選べない場合**: どこでもいいので保存（例: ダウンロード）→ プロジェクトで:
  ```powershell
  .\copy_ltx2_export.ps1 "C:\Users\mana4\Downloads\保存したファイル名.json"
  ```
  （パスは実際の保存場所に合わせる）

## あとは全部こちらのコマンドで

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\run_ltx2_all.ps1
```

プロンプトを変えたいとき:

```powershell
.\run_ltx2_all.ps1 "your prompt here"
```

→ パッチ → ComfyUI へ送信まで自動で実行します。

---

## 1. 環境

- **ComfyUI** を起動（例: `C:\ComfyUI` で `python main.py`）
- **ComfyUI-LTXVideo** が `custom_nodes` にインストール済み
- LTX-2 モデル（例: `ltx-2-19b-distilled.safetensors`）を配置済み

## 2. 動画生成の実行方法

### 方法A: 一括パイプライン（変換 → パッチ → 送信）

サブグラフを展開してAPI形式に変換し、ノード名をパッチしてから送信します。

```powershell
.\run_ltx2_full_pipeline.ps1
# プロンプトを指定する場合
.\run_ltx2_full_pipeline.ps1 "your prompt here"
```

例ワークフローが別バージョンのノード（例: `LTXVSeparateAVLatent`）を参照している場合、**「node XXX does not exist」** になることがあります。その場合は方法Bを使います。

### 方法B: UIで Export (API) したワークフローを使う（推奨）

ComfyUIのUIでワークフローを開き **File → Export (API)** で保存すると、利用中のComfyUIのノードに合ったAPI形式が得られます。

1. ブラウザで **http://127.0.0.1:8188** を開く
2. ワークフローを読み込む（**Load のやり方がわからない場合 → [LTX2_LOAD_WORKFLOW.md](LTX2_LOAD_WORKFLOW.md) を参照**）:
   - **簡単**: `.\open_ltx2_workflow_folder.ps1` でフォルダを開き、**LTX-2_I2V_Distilled_wLora.json** を ComfyUI のキャンバスに**ドラッグ＆ドロップ**
   - または画面上の **Load** ボタンを押し、上記パスの JSON を選択
3. メニュー **File → Export (API)** で JSON を保存（例: `ltx2_workflows/ltx2_i2v_from_ui.json`）
4. （任意）ノード名の違いがある場合はパッチをかける:
   ```bash
   python ltx2_patch_workflow.py ltx2_workflows/ltx2_i2v_from_ui.json ltx2_workflows/ltx2_i2v_ready.json
   ```

## 3. 動画生成の実行

```bash
# 環境チェック（接続とLTXノードの有無）
python run_ltx2_generate.py --check

# ワークフローのノードがComfyUIに存在するかだけ検証（送信しない）
python run_ltx2_generate.py --workflow ltx2_workflows/ltx2_i2v_ready.json --dry-run

# 生成実行（開始画像は ComfyUI の input フォルダに配置）
python run_ltx2_generate.py --workflow ltx2_workflows/ltx2_i2v_ready.json --prompt "a calm sea, sunset"

# プロンプトだけ変えて送信
python run_ltx2_generate.py --workflow ltx2_workflows/ltx2_i2v_ready.json --prompt "your prompt" --image your_image.png
```

## 4. スクリプト一覧

| スクリプト | 説明 |
|-----------|------|
| `run_ltx2_generate.py` | ワークフロー送信・完了待ち・出力表示（送信前にノード検証。`--dry-run` で検証のみ） |
| `ltx2_workflow_compat_check.py` | I2V用ノードの有無を確認（ComfyUI起動中に実行） |
| `ltx2_list_available_nodes.py` | ComfyUIで利用可能なLTX/動画関連ノード一覧を表示 |
| `ltx2_find_compatible_workflow.py` | example_workflows 内で現在のComfyUIと互換のワークフローを検出 |
| `ltx2_workflow_to_api.py` | nodes/links 形式 → API形式の変換（サブグラフは展開されない） |
| `ltx2_patch_workflow.py` | API形式のノード名パッチ（CM_FloatToInt → PrimitiveInt 等） |

**PowerShell（診断・コミット検索）:**

| スクリプト | 説明 |
|-----------|------|
| `run_ltx2_diagnose.ps1` | 接続・ノード一覧・互換ワークフローを一括診断 |
| `find_ltxv_node_commit.ps1` | ComfyUI-LTXVideo で LTXVSeparateAVLatent があったコミットを検索 |

## 出力フォルダを開く（PowerShell）

```powershell
explorer "C:\ComfyUI\output"
```

動画は `C:\ComfyUI\output\video` に保存されることがあります:

```powershell
explorer "C:\ComfyUI\output\video"
```

---

## 5. トラブルシューティング

- **「node XXX does not exist」／「LTXVSeparateAVLatent does not exist」**
  利用中の **ComfyUI-LTXVideo のバージョン**と、ワークフロー（例: LTX-2_I2V_Distilled_wLora）で使われているノードが一致していません。まず **一括診断** を実行してください:
  ```powershell
  .\run_ltx2_diagnose.ps1
  ```
  または個別に:
  ```powershell
  python ltx2_workflow_compat_check.py
  ```
  **不足ノードがある場合**:
  1. **利用可能なノード一覧を確認**: `python ltx2_list_available_nodes.py`
  2. **互換ワークフローを自動検出**: `python ltx2_find_compatible_workflow.py "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows"`
  3. 互換として表示されたワークフローを ComfyUI で開き **File → Export (API)** で保存し、`run_ltx2_generate.py --workflow 保存したファイル` で実行する。
  4. 互換が0件の場合は、`.\find_ltxv_node_commit.ps1` でノードが存在したコミットを探し、そのコミットに合わせるか、[LTX2_NODE_MISMATCH.md](LTX2_NODE_MISMATCH.md)・[LTX2_CURRENT_NODES.md](LTX2_CURRENT_NODES.md) を参照。公式 Issue: [ComfyUI-LTXVideo Issues](https://github.com/Lightricks/ComfyUI-LTXVideo/issues)。
- **「LTX-2ノードがありません」**
  ComfyUI-LTXVideo をインストールし、ComfyUI を再起動する。
- **「Unrecognized model in ... text_encoders」／Gemma が読み込めない**
  1. **ComfyUI-LTXVideo の model_root パッチ**（必須）:
     ```powershell
     $env:COMFYUI_PATH = "C:\ComfyUI"
     python patch_ltxv_gemma_encoder.py
     ```
     `gemma_path` がファイル指定のときにトークナイザーが親フォルダを参照するバグを修正します。1回だけ実行すればOKです。
  2. **config.json の修正**（必要な場合）:
     ```powershell
     python fix_gemma_config.py
     ```
     `models/text_encoders/<gemmaフォルダ>/config.json` に `model_type: "gemma3_text"` を追加または作成します。
  3. **Transformers のバージョン**: Gemma-3 対応は 4.50.0 以降です。ComfyUI で使っている Python で `pip install -U "transformers>=4.50.0"` を実行。
  4. 上記のあと、**ComfyUI を再起動**してからワークフローを再実行してください。
- **開始画像**
  ComfyUI の `input` フォルダに画像を置き、`--image ファイル名.png` で指定する。
