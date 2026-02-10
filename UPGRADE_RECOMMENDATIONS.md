# アップデート推奨一覧（2026-01-30 時点）

## ✅ 完了（2026-01-30）
- openai: 2.14.0 → **2.16.0**
- anthropic: 0.75.0 → **0.77.0**
- mcp: 1.25.0 → **1.26.0**
- aiohttp: 3.13.2 → **3.13.3**

## 優先度：高（ManaOSコア関連・積極的に推奨）

| パッケージ | 現在 | 最新 | 備考 |
|-----------|------|------|------|
| **openai** | 2.14.0 | 2.16.0 | LLM統合の要 |
| **anthropic** | 0.75.0 | 0.77.0 | Claude API |
| **mcp** | 1.25.0 | 1.26.0 | Model Context Protocol |
| **aiohttp** | 3.13.2 | 3.13.3 | 非同期HTTP |
| **langchain** | 1.2.0 | 1.2.7 | 利用している場合 |
| **langchain-core** | 1.2.5 | 1.2.7 | 同上 |
| **langchain-openai** | 1.1.6 | 1.1.7 | 同上 |

## 優先度：中（機能拡張・音声・画像関連）

| パッケージ | 現在 | 最新 | 備考 |
|-----------|------|------|------|
| **elevenlabs** | 2.27.0 | 2.33.0 | 音声合成（voice機能利用時） |
| **diffusers** | 0.30.3 | 0.36.0 | 画像生成（破壊的変更の可能性あり） |
| **huggingface-hub** | 0.36.0 | 1.3.5 | メジャーアップ：要テスト |
| **chromadb** | 1.1.1 | 1.4.1 | RAG/ベクトルDB利用時 |

## 優先度：中（ComfyUI関連）

| パッケージ | 現在 | 最新 |
|-----------|------|------|
| comfyui_frontend_package | 1.35.9 | 1.39.2 |
| comfyui_workflow_templates | 0.7.64 | 0.8.28 |
| comfyui-workflow-templates-* | 各種 | 各種 |

## 要検討（メジャーバージョンアップ）

| パッケージ | 現在 | 最新 | 注意点 |
|-----------|------|------|--------|
| **transformers** | 4.57.3 | **5.0.0** | メジャー：API変更の可能性大 |
| **altair** | 5.5.0 | **6.0.0** | 可視化ライブラリ |

## Node.js（ai_learning_system_mcp-server）

| パッケージ | 現在 | 最新 | 備考 |
|-----------|------|------|------|
| **@modelcontextprotocol/sdk** | 0.5.0 | **1.25.3** | メジャーアップ：要マイグレーション |

---

## 推奨実行コマンド

### スクリプトで一括実行（推奨）
```powershell
# コアパッケージのみ
.\scripts\upgrade_packages_safe.ps1 -Target core

# LangChain 関連
.\scripts\upgrade_packages_safe.ps1 -Target langchain

# ComfyUI 関連
.\scripts\upgrade_packages_safe.ps1 -Target comfyui

# すべて
.\scripts\upgrade_packages_safe.ps1 -Target all
```

### 手動コマンド

#### 安全なアップデート（コアパッケージのみ）
```powershell
pip install --upgrade openai anthropic mcp aiohttp langchain langchain-core langchain-openai
```

### ComfyUI関連のみ
```powershell
pip install --upgrade comfyui_frontend_package comfyui_workflow_templates
```

### Node.js MCP SDK
```powershell
cd konoha_mcp_servers\ai_learning_system_mcp-server
npm update @modelcontextprotocol/sdk
# ※ 0.5→1.x は破壊的変更の可能性あり。CHANGELOG確認推奨
```

### ロックファイル再生成（慎重に）
```powershell
pip-compile requirements.in -o requirements.lock.txt
```

---

## ⚠️ 既知の依存関係警告（既存）

アップデート後に表示される可能性のある警告（ManaOSコア動作には影響なし）:

| パッケージ | 問題 | 対応 |
|-----------|------|------|
| crewai | json-repair バージョン不一致 | crewai を更新するか無視可 |
| matrix-nio | aiofiles~=24.1 要求 | `pip install aiofiles~=24.1` |
| mem0ai | protobuf 5.29+ 要求 | 使用時のみ `pip install protobuf>=5.29` |
