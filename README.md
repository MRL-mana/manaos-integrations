# ManaOS Integrations

**v2.6.0** — ManaOS統合サービスシステム

VSCode/Cursorに接続するメモリベースAIアシスタント。ManaOS と外部サービス（ComfyUI / Google Drive / CivitAI / n8n / Slack / Voice など）をつなぐ統合リポジトリ。

---

## 📋 クイックスタート

### 1分で起動（VSCode/Cursor統合）

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

**自動実行される内容:**
- ✅ 4つのコアサービス起動（MRL Memory, Learning System, LLM Routing, Unified API）
- ✅ ヘルスチェック実行（8サービス / 3グループ: コア・インフラ・オプショナル）
- ✅ 自律監視システム起動（System3）

### ヘルスチェック

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

---

## 🏗 アーキテクチャ

### コアサービス

| サービス | ポート | 説明 |
|---|---|---|
| MRL Memory | 5105 | 3層メモリ（Scratchpad → Working → Long-term/Obsidian） |
| Learning System | 5126 | 学習パターン記録・自動最適化フィードバック |
| LLM Routing | 5111 | モデル選択・負荷分散 |
| Unified API | 9502 | 統合エントリポイント |

### PC操作・HID

| サービス | ポート | 説明 |
|---|---|---|
| Windows Automation | 5115 | システム情報・スクリーンショット・プロセス/ウィンドウ管理・winget |
| Pico HID | 5116 | マウス/キーボード操作（Pico USB HID or pynput フォールバック） |

### インフラ

| サービス | ポート | 説明 |
|---|---|---|
| Ollama | 11434 | ローカルLLM推論 |
| Gallery API | 5559 | 画像管理 |

### オプショナル

| サービス | ポート | 説明 |
|---|---|---|
| ComfyUI | 8188 | 画像生成パイプライン |
| Moltbot Gateway | 8088 | チャット連携 |

### MCPサーバー（8サーバー）

| MCPサーバー | 方式 | ツール数 |
|---|---|---|
| manaos-memory | stdio (Flask bridge :5105) | 4 |
| manaos-learning | stdio (Flask bridge :5126) | 6 |
| manaos-unified-api | stdio (:9502) | 多数 |
| manaos-llm-routing | stdio (:5111) | 3 |
| manaos-video-pipeline | stdio (:5112) | 3 |
| manaos-windows-automation | stdio (直接) | 16 |
| manaos-pico-hid | stdio (直接) | 11 |

### メモリアーキテクチャ

```
ユーザー入力
  ├── MRLMemoryExtractor（固有名詞・数値・TODO抽出）
  │     └── Scratchpad → Working Memory → Long-term (Obsidian)
  ├── RAG Memory V2（SQLite + Ollama embeddings）
  └── Learning System（行動パターン学習＋自動最適化提案）
```

---

## 🧪 テスト

```bash
# 全テスト実行（124テスト）
python -m pytest tests/ --tb=short

# カバレッジ付き
python -m pytest tests/ --cov=. --cov-report=term-missing
```

テスト対象:
- `test_mrl_memory.py` — MRL Memory 抽出・Scratchpad・並行書き込み（13テスト）
- `test_learning_system.py` — 学習記録・永続化・自動最適化（14テスト）
- `test_health_check.py` — ヘルスチェック・設定検証（18テスト）
- `test_manaos_logger.py` — 統合ロガー（7テスト）
- `test_gpu_resource_manager.py` — GPU非同期管理（8テスト）
- `test_windows_automation.py` — Windows自動化ツールキット（14テスト）
- `test_pico_hid.py` — Pico HID / pynput マウス・キーボード（13テスト）

---

## 📝 ロギング

全コアモジュールは `manaos_logger.get_logger(__name__)` で統一されたロガーを使用:
- **RotatingFileHandler**: `logs/` 配下に自動ローテーション（10MB × 5世代）
- **コンソール出力**: 構造化フォーマット
- **try/except フォールバック**: `manaos_logger` が利用不可の場合は標準 `logging.getLogger` にフォールバック

---

## 詳細ドキュメント

- **[クイックリファレンス](QUICKREF.md)** - 1ページのチートシート
- **[VSCodeセットアップ](VSCODE_SETUP_GUIDE.md)** - VSCode完全セットアップガイド
- **[VSCode vs Cursor](VSCODE_VS_CURSOR.md)** - どっちを使うべき?比較ガイド
- **[VSCodeチェックリスト](VSCODE_CHECKLIST.md)** - 対応状況とクイックガイド
- **[起動ガイド](STARTUP_GUIDE.md)** - 詳細な起動手順
- **[System3ガイド](SYSTEM3_GUIDE.md)** - 自律運用システム
- **[緊急停止ガイド](EMERGENCY_STOP_GUIDE.md)** - 緊急停止方法
- **[MCPサーバーガイド](docs/guides/MCP_SERVERS_GUIDE.md)** - MCP設定と使い方
- **[セキュリティ](docs/guides/SECURITY_HARDENING.md)** - API認証・ハードニング

---

## 重要（セキュリティ）

- **統合APIサーバー**: `unified_api_server.py`
- **最小ハードニング手順**: `docs/guides/SECURITY_HARDENING.md`
  - 3段階キー（Admin / Ops / Read-only）
  - IP allow/block、CORS制御
  - 監査ログ、Confirm Token、Rate limit / Concurrency
  - OpenAPI公開制御、セキュリティヘッダ

## 起動

### クイックスタート（MCP・秘書ファイル整理）

統合API (9502) と MoltBot Gateway (8088) をまとめて起動する場合:

```bat
start_unified_api_and_moltbot.bat
```

疎通確認: `scripts\check_manaos_stack.bat`（拡張: `.\scripts\check_manaos_stack.ps1 -Extended`）。.env に `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088` を設定すると MCP から秘書ファイル整理が利用可能。**よく使う起動・確認一覧**: [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)

### 開発（ローカル）

```bash
python unified_api_server.py
```

### 本番（推奨: Waitress）

```bat
start_unified_api_server_prod.bat
```

## 依存関係

- 最小: `requirements-core.txt`
- 開発: `requirements-dev.txt`（pytest, pytest-asyncio, mypy 等）
- 全部入り: `requirements.txt`

## MCPサーバー

- **MCP本体**: `manaos_unified_mcp_server/server.py`
- **一括登録**: `.\add_all_mcp_servers_to_cursor.ps1`（プロジェクトルートで実行、パスは自動取得）
- **詳細**: [docs/guides/MCP_SERVERS_GUIDE.md](docs/guides/MCP_SERVERS_GUIDE.md)
- **Skills と MCP の使い分け**: [docs/guides/SKILLS_AND_MCP_GUIDE.md](docs/guides/SKILLS_AND_MCP_GUIDE.md)
- **起動依存関係**: [docs/guides/STARTUP_DEPENDENCY.md](docs/guides/STARTUP_DEPENDENCY.md)

## スクリプト整理

`scripts/CATALOG.md` にルート配下のスクリプト一覧がカテゴリ別に整理されています。カタログ更新:

```bash
python scripts/catalog_scripts.py > scripts/CATALOG.md
```
