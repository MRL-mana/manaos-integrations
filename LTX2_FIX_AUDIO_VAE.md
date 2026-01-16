# LTX-2 audio_vaeモジュールエラー修正

## 問題

ComfyUI-LTXVideoのインポートエラー：
```
ModuleNotFoundError: No module named 'comfy.ldm.lightricks.vae.audio_vae'
```

## 原因

`comfy.ldm.lightricks.vae.audio_vae`モジュールがComfyUIに存在しないため、ComfyUI-LTXVideoが正しく読み込まれません。

## 修正内容

`C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\latents.py`を修正して、`LATENT_DOWNSAMPLE_FACTOR`を直接定義するようにしました。

### 修正前
```python
from comfy.ldm.lightricks.vae.audio_vae import LATENT_DOWNSAMPLE_FACTOR
```

### 修正後
```python
# 一時的な回避策: audio_vaeモジュールが見つからない場合の代替
try:
    from comfy.ldm.lightricks.vae.audio_vae import LATENT_DOWNSAMPLE_FACTOR
except ImportError:
    # audio_vaeモジュールが見つからない場合のデフォルト値
    # 通常、LTX-2のオーディオVAEのダウンサンプルファクターは8
    LATENT_DOWNSAMPLE_FACTOR = 8
```

## 次のステップ

1. ComfyUIを再起動
2. ノードが正しく読み込まれたか確認: `python check_comfyui_nodes.py`
3. 動画生成を再度試行: `python generate_mana_mufufu_ltx2_video.py`

## 注意

この修正は一時的な回避策です。ComfyUI-LTXVideoの公式アップデートで修正される可能性があります。
