# LTX-2 ノード確認結果

## エラー

`LTXVGemmaCLIPModelLoader`ノードが存在しない

## 確認されたノード

ComfyUIで確認されたLTX-2関連ノード:
- `EmptyLTXVLatentVideo`
- `LTXVAddGuide`
- `LTXVConditioning`
- `LTXVCropGuides`
- `LTXVImgToVideo`
- `LTXVPreprocess`
- `LTXVScheduler`
- `ModelMergeLTXV`
- `ModelSamplingLTXV`

## 問題

`LTXVGemmaCLIPModelLoader`ノードが見つかりません。

## 考えられる原因

1. ComfyUI-LTXVideoが正しくインストールされていない
2. ComfyUIを再起動していない（カスタムノードが読み込まれていない）
3. ComfyUI-LTXVideoのバージョンが古い
4. 必要な依存関係がインストールされていない

## 解決方法

1. ComfyUIを再起動する
2. ComfyUI-LTXVideoが正しくインストールされているか確認
3. ComfyUI Managerから不足しているノードをインストール
4. 実際のワークフローファイルを使用してノード名を確認
