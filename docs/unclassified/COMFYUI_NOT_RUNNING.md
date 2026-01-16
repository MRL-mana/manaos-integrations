# ⚠️ ComfyUIサーバーが起動していません

**現在の状態**: ComfyUIサーバー（ポート8188）が起動していません。

---

## 🚀 ComfyUIサーバーを起動する方法

### 方法1: 起動スクリプトを使用（推奨）

```powershell
.\start_comfyui_local.ps1
```

### 方法2: 手動で起動

```powershell
# ComfyUIディレクトリに移動（実際のパスに変更してください）
cd C:\path\to\ComfyUI

# ComfyUIサーバーを起動
python main.py --port 8188
```

---

## ✅ 起動確認

ComfyUIが起動したら、以下で確認できます：

```powershell
# システム統計を取得
curl http://localhost:8188/system_stats

# またはブラウザで
# http://localhost:8188
```

---

## 📝 注意事項

- ComfyUIサーバーはGPUが必要な場合があります
- 起動には数分かかる場合があります
- ポート8188が既に使用されている場合は、別のポートを指定してください

---

ComfyUIサーバーを起動したら、再度画像生成をリクエストしてください。
