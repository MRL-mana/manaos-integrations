# ComfyUI統合セットアップガイド

## 🎯 目標

ComfyUIサーバーを起動して、ManaOS統合APIサーバーから画像生成できるようにする。

---

## 📋 前提条件

- ComfyUIがインストールされている（このはサーバー側）
- ポート8188が利用可能
- Python環境が整備されている

---

## 🚀 起動方法

### このはサーバー側で起動する場合

```bash
# ComfyUIディレクトリに移動
cd /root/ComfyUI

# ComfyUIサーバーを起動（ポート8188）
python main.py --port 8188

# バックグラウンドで起動する場合
nohup python main.py --port 8188 > /root/logs/comfyui.log 2>&1 &
```

### ローカル（新PC）で起動する場合

```powershell
# ComfyUIディレクトリに移動
cd C:\path\to\ComfyUI

# ComfyUIサーバーを起動
python main.py --port 8188
```

---

## ✅ 動作確認

### 1. ComfyUIサーバーの起動確認

```bash
# このはサーバー側
curl http://127.0.0.1:8188/system_stats

# またはブラウザで
http://127.0.0.1:8188
# または外部から
http://163.44.120.49:8188
```

### 2. 統合APIサーバーからの確認

```powershell
# 統合APIサーバーを起動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python unified_api_server.py

# 別のターミナルでテスト
python test_comfyui_civitai.py
```

### 3. APIエンドポイントでの確認

```powershell
# ComfyUI画像生成テスト
$body = @{
    prompt = "a beautiful landscape, mountains, sunset, highly detailed"
    width = 512
    height = 512
    steps = 20
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:9510/api/comfyui/generate" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

---

## 🔧 トラブルシューティング

### ComfyUIが起動しない場合

1. **ポート8188が使用中**
   ```bash
   # ポート確認
   netstat -tlnp | grep 8188
   # または
   lsof -i :8188
   ```

2. **依存関係が不足**
   ```bash
   cd /root/ComfyUI
   pip install -r requirements.txt
   ```

3. **モデルファイルが不足**
   - ComfyUIのモデルディレクトリに必要なモデルを配置

### 統合APIサーバーから接続できない場合

1. **環境変数の確認**
   ```powershell
   # .envファイルまたは環境変数で確認
   $env:COMFYUI_URL
   # または
   Get-Content .env | Select-String COMFYUI
   ```

2. **ネットワーク接続の確認**
   ```powershell
   # このはサーバー側の場合
   Test-NetConnection -ComputerName 163.44.120.49 -Port 8188
   ```

---

## 📝 次のステップ

ComfyUIが起動したら：

1. ✅ 統合APIサーバーで動作確認
2. ✅ 画像生成テスト
3. ✅ CivitAIと連携してモデル検索・ダウンロード
4. ✅ Google Driveに自動保存（設定済みの場合）

---

## 🔗 関連ファイル

- `comfyui_integration.py` - ComfyUI統合モジュール
- `unified_api_server.py` - 統合APIサーバー
- `test_comfyui_civitai.py` - テストスクリプト



















