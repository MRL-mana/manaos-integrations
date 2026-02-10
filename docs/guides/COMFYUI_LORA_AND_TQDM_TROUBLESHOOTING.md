# ComfyUI よくあるエラー対策（LoRA / tqdm）

## 1. 「lora key not loaded: diffusion_model.layers.X...」

### 原因

**DiT/SD3/Flux/LTX 用の LoRA** を、**SD1.5/SDXL 用のチェックポイント** に掛けていると出ます。

- SD1.5/SDXL の LoRA は `model.diffusion_model` 系のキー
- SD3/Flux/LTX などの DiT 系 LoRA は `diffusion_model.layers.X` 系のキー

キーが一致しないため、ComfyUI は「該当キーなし」としてロードせず、結果として **LoRA が効かない** うえ、ログが大量に出ます。

### 対処（当リポジトリの generate_50 を使っている場合）

`generate_50_mana_mufufu_manaos.py` では、**DiT/Flux/SD3/LTX 用と判断できる LoRA** を自動で除外しています。

- ファイル名に次のいずれかが含まれる LoRA は **常に除外**（safe/lab/use-all 共通）
  `flux`, `sd3`, `sdx3`, `ltx`, `ltx2`, `dit`, `wan2`, `wan2.2`
- これにより、SD1.5/SDXL 用ワークフローでは「lora key not loaded」の原因になる LoRA は使われません。

それでもログが出る場合は、**ComfyUI のワークフローや手動実行** で DiT 用 LoRA を SD1.5/SDXL モデルに掛けていないか確認してください。

---

## 1b. lora_unet_* key not loaded / ERROR lora ... shape is invalid

### 原因

**SD1.5 用 LoRA** を **SDXL モデル** に掛けている（またはその逆）と、キー名やテンソル形状が合わず次のように出ます。

- `lora key not loaded: lora_unet_output_blocks_X...`（SD1.5 側のキー名）
- `ERROR lora diffusion_model... shape '[10240, 1280]' is invalid for input of size ...`（次元の不一致）

### 対処（generate_50 の場合）

`generate_50_mana_mufufu_manaos.py` では、**SDXL モデル** のときは **SDXL 用と判断できる LoRA のみ** 使用するようにしています。

- ファイル名に `sdxl`, `_xl`, `xl_`, `pony`, `lux`, `illustrious`, `uwazumi`, `speciosa` のいずれかを含む LoRA のみ SDXL モデルに使用
- 該当する LoRA が無い場合は、その枚は **LoRA なし** で生成（shape エラーを防ぐ）

---

## 1c. Error while deserializing header: incomplete metadata, file not fully covered

### 原因

**チェックポイント（.safetensors）が破損している**か、**ダウンロード・コピーが途中**です。

### 対処

- 該当するチェックポイントを **再ダウンロード** する
- 別ドライブなどにコピーした場合は、**コピー完了**を確認してから使う
- 問題が続くファイルは `models/checkpoints` から一時退避し、別のモデルで生成する

---

## 2. OSError: [Errno 22] Invalid argument（tqdm / stderr flush）

### 原因

Windows で ComfyUI を **パイプやリダイレクト経由** で起動していると、サンプリング中の **tqdm のプログレスバー** が `sys.stderr.flush()` を呼んだタイミングで
`OSError: [Errno 22] Invalid argument` になり、処理が落ちることがあります。

- ターミナルがない／stderr が無効な状態で tqdm が stderr に書き込むため
- ComfyUI のロガーが stderr をラップしている環境で起きやすい

### 対処

1. **ComfyUI を「普通のコンソール」から起動する**
   例: `start_comfyui_local.ps1` や `python main.py` を、**新しい cmd/PowerShell ウィンドウ**で実行し、そのウィンドウを閉じない。
   バックグラウンドやパイプで起動しない。

2. **tqdm を無効にする**
   起動前に環境変数を設定する:
   ```powershell
   $env:TQDM_DISABLE = "1"
   python main.py --port 8188
   ```
   `start_comfyui_local.ps1` では、この設定をすでに行っています。

3. **ComfyUI を再起動する**
   上記のどちらかで起動し直すと、同じ条件では再発しにくくなります。

---

## 3. Exception ignored in: &lt;function tqdm.__del__ at ...&gt;

### 原因

tqdm のプログレスバーが破棄されるとき（`__del__`）に、Windows で stderr への書き込みが失敗し、「Exception ignored in ...」がログに出ます。

- **生成自体は完了している**（「Prompt executed in X.XX seconds」のあとに出る）
- プロセスは落ちないが、ログがノイズになります

### 対処

**ComfyUI を `TQDM_DISABLE=1` を設定した状態で起動する**と、tqdm が使われずこのメッセージは出ません。

- **推奨**: 当リポジトリの **`start_comfyui_no_tqdm.bat`** をダブルクリックして ComfyUI を起動する
  （`COMFYUI_BASE` が未設定の場合は `C:\ComfyUI` を使用します）
- または **`start_comfyui_local.ps1`** で起動（こちらも起動時に `TQDM_DISABLE=1` を設定しています）

ComfyUI を別の方法で起動している場合は、起動する **前** に環境変数を設定してください。

```batch
set TQDM_DISABLE=1
python main.py --port 8188
```

---

## まとめ

| 現象 | 主な原因 | 対処 |
|------|----------|------|
| lora key not loaded: diffusion_model.layers... | DiT/SD3/Flux/LTX 用 LoRA を SD1.5/SDXL に使用 | generate_50 は該当 LoRA を自動除外。手動では LoRA とモデル種別を一致させる |
| lora_unet_* not loaded / shape is invalid | SD1.5 用 LoRA を SDXL に（またはその逆） | generate_50 は SDXL モデルで SDXL 用 LoRA のみ使用。該当なしなら LoRA なしで生成 |
| incomplete metadata, file not fully covered | チェックポイント破損・未完了コピー | 再ダウンロードまたはコピー完了を確認。問題ファイルは退避 |
| OSError [Errno 22] Invalid argument（サンプリング中） | tqdm の stderr flush が Windows で失敗 | **`start_comfyui_no_tqdm.bat`** で ComfyUI を起動（`TQDM_DISABLE=1`） |
| Exception ignored in tqdm.__del__ | tqdm 破棄時に stderr 書き込みが失敗 | **`start_comfyui_no_tqdm.bat`** または **`start_comfyui_local.ps1`** で起動（`TQDM_DISABLE=1`） |
