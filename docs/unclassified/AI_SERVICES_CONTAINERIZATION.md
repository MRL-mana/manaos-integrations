# AIサービス（ローカルLLM・画像生成AI）コンテナ化ガイド

**作成日**: 2025-01-28  
**状態**: ✅ 実装完了

---

## 📦 コンテナ化状況

### ✅ コンテナ化済み

1. **Ollama**（ローカルLLM）
   - ポート: 11434
   - イメージ: `ollama/ollama:latest`
   - GPU対応: ✅
   - 状態: ✅ 既にコンテナ化済み（`docker-compose.always-ready-llm.yml`）

2. **ComfyUI**（画像生成AI）
   - ポート: 8188
   - カスタムDockerfile: `comfyui/Dockerfile`
   - GPU対応: ✅
   - 状態: ✅ 新規追加

3. **Stable Diffusion WebUI**（画像生成AI、オプション）
   - ポート: 7860
   - カスタムDockerfile: `sd-webui/Dockerfile`
   - GPU対応: ✅
   - 状態: ✅ 新規追加（プロファイル指定で起動）

4. **LM Studio Server**（ローカルLLM、オプション）
   - ポート: 1234
   - 状態: ⚠️ ホストで起動が必要（APIプロキシとしてコンテナ化）
   - 注意: LM StudioはWindowsアプリなので、ホストで起動しAPIサーバーモードで使用

5. **Free-personal-AI-Assistant**（ローカルLLM、オプション）
   - ポート: 8501
   - カスタムDockerfile: `free-assistant/Dockerfile`
   - 状態: ✅ 新規追加（プロファイル指定で起動）

6. **Sara-AI-Platform**（ローカルLLM、オプション）
   - ポート: 8000
   - カスタムDockerfile: `sara-ai/Dockerfile`
   - 状態: ✅ 新規追加（プロファイル指定で起動）

---

## 🚀 セットアップ方法

### 1. すべてのAIサービスを起動

```bash
# ComfyUIとOllamaを起動
docker-compose -f docker-compose.ai-services.yml up -d

# Stable Diffusion WebUIも含めて起動
docker-compose -f docker-compose.ai-services.yml --profile sd-webui up -d
```

### 2. 個別に起動

```bash
# Ollamaのみ
docker-compose -f docker-compose.ai-services.yml up -d ollama

# ComfyUIのみ
docker-compose -f docker-compose.ai-services.yml up -d comfyui

# Stable Diffusion WebUIのみ
docker-compose -f docker-compose.ai-services.yml --profile sd-webui up -d sd-webui

# LM Studio APIプロキシ（LM Studioはホストで起動が必要）
docker-compose -f docker-compose.ai-services.yml --profile lm-studio up -d lm-studio-api

# Free Assistantのみ
docker-compose -f docker-compose.ai-services.yml --profile local-llm up -d free-assistant

# Sara AIのみ
docker-compose -f docker-compose.ai-services.yml --profile local-llm up -d sara-ai

# すべてのローカルLLMを起動
docker-compose -f docker-compose.ai-services.yml --profile local-llm --profile lm-studio up -d
```

### 3. ログ確認

```bash
# すべてのログ
docker-compose -f docker-compose.ai-services.yml logs -f

# 個別のログ
docker-compose -f docker-compose.ai-services.yml logs -f ollama
docker-compose -f docker-compose.ai-services.yml logs -f comfyui
docker-compose -f docker-compose.ai-services.yml logs -f sd-webui
```

### 4. 停止

```bash
# すべて停止
docker-compose -f docker-compose.ai-services.yml down

# 個別停止
docker-compose -f docker-compose.ai-services.yml stop ollama
docker-compose -f docker-compose.ai-services.yml stop comfyui
```

---

## 📋 サービス詳細

### Ollama（ローカルLLM）

**特徴:**
- 軽量で高速なローカルLLM
- 複数のモデルを管理可能
- GPU/CPU両対応

**モデル管理:**
```bash
# モデル一覧
docker exec ollama-always-ready ollama list

# モデルをプル
docker exec ollama-always-ready ollama pull llama3.2:3b

# モデルを削除
docker exec ollama-always-ready ollama rm llama3.2:3b
```

**API使用例:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

### ComfyUI（画像生成AI）

**特徴:**
- ノードベースの画像生成UI
- 高度なワークフロー作成が可能
- カスタムノード対応

**モデル配置:**
```
comfyui/
├── models/
│   ├── checkpoints/     # メインモデル（.safetensors）
│   ├── vae/             # VAEモデル
│   ├── loras/           # LoRAモデル
│   ├── upscale_models/  # アップスケールモデル
│   └── controlnet/      # ControlNetモデル
├── output/              # 生成画像の出力先
├── input/               # 入力画像
└── custom_nodes/        # カスタムノード
```

**アクセス:**
- Web UI: http://localhost:8188
- API: http://localhost:8188

**API使用例:**
```bash
curl http://localhost:8188/system_stats
```

### Stable Diffusion WebUI（画像生成AI、オプション）

