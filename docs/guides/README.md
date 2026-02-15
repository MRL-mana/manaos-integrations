# ManaOS外部システム統合モジュール

ManaOSと外部システムを統合するためのモジュール集です。

## 📦 インストール

```bash
pip install -r requirements.txt
```

## 🔧 設定

環境変数を設定してください：

```bash
# ComfyUI
export COMFYUI_URL=http://127.0.0.1:8188

# Google Drive
export GOOGLE_DRIVE_CREDENTIALS=credentials.json
export GOOGLE_DRIVE_TOKEN=token.json

# CivitAI
export CIVITAI_API_KEY=your_api_key

# Ollama
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen2.5:7b

# Obsidian
export OBSIDIAN_VAULT_PATH=C:/Users/mana4/Documents/Obsidian Vault

# ManaOS統合APIサーバー
export MANAOS_INTEGRATION_PORT=9500
export MANAOS_INTEGRATION_HOST=127.0.0.1
export MANAOS_DEBUG=false

# 推奨: 3段階キー（Admin / Ops / Read-only）
# export MANAOS_INTEGRATION_API_KEY=...
# export MANAOS_INTEGRATION_OPS_API_KEY=...
# export MANAOS_INTEGRATION_READONLY_API_KEY=...
```

より安全な運用（CORS/IP制御/監査ログ/Confirm Token/Rate limit など）は
`docs/guides/SECURITY_HARDENING.md` を参照してください。

## 🚀 使用方法

### 統合APIサーバーを起動

```bash
python unified_api_server.py
```

**統合API ＋ MoltBot Gateway をまとめて起動**（MCP・秘書ファイル整理用）: リポジトリルートで **`start_unified_api_and_moltbot.bat`** を実行すると 9500 と 8088 が別窓で起動する。

本番運用は Flask 開発サーバではなく Waitress を推奨します：

```bat
start_unified_api_server_prod.bat
```

### 個別の統合モジュールを使用

```python
from comfyui_integration import ComfyUIIntegration
from google_drive_integration import GoogleDriveIntegration
from civitai_integration import CivitAIIntegration
from langchain_integration import LangChainIntegration
from mem0_integration import Mem0Integration
from obsidian_integration import ObsidianIntegration

# ComfyUI統合
comfyui = ComfyUIIntegration()
if comfyui.is_available():
    prompt_id = comfyui.generate_image("a beautiful landscape")

# Google Drive統合
drive = GoogleDriveIntegration()
if drive.is_available():
    file_id = drive.upload_file("path/to/file.txt")

# CivitAI統合
civitai = CivitAIIntegration()
models = civitai.search_models("realistic", limit=10)

# LangChain統合
langchain = LangChainIntegration()
response = langchain.chat("こんにちは！")

# Mem0統合
mem0 = Mem0Integration()
memory_id = mem0.add_memory("これはテストメモリです。")

# Obsidian統合
obsidian = ObsidianIntegration("C:/path/to/vault")
note_path = obsidian.create_note("タイトル", "内容", tags=["タグ1", "タグ2"])
```

## 📡 APIエンドポイント

統合APIサーバーが起動している場合、以下のエンドポイントが利用可能です：

- `GET /health` - ヘルスチェック
- `GET /api/integrations/status` - 統合システム状態
- `POST /api/comfyui/generate` - ComfyUI画像生成
- `POST /api/sd-prompt/generate` - SD用プロンプト生成（日本語→英語、Ollama）
- `POST /api/google_drive/upload` - Google Driveアップロード
- `GET /api/civitai/search` - CivitAIモデル検索
- `POST /api/langchain/chat` - LangChainチャット
- `POST /api/mem0/add` - Mem0メモリ追加
- `POST /api/obsidian/create` - Obsidianノート作成

## 🔍 テスト

### クイックスタート

```bash
python quick_start.py
```

対話型メニューから機能を選択できます。

### 個別テスト

各モジュールにはテスト用のmain関数が含まれています：

```bash
python comfyui_integration.py
python google_drive_integration.py
python civitai_integration.py
python langchain_integration.py
python mem0_integration.py
python obsidian_integration.py
python crewai_integration.py
```

### 統合テスト

すべての統合システムを一度にテスト：

```bash
python test_all_integrations.py
```

### 拡張機能

- **ワークフロー自動化**: `python workflow_automation.py`
- **拡張CivitAIダウンローダー**: `python enhanced_civitai_downloader.py --model-id <ID>`
- **ManaOSサービスブリッジ**: `python manaos_service_bridge.py`

## 📝 注意事項

- Google Drive APIを使用するには、Google Cloud Consoleで認証情報を取得する必要があります
- ComfyUIを使用するには、ComfyUIサーバーが起動している必要があります
- LangChain/LangGraphを使用するには、Ollamaサーバーが起動している必要があります
- Mem0を使用するには、追加の設定が必要な場合があります

## 🎯 統合システム一覧

1. **ComfyUI** - Stable Diffusionワークフローエディタ
2. **Google Drive** - バックアップ自動化
3. **CivitAI** - モデル管理自動化
4. **LangChain/LangGraph** - AIエージェントフレームワーク
5. **Mem0** - メモリ管理システム
6. **Obsidian** - ノート管理自動化

## 📱 デバイス・オーケストレーター

| デバイス | 役割 | オンラインにするには |
|----------|------|----------------------|
| 母艦 | 開発・ComfyUI・実行元 | 常時オンライン扱い |
| ManaOS | 統合オーケストレーター (5106) | `start_orchestrator_5106.ps1` |
| Pixel 7 | カメラ・ストレージ・ADB | `start_pixel7_bridge.ps1`（USB） / `start_pixel7_bridge_tailscale.ps1`（Tailscale） |
| X280 | SSOT API (5120) | X280 PC で 5120 起動 |
| Konoha | このはサーバー (5106) | このはで 5106 起動 |

- **3/6 をワンクリック**: `quick_start_devices.bat` または `quick_start_devices.ps1`（Pixel 7 ブリッジ + 5106）
- **接続確認**: `scripts\check_devices_online.ps1`
- **詳細**: [PIXEL7_INTEGRATION_GUIDE.md](PIXEL7_INTEGRATION_GUIDE.md) / [DEVICES_ONLINE_SETUP.md](DEVICES_ONLINE_SETUP.md)

## 📚 詳細ドキュメント

- **起動依存関係**: [STARTUP_DEPENDENCY.md](STARTUP_DEPENDENCY.md)
- **Skills と MCP の使い分け**: [SKILLS_AND_MCP_GUIDE.md](SKILLS_AND_MCP_GUIDE.md)
- **Skills ドキュメント索引**: [SKILLS_INDEX.md](SKILLS_INDEX.md)
- **MCP サーバー一覧**: [MCP_SERVERS_GUIDE.md](MCP_SERVERS_GUIDE.md)
- **他にできること（一覧）**: [WHAT_ELSE_YOU_CAN_DO.md](WHAT_ELSE_YOU_CAN_DO.md)
- **sd-prompt（CLI/MCP/API）**: [SD_PROMPT_USAGE.md](SD_PROMPT_USAGE.md)
- **Pixel 7・デバイス統合**: [PIXEL7_INTEGRATION_GUIDE.md](PIXEL7_INTEGRATION_GUIDE.md) / [DEVICES_ONLINE_SETUP.md](DEVICES_ONLINE_SETUP.md)
- 各統合モジュールの詳細は、各ファイルのdocstringを参照してください。
