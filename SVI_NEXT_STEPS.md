# SVI × Wan 2.2 次のステップ

## ✅ 現在の状態

- ✅ ComfyUI: 起動中（http://localhost:8188）
- ✅ モデルライブラリ: 表示確認済み
- ✅ カスタムノード: インストール済み
  - ComfyUI-Manager
  - ComfyUI-VideoHelperSuite
  - ComfyUI-AnimateDiff-Evolved

---

## 📋 次のステップ

### 1. Wan 2.2モデルの確認・ダウンロード

モデルライブラリで `checkpoints` フォルダを確認してください。

**Wan 2.2モデルが必要な場合:**
- モデル名: `wan2.2.safetensors` または類似の名前
- ダウンロード先:
  - Hugging Face: https://huggingface.co/models
  - CivitAI: https://civitai.com
- 配置先: `C:\ComfyUI\models\checkpoints\`

### 2. SVIワークフローの確認

ComfyUIで以下のノードが利用可能か確認してください：

- **SVI関連ノード**: Stable Video Diffusion関連のノード
- **動画処理ノード**: VideoHelperSuiteのノード
- **AnimateDiffノード**: AnimateDiff-Evolvedのノード

### 3. ワークフローの読み込み

1. ComfyUIのメイン画面に戻る（左上のアイコンをクリック）
2. ワークフローファイルを読み込む（必要に応じて）
3. または、新規ワークフローを作成

### 4. 動作確認

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python test_svi_wan22.py
```

---

## 🎯 使用可能な機能

### Pythonから直接使用

```python
from svi_wan22_video_integration import SVIWan22VideoIntegration

svi = SVIWan22VideoIntegration()
prompt_id = svi.generate_video(
    start_image_path="path/to/image.png",
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

## 📚 参考資料

- [SVI × Wan 2.2 統合ガイド](SVI_WAN22_INTEGRATION_GUIDE.md)
- [技術詳細まとめ](../../Reports/SVI_Wan22_AI動画生成技術_完全まとめ.md)
- [セットアップ完了ガイド](SVI_WAN22_SETUP_COMPLETE.md)

---

*更新日時: 2025-01-28*











