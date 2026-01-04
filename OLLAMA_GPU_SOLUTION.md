# Ollama GPU使用問題の解決策

## 現状

**問題**: OllamaがWindows環境でGPUを使用していない（CPUモードで実行中）

**確認済み**:
- ✅ GPUは正常に認識されている（RTX 5080）
- ✅ PyTorchはCUDAを認識している（CUDA 12.8）
- ✅ 環境変数は設定済み（ユーザー環境変数）
- ❌ `ollama ps`で`PROCESSOR: 100% CPU`と表示される

## 原因

Windows版のOllama（0.13.5）は、GPUサポートが制限されている可能性があります。環境変数を設定しても、Windows環境ではGPUが使用されない場合があります。

## 解決策

### 方法1: システム環境変数の設定（管理者権限が必要）

1. PowerShellを**管理者として実行**
2. 以下のコマンドを実行：

```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_GPU", "1", "Machine")
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU_LAYERS", "99", "Machine")
[System.Environment]::SetEnvironmentVariable("OLLAMA_USE_CUDA", "1", "Machine")
[System.Environment]::SetEnvironmentVariable("OLLAMA_CUDA", "1", "Machine")
[System.Environment]::SetEnvironmentVariable("CUDA_VISIBLE_DEVICES", "0", "Machine")
```

3. システムを再起動
4. Ollamaを再起動

### 方法2: WSL2経由で実行（推奨）

Windows環境でGPUを使用する場合、WSL2経由でOllamaを実行する方が確実です。

1. WSL2をインストール
2. WSL2内でCUDAを設定
3. WSL2内でOllamaをインストール・実行

### 方法3: Docker経由で実行

Docker Desktop for WindowsでGPUサポートを有効にして、Ollamaを実行します。

### 方法4: CPUモードで使用を継続

GPUが使用できない場合でも、CPUモードで動作します（パフォーマンスは低下しますが動作します）。

## 推奨される次のステップ

1. **まず方法1を試す**: システム環境変数を設定して再起動
2. **それでも解決しない場合**: WSL2またはDocker経由での実行を検討
3. **緊急の場合**: CPUモードで使用を継続

## 参考情報

- Ollama公式ドキュメント: https://ollama.ai/
- Windows環境でのGPUサポート: 公式フォーラムで確認推奨

