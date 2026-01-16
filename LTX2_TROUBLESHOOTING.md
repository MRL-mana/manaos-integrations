# LTX-2 トラブルシューティング

## エラー: `LTXVGemmaCLIPModelLoader`ノードが見つからない

### 問題

動画生成を試した際に、以下のエラーが発生しました：
```
Cannot execute because node LTXVGemmaCLIPModelLoader does not exist.
```

### 原因

ComfyUI-LTXVideoのカスタムノードが正しく読み込まれていない可能性があります。

### 確認されたノード

現在ComfyUIに読み込まれているLTX-2関連ノード:
- ✅ `EmptyLTXVLatentVideo`
- ✅ `LTXVAddGuide`
- ✅ `LTXVConditioning`
- ✅ `LTXVCropGuides`
- ✅ `LTXVImgToVideo`
- ✅ `LTXVPreprocess`
- ✅ `LTXVScheduler`
- ✅ `ModelMergeLTXV`
- ✅ `ModelSamplingLTXV`

### 不足しているノード

- ❌ `LTXVGemmaCLIPModelLoader`
- ❌ `LTXVAudioVAELoader`
- ❌ `LTXVEmptyLatentAudio`
- ❌ `LTXVImgToVideoInplace`
- ❌ `LTXVSeparateAVLatent`
- ❌ `LTXVSpatioTemporalTiledVAEDecode`
- ❌ `LTXVAudioVAEDecode`
- ❌ `LTXVLatentUpsampler`

## 解決方法

### 1. ComfyUIを再起動

カスタムノードを読み込むために、ComfyUIを完全に再起動してください。

```powershell
# ComfyUIを停止
# コマンドプロンプトでCtrl+C

# ComfyUIを再起動
cd C:\ComfyUI
python main.py
```

### 2. ComfyUI-LTXVideoのインストール確認

ComfyUI-LTXVideoが正しくインストールされているか確認：

```powershell
cd C:\ComfyUI\custom_nodes
Test-Path ComfyUI-LTXVideo
```

### 3. ComfyUI-LTXVideoの再インストール

もし正しくインストールされていない場合は、再インストール：

```powershell
cd C:\ComfyUI\custom_nodes
Remove-Item -Recurse -Force ComfyUI-LTXVideo
git clone https://github.com/Lightricks/ComfyUI-LTXVideo
```

### 4. 依存関係のインストール

ComfyUI-LTXVideoの依存関係をインストール：

```powershell
cd C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo
pip install -r requirements.txt
```

### 5. ComfyUI Managerを使用

ComfyUI Managerから不足しているノードをインストール：

1. ComfyUIを起動
2. ブラウザで http://localhost:8188 にアクセス
3. 「Manager」→「Install Missing Custom Nodes」を実行

### 6. コンソールログの確認

ComfyUIのコンソールでエラーメッセージを確認：

- ComfyUIを起動したときにエラーが表示されていないか確認
- カスタムノードの読み込みエラーが表示されていないか確認

## 次のステップ

1. ComfyUIを再起動
2. エラーが解消されたか確認
3. 再度動画生成を試行

## 参考資料

- **ComfyUI-LTXVideo**: https://github.com/Lightricks/ComfyUI-LTXVideo
- **LTX-2公式ドキュメント**: https://docs.ltx.video/
