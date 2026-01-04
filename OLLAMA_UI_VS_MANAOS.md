# Ollama UI vs ManaOS統合APIサーバーの違い

## 問題の分析

### 現在の状況

1. **Ollama UI**
   - モデル: `gpt-oss:20b`が選択されている
   - 処理時間: 26秒（長い）
   - GPU使用: CPUモードで実行されている可能性が高い

2. **ManaOS統合APIサーバー**
   - モデル: `qwen2.5:7b`（デフォルト）
   - GPU使用: `num_gpu: 99`を指定するように修正済み
   - 記憶システム: 統合済み

### 違い

| 項目 | Ollama UI | ManaOS統合APIサーバー |
|------|-----------|---------------------|
| **接続方法** | Ollama API直接 | ManaOS統合API経由 |
| **モデル選択** | UIで手動選択 | ルーティング設定に従う |
| **GPU設定** | UIの設定に依存 | `num_gpu: 99`を明示的に指定 |
| **記憶システム** | なし | 統一記憶システムと統合 |
| **人格設定** | なし | 人格設定ファイルから読み込み |
| **会話履歴** | セッション内のみ | Obsidianに永続保存 |

## 問題点

### 1. GPUが使用されていない

**Ollama UIの場合:**
- UIでGPU設定が明示されていない
- デフォルトでCPUモードになる可能性がある

**ManaOS統合APIサーバーの場合:**
- `num_gpu: 99`を指定するように修正済み
- ただし、Ollama自体がCPUモードで起動している場合は効果がない

### 2. 処理時間が長い（26秒）

- CPUモードで実行されているため
- GPUを使用すれば大幅に短縮される可能性がある

### 3. モデルの違い

- **Ollama UI**: `gpt-oss:20b`（20Bパラメータ、大きい）
- **ManaOS統合API**: `qwen2.5:7b`（7Bパラメータ、小さい）

## 解決方法

### 方法1: Ollama UIでGPUを有効化

Ollama UIの設定でGPUを有効化する必要があります。

### 方法2: ManaOS統合APIサーバーを使用

ManaOS統合APIサーバー経由で使用すると：
- GPU使用が明示的に指定される
- 記憶システムと統合される
- 人格設定が適用される
- 会話履歴が永続保存される

### 方法3: OllamaをGPUモードで再起動

```powershell
# 環境変数を設定
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99

# Ollamaを再起動
Stop-Process -Name ollama -Force
Start-Process ollama
```

## 推奨事項

**ManaOS統合APIサーバー経由で使用することを推奨します：**

1. GPU使用が確実に有効化される
2. 記憶システムと統合される
3. 人格設定が適用される
4. 会話履歴が永続保存される

Ollama UIは直接Ollama APIを呼び出すため、ManaOSの機能（記憶、人格設定など）が使えません。



