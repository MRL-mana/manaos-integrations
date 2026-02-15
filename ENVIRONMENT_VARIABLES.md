# 環境変数設定ガイド

ManaOS Integrations は、ポートやサービス URL を環境変数で柔軟に設定できます。このドキュメントでは、利用可能な環境変数とその使用方法を説明します。

---

## 📌 概要

- **デフォルト**: すべてのサービスは `localhost` (127.0.0.1) の標準ポートで動作
- **上書き**: 環境変数を設定することで、異なるホストやポートを使用可能
- **分散環境**: Tailscale 等を使用した分散デプロイメントに対応

---

## 🔧 環境変数一覧

### コアサービス

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `MRL_MEMORY_URL` | `http://127.0.0.1:5105` | MRL Memory API |
| `LEARNING_SYSTEM_URL` | `http://127.0.0.1:5126` | Learning System API |
| `LLM_ROUTING_URL` | `http://127.0.0.1:5111` | LLM Routing API |
| `MANAOS_INTEGRATION_API_URL` | `http://127.0.0.1:9502` | Unified API |

### LLM / 推論エンジン

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama ローカル LLM |
| `LM_STUDIO_URL` | `http://127.0.0.1:1234` | LM Studio API |

### 外部統合サービス

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `N8N_URL` | `http://127.0.0.1:5678` | n8n ワークフロー自動化 |
| `SEARXNG_URL` | `http://127.0.0.1:8080` | SearXNG 検索エンジン |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI 画像生成 |
| `OPENWEBUI_URL` | `http://127.0.0.1:3000` | Open WebUI |

### デバイス健康モニタリング

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `MANAOS_HEALTH_URL` | `http://127.0.0.1:5106/health` | ManaOS デバイス |
| `X280_HEALTH_URL` | `http://100.127.121.20:5120/health` | X280 ThinkPad (Tailscale) |
| `KONOHA_HEALTH_URL` | `http://100.93.120.33:5106/health` | Konoha サーバー (Tailscale) |
| `PIXEL7_HEALTH_URL` | `http://127.0.0.1:5122/health` | Pixel 7 デバイス |

### その他サービス

| 環境変数 | デフォルト | 説明 |
|----------|-----------|------|
| `WHISPER_API_URL` | `http://127.0.0.1:5001` | Whisper 音声認識 API |
| `TTS_API_URL` | `http://127.0.0.1:5000` | TTS 音声合成 API |
| `REMI_API_URL` | `http://127.0.0.1:9407` | Remi Brain MVP API |
| `NGROK_URL` | `http://127.0.0.1:4040` | ngrok トンネル管理 |
| `RAG_MEMORY_URL` | `http://127.0.0.1:5104` | RAG Memory API |

---

## 💻 設定方法

### Windows PowerShell

**一時的な設定（現在のセッションのみ）:**
```powershell
$env:OLLAMA_URL = "http://192.168.1.100:11434"
$env:MRL_MEMORY_URL = "http://100.93.120.33:5105"
```

**永続的な設定（ユーザー環境変数）:**
```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_URL", "http://192.168.1.100:11434", "User")
```

**永続的な設定（システム環境変数、管理者権限必要）:**
```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_URL", "http://192.168.1.100:11434", "Machine")
```

### Linux / macOS

**一時的な設定:**
```bash
export OLLAMA_URL="http://192.168.1.100:11434"
export MRL_MEMORY_URL="http://100.93.120.33:5105"
```

**永続的な設定（`.bashrc` または `.zshrc` に追加）:**
```bash
echo 'export OLLAMA_URL="http://192.168.1.100:11434"' >> ~/.bashrc
source ~/.bashrc
```

### Python スクリプト内

```python
import os

# 環境変数の設定
os.environ["OLLAMA_URL"] = "http://192.168.1.100:11434"

# または、直接アクセス
ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
```

---

## 🌐 分散デプロイメント例

### Tailscale を使用した分散環境

```powershell
# 母艦 (Mothership) - MRL Memory を konoha サーバーから取得
$env:MRL_MEMORY_URL = "http://100.93.120.33:5105"

# X280 - Ollama を母艦から使用
$env:OLLAMA_URL = "http://100.127.121.20:11434"

# Pixel 7 - LLM Routing を母艦経由
$env:LLM_ROUTING_URL = "http://100.127.121.20:5111"
```

### Docker コンテナ

```bash
docker run -e OLLAMA_URL=http://host.docker.internal:11434 \
           -e MRL_MEMORY_URL=http://host.docker.internal:5105 \
           your-image
```

---

## 🧪 動作確認

環境変数が正しく設定されているか確認:

```powershell
# PowerShell
Write-Host "OLLAMA_URL: $env:OLLAMA_URL"
Write-Host "MRL_MEMORY_URL: $env:MRL_MEMORY_URL"
```

```bash
# Bash
echo "OLLAMA_URL: $OLLAMA_URL"
echo "MRL_MEMORY_URL: $MRL_MEMORY_URL"
```

```python
# Python
import os
print("OLLAMA_URL:", os.getenv("OLLAMA_URL"))
print("MRL_MEMORY_URL:", os.getenv("MRL_MEMORY_URL"))
```

---

## ⚙️ PowerShell スクリプトでの使用

多くの PowerShell スクリプトは、環境変数を自動的に使用します:

```powershell
# check_llm_setup.ps1 の例
# 自動的に $env:OLLAMA_URL を使用し、未設定の場合はデフォルト値を使用
.\check_llm_setup.ps1

# import_n8n_workflows.ps1 の例
# -N8nUrl パラメータを省略すると $env:N8N_URL を使用
.\import_n8n_workflows.ps1 -Category all
```

---

## 📚 参考資料

- [README.md](README.md) - メインドキュメント
- [_paths.py](manaos_integrations/_paths.py) - ポート定数の定義
- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - サービス起動ガイド
- [QUICKREF.md](QUICKREF.md) - クイックリファレンス

---

## 🔍 トラブルシューティング

### 環境変数が反映されない

1. **PowerShell を再起動**:新しい環境変数は、新しいセッションで有効になります
2. **VSCode / Cursor を再起動**: IDE を再起動して環境変数を再読み込み
3. **確認**: `$env:変数名` (PowerShell) または `echo $変数名` (Bash) で確認

### サービスに接続できない

1. **URL の形式を確認**: `http://` プロトコルを含める必要があります
2. **ポートが開いているか確認**: `netstat -ano | findstr :ポート番号`
3. **ファイアウォールを確認**: Tailscale 経由の場合、ファイアウォール設定を確認

### デフォルト値に戻したい

環境変数を削除します:

```powershell
# PowerShell（一時的）
Remove-Item Env:\OLLAMA_URL

# PowerShell（永続的）
[System.Environment]::SetEnvironmentVariable("OLLAMA_URL", $null, "User")
```

---

**Last Updated**: 2026-02-15  
**Version**: v2.6.0
