# ローカルLLM GPUモード設定完了

## ✅ 設定完了

WSL2経由でGPUモードでOllamaを使用できるようになりました。

## 🚀 起動方法

### 1. GPUモードで起動

```powershell
.\start_ollama_gpu.ps1
```

このスクリプトで：
- Windows版Ollamaを停止
- WSL2内でOllamaをGPUモードで起動
- 起動確認とGPU使用状況を表示

### 2. 使用方法

**Pythonから使用：**

```python
from local_llm_helper import ask

# 簡単に質問
answer = ask("質問内容", model="qwen3:4b")
print(answer)
```

**自動的にWSL2経由でGPUモードで実行されます。**

## 📊 GPU使用状況の確認

### Ollamaの状態確認

```powershell
wsl -d Ubuntu-22.04 -- ollama ps
```

`PROCESSOR`列に`GPU`または`GPU+CPU`と表示されれば、GPUが使用されています。

### GPU使用率の確認

```powershell
wsl -d Ubuntu-22.04 -- nvidia-smi
```

または

```powershell
nvidia-smi
```

## 🔧 停止方法

```powershell
wsl -d Ubuntu-22.04 -- pkill ollama
```

## 📝 注意事項

1. **初回起動**: モデルのダウンロードに時間がかかることがあります
2. **自動切り替え**: `local_llm_helper.py`は自動的にWSL2経由のOllamaを使用します
3. **ポート**: WSL2内のOllamaは`localhost:11434`でアクセス可能です

## 🎯 推奨モデル

- **軽量・高速**: `llama3.2:3b`, `qwen3:4b`
- **中型（高品質）**: `qwen2.5:14b`, `llama3.1:8b`
- **大型（最高品質）**: `qwen2.5:32b`, `llama3.1:70b`
- **コード生成**: `deepseek-coder:6.7b`, `qwen2.5-coder:32b`

## 💡 使い方の例

```python
from local_llm_helper import ask, check_status

# 状態確認
status = check_status()
print(f"WSL2 Running: {status['wsl2_running']}")
print(f"GPU Mode: {status['gpu_mode']}")

# 質問
answer = ask("PythonでHello Worldを出力するコードを書いて", model="qwen3:4b")
print(answer)
```

---

**これでGPUモードでローカルLLMを使えます！**

