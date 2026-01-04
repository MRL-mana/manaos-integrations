# Ollama GPU使用状況レポート

## 現在の状況

**日時**: 2026年1月3日

### GPU状態
- ✅ GPU認識: NVIDIA GeForce RTX 5080
- ✅ CUDA認識: PyTorchがCUDA 12.8を認識
- ✅ GPU使用可能: 他のアプリケーション（Stable Diffusion等）はGPUを使用可能
- ❌ Ollama GPU使用: **CPUモードで実行中**

### 環境変数設定
以下の環境変数が設定済み：
- `OLLAMA_NUM_GPU = 1`
- `OLLAMA_GPU_LAYERS = 99`
- `OLLAMA_USE_CUDA = 1`
- `OLLAMA_CUDA = 1`
- `CUDA_VISIBLE_DEVICES = 0`

### Ollamaバージョン
- バージョン: 0.13.5
- インストールパス: `C:\Users\mana4\AppData\Local\Programs\Ollama\ollama.exe`

### 問題
`ollama ps`の結果で`PROCESSOR: 100% CPU`と表示され、GPUが使用されていません。

## 試した解決策

1. ✅ 環境変数の設定（`OLLAMA_NUM_GPU`, `OLLAMA_GPU_LAYERS`, `OLLAMA_USE_CUDA`, `OLLAMA_CUDA`）
2. ✅ Ollamaの完全停止と再起動
3. ✅ API経由で`num_gpu=99`を指定
4. ✅ ユーザー環境変数として永続化

## 考えられる原因

1. **Windows版OllamaのGPUサポート制限**: Windows版のOllamaはGPUサポートが制限されている可能性があります。
2. **Ollamaのバージョン**: 0.13.5が最新かどうか確認が必要です。
3. **CUDAドライバーの互換性**: CUDA 12.8とOllamaの互換性の問題の可能性があります。

## 推奨される解決策

### 1. Ollamaの最新版への更新
```powershell
winget upgrade ollama
# または
ollama update
```

### 2. WSL2経由での実行（推奨）
Windows環境でGPUを使用する場合、WSL2経由でOllamaを実行する方が確実です。

### 3. Docker経由での実行
Docker Desktop for WindowsでGPUサポートを有効にして、Ollamaを実行する方法もあります。

### 4. 代替案
- CPUモードで使用を継続（パフォーマンスは低下しますが動作します）
- 他のLLM実行環境（LM Studio、Oobabooga等）の検討

## 次のステップ

1. Ollamaの最新バージョンを確認・更新
2. WSL2環境でのGPUサポート確認
3. 公式ドキュメントでWindows版のGPUサポート状況を確認
