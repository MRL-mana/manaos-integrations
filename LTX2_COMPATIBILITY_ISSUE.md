# LTX-2 ComfyUI互換性問題

## 問題の概要

ComfyUI-LTXVideoがComfyUIの最新バージョンと互換性がない可能性があります。

## 発生しているエラー

1. `ModuleNotFoundError: No module named 'comfy.ldm.lightricks.vae.audio_vae'`
2. `ImportError: cannot import name 'LTXFrequenciesPrecision' from 'comfy.ldm.lightricks.model'`
3. `ImportError: cannot import name 'LTXRopeType' from 'comfy.ldm.lightricks.model'`
4. `ImportError: cannot import name 'generate_freq_grid_np' from 'comfy.ldm.lightricks.model'`
5. `ImportError: cannot import name 'AudioVAE' from 'comfy.ldm.lightricks.vae.audio_vae'`

## 修正済みファイル

1. ✅ `latents.py` - `LATENT_DOWNSAMPLE_FACTOR`の代替定義を追加
2. ✅ `gemma_encoder.py` - `LTXFrequenciesPrecision`と`LTXRopeType`の代替定義を追加
3. ✅ `embeddings_connector.py` - `generate_freq_grid_np`、`interleaved_freqs_cis`、`split_freqs_cis`の代替定義を追加
4. ✅ `low_vram_loaders.py` - `AudioVAE`の代替定義を追加

## 根本的な原因

ComfyUIの最新バージョン（0.6.0）で、`comfy.ldm.lightricks`モジュールの構造が変更された可能性があります。

## 推奨される解決方法

### 方法1: ComfyUIのバージョンを確認

ComfyUI-LTXVideoがサポートしているComfyUIのバージョンを確認し、互換性のあるバージョンを使用する。

### 方法2: ComfyUI-LTXVideoを最新版に更新

ComfyUI-LTXVideoのGitHubリポジトリから最新版を取得：

```powershell
cd C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo
git pull
```

### 方法3: 一時的な回避策（現在実施中）

不足しているモジュールやクラスを直接定義する一時的な回避策を実装。

## 注意

現在の修正は一時的な回避策です。ComfyUI-LTXVideoの公式アップデートで修正される可能性があります。