**特徴:**
- シンプルなWeb UI
- 拡張機能対応
- プロンプト生成支援

**モデル配置:**
```
sd-webui/
├── models/
│   ├── Stable-diffusion/  # メインモデル
│   ├── VAE/               # VAEモデル
│   ├── Lora/              # LoRAモデル
│   └── ControlNet/        # ControlNetモデル
├── outputs/               # 生成画像の出力先
└── extensions/            # 拡張機能
```

**アクセス:**
- Web UI: http://localhost:7860

**注意:** ComfyUIと同時に起動する場合はGPUメモリに注意してください。

### LM Studio Server（ローカルLLM）

**特徴:**
- Windowsアプリケーション（ホストで起動が必要）
- OpenAI互換APIサーバー
- 複数のモデルを管理可能

**セットアップ:**
1. LM Studioをホストで起動
2. APIサーバーモードを有効化（ポート1234）
3. Dockerコンテナから `http://host.docker.internal:1234/v1` でアクセス

**アクセス:**
- API: http://localhost:1234/v1
- OpenAI互換エンドポイント: http://localhost:1234/v1/chat/completions

**注意:** LM StudioはWindowsアプリなので、コンテナ化はできません。ホストで起動し、APIサーバーとして使用します。

### Free-personal-AI-Assistant（ローカルLLM）

**特徴:**
- プラグイン対応チャットボット
- Web検索、PDF、YouTube統合
- シンプルなUI

**アクセス:**
- Web UI: http://localhost:8501
- API: http://localhost:8501/api

### Sara-AI-Platform（ローカルLLM）

**特徴:**
- メモリ機能
- ペルソナ機能
- TTS対応
- マルチモデルルーティング

**アクセス:**
- API: http://localhost:8000
- Web UI: http://localhost:8000/docs（FastAPI自動生成）

---

## 🔧 環境変数

### Ollama

```bash
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_KEEP_ALIVE=5m
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_NUM_PARALLEL=4
```

### ComfyUI

```bash
PYTHONUNBUFFERED=1
TZ=Asia/Tokyo
```

### Stable Diffusion WebUI

```bash
PYTHONUNBUFFERED=1
TZ=Asia/Tokyo
CLI_ARGS=--listen --port 7860
```

---

## 🐳 GPU設定

### NVIDIA GPUが必要

```bash
# NVIDIA Container Toolkitのインストール（Linux）
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# GPU確認
nvidia-smi

# DockerでGPU使用確認
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

### CPUモード（GPUがない場合）

ComfyUIをCPUモードで起動する場合：

```yaml
# docker-compose.ai-services.yml のcomfyuiサービスに追加
command: ["python", "main.py", "--port", "8188", "--cpu"]
```

---

## 📝 モデルの追加方法

### ComfyUIにモデルを追加

```bash
# ホストからモデルをコピー
docker cp your_model.safetensors comfyui-server:/app/models/checkpoints/

# または、ボリュームマウントを使用
# docker-compose.ai-services.ymlで既にマウント済み:
# ./comfyui/models:/app/models
```

### Stable Diffusion WebUIにモデルを追加

```bash
# ホストからモデルをコピー
docker cp your_model.safetensors sd-webui-server:/app/models/Stable-diffusion/

# または、ボリュームマウントを使用
# docker-compose.ai-services.ymlで既にマウント済み:
# ./sd-webui/models:/app/models
```

---

## 🔍 トラブルシューティング

### GPUが認識されない

1. NVIDIA Container Toolkitがインストールされているか確認：
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
   ```

2. docker-compose.ymlでGPU設定を確認：
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities:
               - gpu
   ```

### ComfyUIが起動しない

1. ログを確認：
   ```bash
   docker-compose -f docker-compose.ai-services.yml logs comfyui
   ```

2. ポート8188が使用中でないか確認：
   ```bash
   netstat -an | grep 8188
   ```

3. モデルディレクトリの権限を確認：
   ```bash
   ls -la comfyui/models/
   ```

### メモリ不足エラー

1. GPUメモリを確認：
   ```bash
   nvidia-smi
   ```

2. 同時起動するサービスを減らす：
   - ComfyUIとStable Diffusion WebUIは同時に起動しない
   - プロファイルを使用して切り替え

---

## 📚 参考資料

- [Ollama Documentation](https://ollama.ai/docs)
- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [Stable Diffusion WebUI GitHub](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)

---

## ✅ 完了チェックリスト

- [x] Ollamaコンテナ化（既存）
- [x] ComfyUI Dockerfile作成
- [x] Stable Diffusion WebUI Dockerfile作成
- [x] LM Studio APIプロキシ設定
- [x] Free-personal-AI-Assistant Dockerfile作成
- [x] Sara-AI-Platform Dockerfile作成
- [x] docker-compose.ai-services.yml作成（全サービス統合）
- [x] セットアップガイド作成

---

## 🎉 次のステップ

1. **テスト**: 各サービスを起動して動作確認
2. **モデル追加**: 必要なモデルを追加
3. **統合**: Unified API Serverとの統合確認
4. **最適化**: GPUメモリ使用量の最適化
