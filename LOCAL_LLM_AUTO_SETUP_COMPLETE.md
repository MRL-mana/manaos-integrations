# ローカルLLM GPUモード自動起動設定完了

## ✅ 設定完了

Windows起動時に自動でGPUモードでOllamaが起動するように設定しました。

## 🚀 自動化の内容

### 1. 自動起動設定
- **タスク名**: `ManaOS_Ollama_GPU_WSL2`
- **起動タイミング**: Windows起動時（30秒遅延でWSL2の準備を待つ）
- **自動再起動**: 失敗時は最大3回再試行
- **バッテリー時も起動**: バッテリー駆動時も継続

### 2. 自動検出機能
- `local_llm_helper.py`が自動的にWSL2経由のOllamaを使用
- Windows版とWSL2版を自動判定

### 3. GPUモード自動起動
- WSL2経由でGPUモードで起動
- 環境変数を自動設定

---

## 📋 確認方法

### タスクスケジューラで確認

```powershell
Get-ScheduledTask -TaskName "ManaOS_Ollama_GPU_WSL2"
```

### 手動で確認

1. Windowsキーを押して「タスクスケジューラ」と入力
2. 「タスクスケジューラ」を開く
3. 「タスク スケジューラ ライブラリ」を開く
4. `ManaOS_Ollama_GPU_WSL2`を探す

---

## 🎯 使い方

### Pythonから使用（自動）

```python
from local_llm_helper import ask

# 自動的にWSL2経由でGPUモードで実行されます
answer = ask("質問内容", model="qwen3:4b")
print(answer)
```

### 手動起動（必要に応じて）

```powershell
.\start_ollama_gpu.ps1
```

### 停止（必要に応じて）

```powershell
wsl -d Ubuntu-22.04 -- pkill ollama
```

---

## 🔧 設定の変更

### 自動起動を無効化

```powershell
Unregister-ScheduledTask -TaskName "ManaOS_Ollama_GPU_WSL2" -Confirm:$false
```

### 自動起動を再有効化

```powershell
.\setup_ollama_gpu_autostart.ps1
```

---

## 📊 動作確認

### 1. PC再起動後

```powershell
# Ollamaの状態確認
wsl -d Ubuntu-22.04 -- ollama ps

# GPU使用状況確認
wsl -d Ubuntu-22.04 -- nvidia-smi
```

### 2. Pythonから確認

```python
from local_llm_helper import check_status

status = check_status()
print(f"WSL2 Running: {status['wsl2_running']}")
print(f"GPU Mode: {status['gpu_mode']}")
```

---

## 💡 注意事項

1. **初回起動**: モデルのダウンロードに時間がかかることがあります
2. **WSL2の準備**: 起動後30秒遅延でOllamaが起動します（WSL2の準備を待つため）
3. **GPU使用**: WSL2経由でGPUが使用されます

---

## 🎉 完了

**これで全部自動です！**

- ✅ Windows起動時に自動でGPUモードでOllama起動
- ✅ Pythonから自動的に使用可能
- ✅ 失敗時は自動再起動

次回のWindows起動時から自動で動作します。

