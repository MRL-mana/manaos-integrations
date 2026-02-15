# 他にできること（ManaOS 統合まわり）

デバイス・母艦・Pixel 7 のほかに、**今すぐ使える機能**と**追加で取り込めるもの**をまとめます。

**スタックをまとめて起動**: 統合API (9500) と MoltBot Gateway (8088) を両方起動するには、リポジトリルートで **`start_unified_api_and_moltbot.bat`** を実行する。2つの窓が開き、MCP と秘書ファイル整理が利用可能になる。疎通確認は **`scripts\check_manaos_stack.bat`** または **`scripts\check_manaos_stack.ps1`**。

---

## 今すぐ使えるもの

### デバイス・状態

| 手段 | 内容 |
|------|------|
| **MCP** `device_discover` | 全デバイス検出・オンライン数 |
| **MCP** `device_get_status` | オーケストレーターの状態・キュー |
| **MCP** `device_get_health` | 特定デバイス（mothership, x280, konoha）の CPU/メモリ/ディスク |
| **MCP** `device_get_resources` | 全デバイスのリソース一覧 |
| **MCP** `device_get_alerts` | 全デバイスのアラート |
| **統合API** `GET /api/devices/status` | 全デバイス状態（オーケストレーター経由） |

### 端末ごとの操作（統合API + MCP）

| 端末 | リソース取得 | コマンド実行 | その他 |
|------|--------------|--------------|--------|
| **母艦** | `GET /api/mothership/resources` / `mothership_get_resources` | `POST /api/mothership/execute` / `mothership_execute` | マウス/キー/スクショ: `pico_hid_*` |
| **Pixel 7** | `GET /api/pixel7/resources` / `pixel7_get_resources` | `POST /api/pixel7/execute` / `pixel7_execute` | `pixel7_screenshot`, `pixel7_get_apps`, push/pull |
| **X280** | `GET /api/x280/resources` / `x280_get_resources` | `POST /api/x280/execute` / `x280_execute` | X280 で 5120 起動が必要 |
| **Konoha** | - | - | `GET /api/konoha/health` / MCP `konoha_health`（このは 5106） |
| **NanoKVM** | - | - | `GET /api/nanokvm`（疎通）/ `GET /api/nanokvm/console_url`（ログインURL）/ `GET /api/nanokvm/health`（到達性）。MCP: `nanokvm_console_url`, `nanokvm_health`。ログイン後は KVM コンソールで接続先を操作可能。 |
| **Pixel 7 スクショ** | - | - | `GET /api/pixel7/screenshot` / MCP `pixel7_screenshot` |
| **Pixel 7 アプリ** | - | - | `GET /api/pixel7/apps` / MCP `pixel7_get_apps` |
| **Pixel 7 音声出力（TTS）** | - | - | `POST /api/pixel7/tts`（text→合成→Push→再生）/ MCP `pixel7_tts`。音声統合要。 |
| **Pixel 7 音声入力（文字起こし）** | - | - | `POST /api/pixel7/transcribe`（remote_path→Pull→STT）/ MCP `pixel7_transcribe`。端末で録音したファイルを指定。 |
| **File Secretary** | - | - | `GET /api/file-secretary/health`, `/api/file-secretary/inbox/status`, `POST /api/file-secretary/files/organize`（FILE_SECRETARY_URL 要） |

### 画像・動画・検索・AI

- **ComfyUI** 画像生成、**SVI** 動画生成、**LTX2**、**CivitAI** 検索・お気に入り
- **SD プロンプト** 日本語→英語（Ollama）
- **Web 検索** `web_search`, `brave_search`、**LLM** `llm_chat`, `base_ai_chat`、**Open WebUI** チャット作成・送信
- **Step Deep Research** `research_quick`（クイック調査）、`research_status`（ジョブ状態）。統合API `/api/research/quick` 等。

### メモリ・ノート・学習

- **記憶** `memory_store`, `memory_recall`
- **Obsidian** ノート作成・検索
- **Phase1/Phase2** 振り返り・メモ・週次レポート
- **学習** `learning_record`, `learning_analyze`, `learning_get_preferences`
- **人格** `personality_get_persona`, `personality_apply` など

### その他 MCP

