# LTX-2「プロンプトの実行に失敗しました」の対処

実行時に出る代表的な3エラーと対処です。

---

## 1. LTXVGemmaCLIPModelLoader: 値がリストにありません (gemma_path)

**原因:** ワークフロー側のパスが `/`、ComfyUI のリストが `\` のため一致していない。

**実施済み対応:** ComfyUI-LTXVideo の `gemma_encoder.py` を修正済みです。
- ドロップダウンリストをスラッシュに正規化して両方受け付けるように変更
- `load_model` 内で `os.path.normpath` によりパスを正規化

**あなたがやること:** **ComfyUI を再起動**してから、もう一度ワークフローを実行してください。

---

## 2. LoadImage: 無効な画像ファイル distilled image.png

**原因:** 開始画像が ComfyUI の `input` フォルダにない。

**実施済み対応:** サンプル画像を `input` にコピーしました。
- コピー元: `ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows\assets\distilled image.png`
- コピー先: `C:\ComfyUI\input\distilled image.png`

**あなたがやること:** 特になし。別の画像を使う場合は、そのファイルを `C:\ComfyUI\input\` に置き、ワークフローの Load Image ノードでそのファイル名を選んでください。

---

## 3. LatentUpscaleModelLoader: model_name が [] にありません

**原因:** 空間アップスケーラーモデルが `models/unet` にない。

**あなたがやること:** 以下でモデルを取得し、指定フォルダに置いてください。

1. **ダウンロード**
   - Hugging Face: https://huggingface.co/Lightricks/LTX-2/resolve/main/ltx-2-spatial-upscaler-x2-1.0.safetensors
   - ブラウザで上記URLを開くか、`huggingface-cli download Lightricks/LTX-2 ltx-2-spatial-upscaler-x2-1.0.safetensors --local-dir C:\ComfyUI\models\unet` で取得

2. **配置**
   - 保存先: `C:\ComfyUI\models\unet\ltx-2-spatial-upscaler-x2-1.0.safetensors`
   - ファイル名は **そのまま** にしてください。

3. **再実行**
   - ComfyUI を再起動せずに、そのまま「Queue Prompt」で再実行して問題ありません（モデル一覧は起動時に読まれる場合があります。変わらなければ ComfyUI を再起動）。

---

## まとめ

| エラー | 対応 |
|--------|------|
| Gemma パス | ノード側を修正済み → **ComfyUI 再起動** |
| distilled image.png | `input` にコピー済み → そのまま利用可 |
| ltx-2-spatial-upscaler | **手動でダウンロード** → `models/unet` に配置 |

アップスケーラーを入れずにワークフローを試したい場合は、Latent Upscale を使うノードを外すか、別のアップスケール方法に差し替える必要があります。

---

## 推奨: 動画生成を成功させる手順

1. **ComfyUI を再起動**（gemma_encoder の修正を反映するため）
2. **チェックポイント**は `ltx-2-19b-distilled.safetensors` のまま。LTX-2 用でない LoRA は**接続しない**
3. **Latent アップスケールモデルを読み込む**ノードで `ltx-2-spatial-upscaler-x2-1.0.safetensors` を選択（一覧が空なら再起動後に再選択）
4. **プロンプトが長い場合**は、Enhancer を通すとトークン数が max_length(1024) を超えて失敗しやすい。  
   → **実施済み:** 入力が長いときは自動で切り詰めるように `_enhance` を修正済み。  
   → それでも失敗する場合は、Positive Prompt を短くするか、**Gemma 3 Model Loader** の **max_length** を **2048** に上げて試す
5. **Queue Prompt** で実行し、`C:\ComfyUI\output` または `C:\ComfyUI\output\video` に動画が保存されるか確認する
