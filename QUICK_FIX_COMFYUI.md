# ComfyUIエラー修正手順

## 現在の問題
ComfyUI-Managerのエンコーディングエラーで画像生成が失敗しています。

## 修正手順

### 1. ComfyUI-Managerを無効化
```bash
python disable_comfyui_manager.py
```

### 2. ComfyUIを再起動
ComfyUIを停止して、以下のコマンドで再起動：

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "1"
cd C:\ComfyUI
python main.py
```

または、`start_comfyui_fixed.ps1` を実行

### 3. 画像生成を再実行
```bash
python generate_10_mufufu_clear_gyaru.py
```

## 確認
```bash
python restart_and_generate.py
```

正常に画像が生成されれば修正完了です。
