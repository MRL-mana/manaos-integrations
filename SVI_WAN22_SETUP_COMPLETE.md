# SVI × Wan 2.2 セットアップ完了ガイド

## ✅ セットアップ状況

### 完了した項目

1. ✅ **ComfyUI**: インストール済み（C:\ComfyUI）
2. ✅ **ComfyUI Manager**: インストール済み
3. ✅ **SVI動画生成統合モジュール**: 実装完了
4. ✅ **統合APIエンドポイント**: 追加完了
5. ✅ **ManaOSコアAPI統合**: 完了

### 残りの作業

1. ⚠️ **カスタムノードのインストール**: ComfyUI起動後に手動でインストール
2. ⚠️ **Wan 2.2モデルのダウンロード**: 必要に応じてダウンロード
3. ⚠️ **動作確認**: テストスクリプトの実行

---

## 📋 次のステップ

### ステップ1: ComfyUIを起動

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_comfyui_local.ps1
```

または手動で:

```powershell
cd C:\ComfyUI
python main.py --port 8188
```

### ステップ2: ComfyUI Managerでカスタムノードをインストール

1. ブラウザで `http://localhost:8188` にアクセス
2. 「Manager」ボタンをクリック
3. 「Install Missing Custom Nodes」を実行

または、以下のカスタムノードを個別にインストール:

- **ComfyUI-VideoHelperSuite**: 動画処理用
  - URL: `https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite`
  
- **ComfyUI-AnimateDiff-Evolved**: 動画生成用
  - URL: `https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved`
  
- **ComfyUI-Stable-Video-Diffusion**: SVI統合用
  - URL: `https://github.com/Stability-AI/ComfyUI-Stable-Video-Diffusion`

### ステップ3: Wan 2.2モデルのダウンロード（オプション）

モデルファイルを以下のパスに配置:

```
C:\ComfyUI\models\checkpoints\wan2.2.safetensors
```

ダウンロード先:
- Hugging Face: https://huggingface.co/models
- CivitAI: https://civitai.com

### ステップ4: 動作確認

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python test_svi_integration.py
```

---

## 🚀 使用方法

### Pythonから直接使用

```python
from svi_wan22_video_integration import SVIWan22VideoIntegration

svi = SVIWan22VideoIntegration()
prompt_id = svi.generate_video(
    start_image_path="image.png",
    prompt="a beautiful landscape",
    video_length_seconds=5,
    steps=6,
    motion_strength=1.3
)
```

### REST API経由

```bash
curl -X POST http://localhost:9500/api/svi/generate \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_path": "image.png",
    "prompt": "landscape",
    "video_length_seconds": 5
  }'
```

### ManaOSコアAPI経由

```python
from manaos_integrations.manaos_core_api import act

result = act("generate_video", {
    "start_image_path": "image.png",
    "prompt": "landscape",
    "video_length_seconds": 5
})
```

---

## 📚 関連ドキュメント

- [SVI × Wan 2.2 統合ガイド](SVI_WAN22_INTEGRATION_GUIDE.md)
- [技術詳細まとめ](../../Reports/SVI_Wan22_AI動画生成技術_完全まとめ.md)
- [ComfyUIセットアップガイド](COMFYUI_SETUP.md)

---

*最終更新: 2025-01-28*


