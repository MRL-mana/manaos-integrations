# 現在の ComfyUI-LTXVideo (master) で登録されているノード（静的）

GitHub の `__init__.py`（master）から取得した静的ノード一覧です。
**ランタイムで追加されるノード**（`nodes_registry` 経由）もあるため、実際の一覧は ComfyUI 起動後に `python ltx2_list_available_nodes.py` で確認してください。

## 静的マッピング（__init__.py）

| ノード名 | 用途イメージ |
|----------|--------------|
| LTXVLinearOverlapLatentTransition | 潜在空間の線形オーバーラップ遷移 |
| LTXVAddGuideAdvanced | ガイド追加（詳細） |
| LTXVAddLatentGuide | 潜在ガイド追加 |
| LTXVAdainLatent | AdaIN 潜在 |
| LTXVImgToVideoConditionOnly | 画像→動画（条件のみ） |
| LTXVPerStepAdainPatcher | ステップごと AdaIN パッチ |
| LTXVApplySTG | STG 適用 |
| LTXVBaseSampler | ベースサンプラー |
| LTXVInContextSampler | インコンテキストサンプラー |
| LTXVExtendSampler | 拡張サンプラー |
| LTXVNormalizingSampler | 正規化サンプラー |
| LTXVPreprocessMasks | マスク前処理 |
| LTXVPatcherVAE | VAE パッチ |
| LTXVPromptEnhancer | プロンプト拡張 |
| LTXVPromptEnhancerLoader | プロンプト拡張ローダー |
| LTXVSelectLatents | 潜在の選択 |
| LTXVSetVideoLatentNoiseMasks | 動画潜在ノイズマスク設定 |
| LTXVTiledSampler | タイルサンプラー |
| LTXVLoopingSampler | ループサンプラー |
| LTXVTiledVAEDecode | タイル VAE デコード |
| LTXVStatNormLatent | 統計正規化潜在 |
| LTXVGemmaCLIPModelLoader | Gemma CLIP モデルローダー |
| LTXVGemmaEnhancePrompt | Gemma プロンプト拡張 |
| GemmaAPITextEncode | Gemma API テキストエンコード |
| LowVRAMCheckpointLoader | 低 VRAM チェックポイントローダー |
| LowVRAMAudioVAELoader | 低 VRAM オーディオ VAE ローダー |
| LowVRAMLatentUpscaleModelLoader | 低 VRAM 潜在アップスケールモデルローダー |
| LTXVLoadConditioning | 条件付けロード |
| LTXVSaveConditioning | 条件付け保存 |
| … (tricks / nodes_registry で追加分あり) |

## example ワークフローで参照されているが現行にないノード

- LTXVSeparateAVLatent
- LTXVConcatAVLatent
- LTXVEmptyLatentAudio / EmptyLTXVLatentVideo
- LTXVLatentUpsampler
- LTXVAudioVAEDecode
- LTXVSpatioTemporalTiledVAEDecode
- LTXVImgToVideoInplace

## 現行ノードだけでワークフローを組む場合

1. ComfyUI の UI で **現在表示されている LTX ノードだけ**を使って I2V ワークフローを手動で組み、**File → Export (API)** で保存する。
2. 保存した JSON を `run_ltx2_generate.py --workflow 保存したファイル.json` で実行する。

公式の「現行ノードのみ」の example がまだないため、上記か、`find_ltxv_node_commit.ps1` でノードが存在したコミットに合わせる方法を検討してください。
