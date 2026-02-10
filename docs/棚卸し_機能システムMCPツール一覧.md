# 機能・システム・MCP・ツール 包括的棚卸し一覧

最終更新: 2025-02-01

> インフラ・デバイス構成は `棚卸し_母艦とまなOSとサーバー.md` 参照

---

## 目次

1. [統合モジュール（Integration）](#1-統合モジュールintegration)
2. [内部システム（System）](#2-内部システムsystem)
3. [MCPサーバー・ツール](#3-mcpサーバーとツール)
4. [統合APIエンドポイント（9500）](#4-統合apiエンドポイント9500)
5. [CLIツール・スクリプト](#5-cliツールスクリプト)
6. [Cursor Skills（YAML駆動）](#6-cursor-skillsyaml駆動)
7. [外部MCP・OpenAPIサーバー](#7-外部mcpopenapiサーバー)

---

## 1. 統合モジュール（Integration）

| モジュール | ファイル | 概要 |
|------------|----------|------|
| **ComfyUI** | `comfyui_integration.py` | 画像生成（Stable Diffusion） |
| **SVI × Wan 2.2** | `svi_wan22_video_integration.py` | 動画生成 |
| **LTX-2** | `ltx2_video_integration.py` | LTX-2動画生成 |
| **LTX-2 Infinity** | `ltx2_infinity_integration.py` | 無限動画・テンプレート管理 |
| **Google Drive** | `google_drive_integration.py` | ファイルアップロード・一覧 |
| **CivitAI** | `civitai_integration.py` | モデル検索・お気に入り・画像取得 |
| **Rows** | `rows_integration.py` | スプレッドシート（AIクエリ・データ送信） |
| **Obsidian** | `obsidian_integration.py` | ノート作成・検索 |
| **LangChain** | `langchain_integration.py` | LLMチャット（LangChain） |
| **Mem0** | `mem0_integration.py` | メモリ追加・検索 |
| **n8n** | `n8n_integration.py` | ワークフロー一覧・実行・有効化/無効化 |
| **Slack** | `slack_integration.py` | メッセージ送信・イベント受信 |
| **GitHub** | `github_integration.py` | リポジトリ・コミット・PR・検索 |
| **SearXNG** | `searxng_integration.py` | ウェブ検索 |
| **Brave Search** | `brave_search_integration.py` | Brave Search API |
| **Base AI** | `base_ai_integration.py` | Base AI チャット |
| **Oh My OpenCode** | `oh_my_opencode_integration.py` | OpenCode実行 |
| **Voice** | `voice_integration.py` | STT・TTS・音声会話 |
| **Local LLM** | `local_llm_integration.py` | LM Studio / Ollama |
| **MRL Memory** | `mrl_memory_integration.py` | MRLメモリ連携 |
| **Portal Voice** | `portal_voice_integration.py` | ポータル音声統合 |
| **Hugging Face** | `huggingface_integration.py` | HFモデル連携 |
| **Excel LLM** | `excel_llm_integration.py` | Excel×LLM処理 |
| **Database** | `database_integration.py` | DB操作 |
| **Cloud** | `cloud_integration.py` | クラウド連携 |
| **CrewAI** | `crewai_integration.py` | CrewAIエージェント |
| **Multimodal** | `multimodal_integration.py` | マルチモーダル |
| **NectarSTT** | `nectarstt_integration.py` | 音声認識 |
| **Payment** | `payment_integration.py` | 決済連携 |
| **Prometheus** | `prometheus_integration.py` | メトリクス |
| **FWPKM** | `fwpkm_integration.py` | FWPKM連携 |
| **Step Deep Research** | `step_deep_research/trinity_integration.py` | 専門調査員AI |

---

## 2. 内部システム（System）

| システム | ファイル | ポート | 概要 |
|----------|----------|--------|------|
| **Intent Router** | `intent_router.py` | 5100 | 意図分類 |
| **Task Planner** | `task_planner.py` | 5101 | タスク計画 |
| **Task Critic** | `task_critic.py` | 5102 | タスク評価 |
| **RAG Memory** | `rag_memory_enhanced.py` | 5103 | RAG記憶 |
| **Task Queue** | `task_queue_system.py` | 5104 | タスクキュー |
| **UI Operations** | `ui_operations_api.py` | 5105 | UI操作API |
| **Unified Orchestrator** | `unified_orchestrator.py` | 5106 | 統合オーケストレーター |
| **Executor Enhanced** | `task_executor_enhanced.py` | 5107 | タスク実行 |
| **Portal Integration** | `portal_integration_api.py` | 5108 | ポータル連携 |
| **Content Generation** | `content_generation_loop.py` | 5109 | コンテンツ生成 |
| **LLM Optimization** | `llm_optimization.py` | 5110 | LLM最適化 |
| **Service Monitor** | `service_monitor.py` | 5111 | サービス監視 |
| **System Status** | `system_status_api.py` | 5112 | ステータスAPI |
| **Slack Integration** | `slack_integration.py` | 5114 | Slack API |
| **Portal Voice** | `portal_voice_integration.py` | 5116 | ポータル音声 |
| **SSOT API** | `ssot_api.py` | 5120 | 単一信頼ソース |
| **Step Deep Research** | `step_deep_research_service.py` | 5121 | 専門調査 |
| **Personality** | `personality_system.py` | 5123 | 人格システム |
| **Autonomy** | `autonomy_system.py` | 5124 | 自律システム |
| **Secretary** | `secretary_system.py` | 5125 | 秘書システム |
| **Learning System** | `learning_system_api.py` | 5126 | 学習記録・分析 |
| **Metrics Collector** | `metrics_collector.py` | 5127 | メトリクス収集 |
| **Performance Dashboard** | `performance_dashboard.py` | 5128 | パフォーマンスダッシュボード |
| **Intrinsic Motivation** | `intrinsic_motivation.py` | 5130 | 内発的動機・スコア |
| **Todo Queue** | `intrinsic_todo_queue.py` | 5134 | TODOキュー |
| **Degraded Mode** | `degraded_mode_system.py` | - | 劣化運転モード |
| **Self Protection** | `self_protection_system.py` | - | 自己保護 |
| **Comprehensive Self Capabilities** | `comprehensive_self_capabilities_system.py` | - | 自己能力体系 |

---

## 3. MCPサーバーとツール

### 3.1 ManaOS統合MCP（manaos_unified_mcp_server）

**設定**: `add_to_cursor_mcp.ps1` または `manaos_unified_mcp_server/add_to_cursor_mcp.ps1`

| カテゴリ | ツール名 | 説明 |
|----------|----------|------|
| **動画** | `svi_generate_video` | SVI×Wan2.2 動画生成 |
| | `svi_extend_video` | 動画延長 |
| | `svi_get_queue_status` | キュー状態取得 |
| **画像** | `comfyui_generate_image` | ComfyUI画像生成 |
| | `generate_sd_prompt` | 日本語→SD英語プロンプト（Ollama） |
| **CivitAI** | `civitai_get_favorites` | お気に入り一覧 |
| | `civitai_download_favorites` | お気に入りダウンロード |
| | `civitai_get_images` | 画像取得 |
| | `civitai_get_image_details` | 画像詳細 |
| | `civitai_get_creators` | クリエイター一覧 |
| **Google Drive** | `google_drive_upload` | アップロード |
| | `google_drive_list_files` | 一覧取得 |
| **Rows** | `rows_query` | AI自然言語クエリ |
| | `rows_send_data` | データ送信 |
| | `rows_list_spreadsheets` | スプレッドシート一覧 |
| **Obsidian** | `obsidian_create_note` | ノート作成 |
| | `obsidian_search_notes` | ノート検索 |
| **画像ストック** | `image_stock_add` | 画像追加 |
| | `image_stock_search` | 画像検索 |
| **通知** | `notification_send` | 通知送信 |
| **記憶** | `memory_store` | 記憶に保存 |
| | `memory_recall` | 記憶から検索 |
| **LLM** | `llm_chat` | LLMチャット（最適モデル自動選択） |
| **秘書** | `secretary_morning_routine` | 朝ルーチン |
| | `secretary_noon_routine` | 昼ルーチン |
| | `secretary_evening_routine` | 夜ルーチン |
| **学習** | `learning_record` | 使用パターン記録 |
| | `learning_analyze` | パターン分析 |
| | `learning_get_preferences` | 好み取得 |
| | `learning_get_optimizations` | 最適化提案取得 |
| **人格** | `personality_get_persona` | 人格プロフィール取得 |
| | `personality_get_prompt` | 人格プロンプト取得 |
| | `personality_apply` | プロンプトに人格適用 |
| | `personality_update` | 人格プロフィール更新 |
| **自律** | `autonomy_add_task` | 自律タスク追加 |
| | `autonomy_execute_tasks` | 自律タスク実行 |
| | `autonomy_list_tasks` | タスク一覧 |
| | `autonomy_get_level` | 自律レベル取得 |
| **デバイス** | `device_discover` | 全デバイス検出 |
| | `device_get_status` | デバイス状態取得 |
| **MoltBot** | `moltbot_submit_plan` | Plan送信 |
| | `moltbot_get_result` | 実行結果取得 |
| | `moltbot_health` | ヘルスチェック |
| **VS Code** | `vscode_open_file` | ファイルを開く |
| | `vscode_open_folder` | フォルダを開く |

※ VS Codeツールは `MANAOS_ENABLE_VSCODE_TOOLS=true` で有効化

---

### 3.2 個別MCPサーバー（add_all_mcp_servers_to_cursor.ps1 で追加）

| サーバー名 | モジュール | 接続先 | 主なツール |
|------------|------------|--------|------------|
| **ltx2** | `ltx2_mcp_server` | 9500 | ltx2_generate, ltx2_get_queue, ltx2_get_history, ltx2_get_status |
| **phase1** | `phase1_mcp_server` | ローカル | phase1_run_off, phase1_run_on, phase1_save_run, phase1_aggregate, phase1_compare_on_off |
| **unified-api** | `unified_api_mcp_server` | 9500 | 統合APIのラッパー |
| **step-deep-research** | `step_deep_research_mcp_server` | 5121 | 専門調査員AI |
| **gallery-api** | `gallery_api_mcp_server` | 5559 | ギャラリーAPI |
| **system-status** | `system_status_mcp_server` | 5112 | システムステータス |
| **ssot-api** | `ssot_mcp_server` | 5120 | SSOT API |
| **service-monitor** | `service_monitor_mcp_server` | 5111 | サービス監視 |
| **web-voice** | `web_voice_mcp_server` | 5115 | ウェブ音声 |
| **portal-integration** | `portal_integration_mcp_server` | 5108 | ポータル連携 |
| **slack-integration** | `slack_integration_mcp_server` | 5114 | Slack |
| **portal-voice-integration** | `portal_voice_integration_mcp_server` | 5116 | ポータル音声 |

---

### 3.3 n8n MCP

| ツール | 説明 |
|--------|------|
| `n8n_list_workflows` | ワークフロー一覧取得 |
| `n8n_import_workflow` | ワークフローインポート |
| `n8n_activate_workflow` | ワークフロー有効化 |
| `n8n_deactivate_workflow` | ワークフロー無効化 |
| `n8n_execute_workflow` | ワークフロー実行 |

---

### 3.4 LLMルーティング MCP

| ツール | 説明 |
|--------|------|
| `analyze_llm_difficulty` | プロンプト難易度分析 |
| `route_llm_request` | LLMリクエストルーティング |
| `get_available_models` | 利用可能モデル一覧 |

---

### 3.5 SVI MCP（svi_mcp_server）

| ツール | 説明 |
|--------|------|
| `svi_check_connection` | ComfyUI接続確認 |
| `svi_generate_video` | 動画生成 |
| `svi_extend_video` | 動画延長 |
| `svi_create_story_video` | ストーリー動画作成 |
| `svi_get_queue_status` | キュー状態 |

---

### 3.6 外部MCP（Cursorに登録されているもの）

| サーバー | ツール | 概要 |
|----------|--------|------|
| **Byterover** | `byterover-store-knowledge` | 知識の保存 |
| | `byterover-retrieve-knowledge` | 知識の検索 |
| **cursor-browser-extension** | `browser_navigate` | ブラウザナビゲーション |
| | `browser_click` | クリック |
| | `browser_type` | テキスト入力 |
| | `browser_snapshot` | スナップショット |
| | `browser_take_screenshot` | スクリーンショット |
| | `browser_tabs` | タブ操作 |
| | その他多数 | フォーム入力・ドラッグ等 |

---

## 4. 統合APIエンドポイント（9500）

### 4.1 ヘルス・ステータス

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/ready` |  readiness |
| GET | `/status` | ステータス |
| GET | `/api/integrations/status` | 統合システム状態 |

### 4.2 画像・動画生成

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/comfyui/generate` | ComfyUI画像生成 |
| POST | `/api/sd-prompt/generate` | SDプロンプト生成（Ollama） |
| POST | `/api/svi/generate` | SVI動画生成 |
| POST | `/api/svi/extend` | 動画延長 |
| POST | `/api/svi/story` | ストーリー動画 |
| GET | `/api/svi/queue` | SVIキュー |
| GET | `/api/svi/history` | SVI履歴 |
| POST | `/api/svi/batch/generate` | バッチ動画生成 |
| GET | `/api/svi/status/<prompt_id>` | SVI状態 |
| POST | `/api/ltx2/generate` | LTX-2動画生成 |
| GET | `/api/ltx2/queue` | LTX-2キュー |
| GET | `/api/ltx2/history` | LTX-2履歴 |
| POST | `/api/ltx2-infinity/generate` | LTX-2 Infinity動画 |
| GET/POST | `/api/ltx2-infinity/templates` | LTX-2テンプレート |

### 4.3 クラウド・ストレージ

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/google_drive/upload` | Google Driveアップロード |
| GET | `/api/civitai/search` | CivitAI検索 |
| GET | `/api/civitai/favorites` | お気に入り |
| GET | `/api/civitai/images` | 画像一覧 |
| POST | `/api/civitai/favorites/download` | お気に入りダウンロード |

### 4.4 LLM・AI

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/local-llm/systems` | ローカルLLM一覧 |
| POST | `/api/llm/route` | LLMルーティング |
| POST | `/api/llm/chat` | LLMチャット |
| POST | `/api/llm/route-enhanced` | 拡張ルーティング |
| POST | `/api/llm/analyze` | 難易度分析 |
| GET | `/api/llm/models-enhanced` | モデル一覧 |
| POST | `/api/lfm25/chat` | LFM 2.5チャット |
| POST | `/api/lfm25/lightweight` | LFM 2.5軽量会話 |
| POST | `/api/langchain/chat` | LangChainチャット |
| POST | `/api/base-ai/chat` | Base AIチャット |
| POST | `/api/oh_my_opencode/execute` | Oh My OpenCode |

### 4.5 音声（Voice）

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/voice/transcribe` | STT |
| POST | `/api/voice/synthesize` | TTS |
| POST | `/api/voice/synthesize/stream` | TTSストリーミング |
| POST | `/api/voice/conversation` | 音声会話 |
| GET | `/api/voice/health` | 音声ヘルス |
| GET | `/api/voice/metrics` | 音声メトリクス |
| GET | `/api/voice/speakers` | スピーカー一覧 |

### 4.6 記憶・通知・秘書

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/memory/store` | 記憶に保存 |
| GET | `/api/memory/recall` | 記憶から検索 |
| POST | `/api/notification/send` | 通知送信 |
| POST | `/api/secretary/morning` | 朝ルーチン |
| POST | `/api/secretary/noon` | 昼ルーチン |
| POST | `/api/secretary/evening` | 夜ルーチン |
| POST | `/api/mem0/add` | Mem0メモリ追加 |

### 4.7 Rows・Excel

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/rows/spreadsheets` | スプレッドシート一覧 |
| POST | `/api/rows/spreadsheets` | スプレッドシート作成 |
| GET | `/api/rows/spreadsheets/<id>` | スプレッドシート取得 |
| POST | `/api/rows/ai/query` | AI自然言語クエリ |
| POST | `/api/rows/ai/analyze` | AIデータ分析 |
| POST | `/api/rows/data/send` | データ送信 |
| POST | `/api/rows/export/slack` | Slackエクスポート |
| POST | `/api/rows/batch/update` | バッチ更新 |
| POST | `/api/rows/import/csv` | CSVインポート |
| POST | `/api/rows/export/csv` | CSVエクスポート |
| POST | `/api/excel/process` | Excel処理 |
| POST | `/api/excel/summary` | Excelサマリー |

### 4.8 その他

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/obsidian/create` | Obsidianノート作成 |
| GET/POST | `/api/searxng/search` | SearXNG検索 |
| GET/POST | `/api/brave/search` | Brave Search |
| POST | `/api/image/stock` | 画像ストック |
| GET | `/api/image/search` | 画像検索 |
| GET | `/api/github/repository` | GitHubリポジトリ |
| GET | `/api/github/commits` | コミット一覧 |
| GET | `/api/github/pull_requests` | PR一覧 |
| GET | `/api/n8n/workflows` | n8nワークフロー |
| POST | `/api/n8n/workflow/<id>/execute` | ワークフロー実行 |
| POST | `/api/research/create` | 専門調査作成 |
| POST | `/api/research/execute/<job_id>` | 調査実行 |
| GET | `/api/cache/get` | キャッシュ取得 |
| POST | `/api/cache/set` | キャッシュ保存 |
| POST | `/api/vscode/open` | VS Codeで開く |

### 4.9 緊急・システム

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/emergency` | 緊急用ダッシュボード |
| GET | `/api/emergency/status` | 緊急ステータス |
| POST | `/api/emergency/workflow` | ワークフロー実行 |
| GET | `/api/system/docker/containers` | Dockerコンテナ一覧 |

---

## 5. CLIツール・スクリプト

### 5.1 起動系

| スクリプト | 内容 |
|------------|------|
| `start_all_manaos_services.ps1` | 全ManaOSサービス一括起動 |
| `start_system3_services.ps1` | System3系のみ |
| `start_all_llm_services_auto.ps1` | LM Studio + LLM Routing |
| `start_all_services.ps1` | 統合API + LLM Routing |
| `auto_restart_services.ps1` | 監視・自動再起動 |

### 5.2 確認・診断

| スクリプト/コマンド | 内容 |
|---------------------|------|
| `python check_service_status.py` | サービス状態確認 |
| `python system3_health_check.py` | System3ヘルスチェック |
| `python device_health_monitor.py` | デバイス監視 |
| `health_check_auto.ps1` | ヘルスチェック自動 |
| `validate_mcp_config.py` | MCP設定検証 |

### 5.3 設定・セットアップ

| スクリプト | 内容 |
|------------|------|
| `add_all_mcp_servers_to_cursor.ps1` | MCP一括登録 |
| `apply_n8n_api_key_auto.ps1` | n8n APIキー適用 |
| `apply_slack_config.py` | Slack設定適用 |
| `add_brave_api_key_to_mcp.ps1` | Brave APIキー追加 |

### 5.4 ユーティリティ

| スクリプト/コマンド | 内容 |
|---------------------|------|
| `generate_50_mana_mufufu_manaos.py` | まなキャラ画像一括生成 |
| `download_civitai_favorites.py` | CivitAIお気に入りDL |
| `cross_platform_file_sync.py` | クロスプラットフォーム同期 |
| `create_system3_status.py` | System3ステータス生成 |
| `phase1_metrics_snapshot.py` | Phase1メトリクススナップショット |
| `create_playbook_promotion_rules.py` | プレイブック昇格ルール作成 |

---

## 6. Cursor Skills（YAML駆動）

`.cursor/rules` の agent_requestable_workspace_rules として登録：

| スキル | ファイル | 概要 |
|--------|----------|------|
| **server_monitor** | `server_monitor_skill.mdc` | サーバー監視・復旧（YAML） |
| **rows_ops** | `rows_ops_skill.mdc` | Rowsスプレッドシート操作 |
| **notion_ops** | `notion_ops_skill.mdc` | Notion DB操作 |
| **n8n_workflow** | `n8n_workflow_skill.mdc` | n8nワークフロー操作 |
| **log_analysis** | `log_analysis_skill.mdc` | ログ分析・レポート |
| **git_ops** | `git_ops_skill.mdc` | Git操作 |
| **file_organize** | `file_organize_skill.mdc` | ファイル整理・分類 |
| **email_ops** | `email_ops_skill.mdc` | メール送信 |
| **drive_backup** | `drive_backup_skill.mdc` | Google Driveバックアップ |
| **db_backup** | `db_backup_skill.mdc` | DBバックアップ |
| **data_transform** | `data_transform_skill.mdc` | データ変換 |
| **database_ops** | `database_ops_skill.mdc` | DB操作 |
| **daily_ops** | `daily_ops_skill.mdc` | 日次運用（Obsidian+Slack） |
| **calendar_ops** | `calendar_ops_skill.mdc` | カレンダー操作 |

---

## 7. 外部MCP・OpenAPIサーバー

### 7.1 OpenAPIサーバー（openapi-servers/servers）

| サーバー | 概要 |
|----------|------|
| `bitcoin-price-predictor` | ビットコイン価格予測 |
| `external-rag` | 外部RAG |
| `filesystem` | ファイルシステム |
| `flashcards` | フラッシュカード |
| `get-oauth-tokens` | OAuthトークン取得 |
| `get-tokens-from-cookies` | クッキーからトークン |
| `get-user-info` | ユーザー情報 |
| `git` | Git操作 |
| `google-pse` | Google PSE |
| `mcp-proxy` | MCPプロキシ |
| `memory` | メモリ |
| `quotes-ui` | 引用UI |
| `slack` | Slack |
| `summarizer-tool` | 要約ツール |
| `time` | 時刻 |
| `time-ui` | 時刻UI |
| `weather` | 天気 |
| `sql` | SQL |

### 7.2 Konoha MCP群（konoha_mcp_servers）

> Konoha = このはサーバー（レンタルVPS、100.93.120.33）。インフラ詳細は `棚卸し_母艦とまなOSとサーバー.md` 参照。

| 種別 | 内容 |
|------|------|
| **ai_learning_system** | AI学習システム（Node.js） |
| **mcp_proxy** | MCPプロキシ |
| **super_ocr_pipeline** | OCRパイプライン |
| **trinity_workspace_mcp_bridge** | Trinityワークスペースブリッジ |
| **manaos_unified_system_mcp** | 統合MCP（Docker） |

---

## 8. ドキュメント・ガイド

| ドキュメント | 概要 |
|--------------|------|
| `docs/guides/README.md` | 外部システム統合ガイド |
| `docs/guides/SECURITY_HARDENING.md` | セキュリティ強化 |
| `docs/guides/HOW_TO_USE_LLM_TOOLS.md` | LLMツール使い方 |
| `docs/guides/SD_PROMPT_USAGE.md` | SDプロンプト |
| `docs/guides/MUFUFU_LLAMA3_UNCENSORED.md` | Mufufu Llama3 |
| `docs/guides/N8N_LOCAL_SETUP.md` | n8nローカルセットアップ |
| `docs/BYTEROVER_活用ガイド.md` | Byterover MCP活用 |
| `LTX2_QUICKSTART.md` | LTX-2クイックスタート |
| `MRL_MEMORY_RUNBOOK.md` | MRLメモリ運用 |

---

## 9. 依存関係・環境変数（主要）

| 環境変数 | 用途 |
|----------|------|
| `COMFYUI_URL` | ComfyUI（デフォルト: 8188） |
| `OLLAMA_URL` | Ollama（11434） |
| `LM_STUDIO_URL` | LM Studio（1234/v1） |
| `MANAOS_INTEGRATION_PORT` | 統合API（9500） |
| `N8N_BASE_URL` | n8n（5678/5679） |
| `OBSIDIAN_VAULT_PATH` | Obsidian Vault |
| `CIVITAI_API_KEY` | CivitAI |
| `SLACK_BOT_TOKEN` | Slack |
| `MANAOS_INTEGRATION_API_KEY` | 統合API認証（Admin） |
| `MANAOS_INTEGRATION_OPS_API_KEY` | Ops |
| `MANAOS_INTEGRATION_READONLY_API_KEY` | Read-only |

詳細は `env.example` を参照。