- **Rows** スプレッドシート検索・データ送信
- **Google Drive** アップロード、一覧
- **通知** `notification_send`
- **MoltBot** Plan 送信・結果取得
- **自律** `autonomy_add_task`, `autonomy_execute_tasks`, `autonomy_list_tasks`
- **秘書** 朝/昼/夜ルーチン、**秘書ファイル整理** `secretary_file_organize`（path / intent / user_hint → MoltBot Plan）。※ **MoltBot Gateway がオフラインだと失敗**（`moltbot_health` で確認。デバイス一覧の `moltbot-konoha` が ONLINE か、または母艦のみなら `MOLTBOT_GATEWAY_URL` で localhost:8088 を指し Gateway を起動。起動方法は `docs/integration/MOLTBOT_MANAOS_INTEGRATION_DESIGN.md` や `moltbot_gateway/deploy/` 参照）
- **音声** `voice_health`（稼働確認）、`voice_synthesize`（TTS。音声バイナリは統合APIから取得）
- **n8n** `n8n_list_workflows`（ワークフロー一覧）、`n8n_execute_workflow`（workflow_id で実行）
- **GitHub** `github_search`（query でリポジトリ検索）、`github_commits`（owner/repo で直近コミット）
- **監視** `cache_stats`（キャッシュ統計）、`performance_stats`（パフォーマンス統計）
- **VSCode/Cursor** `vscode_open_file`, `vscode_open_folder`, `vscode_execute_command`, `vscode_search_files`（条件付き表示）

---

## 統合API にあるが上の表に書ききれていないもの

同じことは **統合API（Unified API Server）** からも呼べます。主なカテゴリだけ挙げます。

| カテゴリ | 例（パス） |
|----------|------------|
| **音声** | `/api/voice/transcribe`, `/api/voice/synthesize`, `/api/voice/conversation`, `/api/voice/health` |
| **キャッシュ・パフォーマンス** | `/api/cache/get`, `/api/cache/set`, `/api/cache/stats`, `/api/performance/stats` |
| **メモリ・通知・秘書** | `/api/memory/store`, `/api/memory/recall`, `/api/notification/send`, `/api/secretary/morning` など |
| **VSCode / GitHub** | `/api/vscode/open`, `/api/vscode/open-folder`, `/api/github/repository`, `/api/github/commits`, `/api/github/search` など |
| **n8n** | `/api/n8n/workflows`, `/api/n8n/workflow/<id>/execute`, activate, deactivate |
| **画像ストック** | `/api/image/stock`, `/api/image/search`, `/api/image/statistics` |
| **Rows（詳細）** | `/api/rows/ai/query`, `/api/rows/ai/analyze`, `/api/rows/data/send`, `/api/rows/export/slack`, `/api/rows/import/csv`, `/api/rows/export/csv` など |
| **Excel** | `/api/excel/process`, `/api/excel/summary` |
| **Step Deep Research** | `/api/research/create`, `/api/research/execute/<id>`, `/api/research/status/<id>`, `/api/research/quick` |
| **緊急・運用** | `/api/emergency/logs`, `/api/emergency/workflow`, `/api/emergency/status`, `/api/system/docker/containers` など |
| **LLM ルーティング** | `/api/llm/route`, `/api/llm/chat`, `/api/llm/route-enhanced`, `/api/lfm25/chat` など |
| **その他** | `/api/oh_my_opencode/execute`, `/api/langchain/chat`, `/api/mem0/add`, `/api/obsidian/create`, `/api/integrations/status`, `/api/orchestrator/stats` |

OpenAPI: `GET /openapi.json` で全パスを確認できます。

---

## 意図分類（Intent Router）

「Pixel 7 のバッテリー教えて」「デバイス状態」→ **device_status** に分類されます。

その他: conversation, task_execution, information_search, image_generation, code_generation, system_control, scheduling, data_analysis, deep_research, file_management, file_search, file_status など。
Task Queue / Executor 側で意図に応じた実行パスを増やすと、音声やチャットからそのまま動かせます。

---

## 追加で取り込むなら（例）

- **Konoha**: 統合API に **済** — `GET /api/konoha/health`、MCP `konoha_health`。`KONOHA_URL`（デフォルト http://100.93.120.33:5106）。リモート実行はオーケストレーター設計次第。
- **File Secretary**: 統合API に **済** — `GET /api/file-secretary/health`, `GET /api/file-secretary/inbox/status`, `POST /api/file-secretary/files/organize`。`FILE_SECRETARY_URL`（デフォルト http://127.0.0.1:5120）で File Secretary を指す。
- **Step Deep Research**: 統合API に **済** — `/api/research/quick`, `/api/research/status/<job_id>`。MCP に **済** — `research_quick`, `research_status`。

---

## 起動・確認のリンク

- デバイスをオンラインに: [DEVICES_ONLINE_SETUP.md](DEVICES_ONLINE_SETUP.md)
- Pixel 7・母艦の取り込み: [PIXEL7_INTEGRATION_GUIDE.md](PIXEL7_INTEGRATION_GUIDE.md) の「ManaOS への取り込み」
- 全体ガイド: [README.md](README.md)
