# ComfyUI再起動と画像生成手順

## 現在の状況
- ComfyUI-Managerは無効化済み
- ComfyUIのエンコーディングエラーが発生中
- **ComfyUIの再起動が必要です**

## 手順

### 1. ComfyUIを再起動

現在のComfyUIを停止（Ctrl+C）して、以下のコマンドで再起動：

```powershell
powershell -ExecutionPolicy Bypass -File start_comfyui_fixed.ps1
```

または、手動で：

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "1"
cd C:\ComfyUI
python main.py
```

### 2. 再起動後、自動で画像生成を実行

ComfyUIが起動したら、以下のコマンドを実行：

```bash
python auto_generate_after_restart.py
```

このスクリプトは：
- ComfyUIの接続を自動確認
- 10枚の画像生成を自動実行
- ムフフモードで清楚系ギャル画像を生成

### 3. 生成状況の確認

```bash
python check_generation_status.py
```

または、ブラウザで：
- `http://localhost:5559/api/images` - 生成された画像一覧

## 注意事項

- ComfyUI-Managerは無効化されています（エンコーディングエラー回避のため）
- 再起動後は正常に画像生成できるはずです
- 生成には時間がかかります（1枚あたり数分）
