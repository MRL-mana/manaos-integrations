# ComfyUI再起動手順（必須）

## 現在の状況
- エンコーディングエラーが大量に発生しています
- ComfyUI-Managerは既に無効化されています
- ComfyUIを再起動する必要があります

## 再起動手順

### 方法1: バッチファイルを使用（推奨）

1. **現在のComfyUIを停止**
   - ComfyUIが実行されているコマンドプロンプト/ターミナルで `Ctrl+C` を押す

2. **新しいコマンドプロンプトを開く**

3. **以下のコマンドを実行:**
   ```cmd
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\start_comfyui_simple.bat
   ```

### 方法2: 手動で環境変数を設定

1. **現在のComfyUIを停止**
   - ComfyUIが実行されているコマンドプロンプト/ターミナルで `Ctrl+C` を押す

2. **新しいコマンドプロンプトを開く**

3. **以下のコマンドを順番に実行:**
   ```cmd
   cd C:\ComfyUI
   set PYTHONIOENCODING=utf-8
   set PYTHONLEGACYWINDOWSSTDIO=1
   python main.py
   ```

## 再起動後の確認

ComfyUIが起動したら、以下のコマンドで生成状況を確認してください:

```cmd
cd C:\Users\mana4\Desktop\manaos_integrations
python check_generation_status.py
python final_status_check.py
```

## 注意事項

- ComfyUI-Managerは既に無効化されているため、再起動後も無効化されたままです
- 環境変数（`PYTHONIOENCODING`と`PYTHONLEGACYWINDOWSSTDIO`）を設定してから起動することが重要です
- 再起動後、エンコーディングエラーが解消されれば、画像生成が正常に動作するはずです
