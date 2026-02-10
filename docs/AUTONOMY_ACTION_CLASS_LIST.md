# Action Class 一覧表（ManaOS エンドポイント C0〜C4 仕分け）

全 MCP ツールを Action Class で分類。未定義ツールは **C4（安全側）** として扱う。

## 凡例

| Class | 意味 | Confirm Token |
|-------|------|----------------|
| **C0** | Read-only（GET/status/search） | 不要 |
| **C1** | Append-only（Obsidian/Rows 追記など） | 不要 |
| **C2** | Reversible（タグ・移動・n8n 安全 WF・秘書ルーチン） | 不要 |
| **C3** | Costly（LLM 大量・画像/動画生成・外部課金） | **必須** |
| **C4** | Destructive（実行・削除・上書き・停止・Docker） | **必須** |

---

## C0: Read-only

| ツール名 | 用途 |
|----------|------|
| device_discover | デバイス検出 |
| device_get_status | デバイス状態一覧 |
| device_get_health | デバイスヘルス |
| device_get_resources | デバイスリソース |
| device_get_alerts | デバイスアラート |
| cache_stats | キャッシュ統計 |
| performance_stats | パフォーマンス統計 |
| phase1_aggregate | Phase1 集計 |
| phase1_compare_on_off | Phase1 ON/OFF 比較 |
| phase1_low_sat_history_view | 低満足度履歴表示 |
| phase2_get_memos | Phase2 メモ取得 |
| phase2_memo_summary | Phase2 メモサマリ |
| obsidian_search_notes | Obsidian 検索 |
| rows_query | Rows クエリ |
| rows_list_spreadsheets | Rows スプレッドシート一覧 |
| file_secretary_inbox_status | ファイル秘書 Inbox 状態 |
| moltbot_health | MoltBot ヘルス |
| moltbot_get_result | MoltBot 結果取得 |
| n8n_list_workflows | n8n ワークフロー一覧 |
| konoha_health | Konoha ヘルス |
| nanokvm_console_url | NanoKVM コンソール URL |
| nanokvm_health | NanoKVM ヘルス |
| voice_health | 音声ヘルス |
| github_search | GitHub 検索 |
| github_commits | GitHub コミット |
| research_status | リサーチ状態 |
| openwebui_list_chats | Open WebUI チャット一覧 |
| openwebui_list_models | Open WebUI モデル一覧 |
| openwebui_get_chat | Open WebUI チャット取得 |
| personality_get_persona | 人格プロフィール取得 |
| personality_get_prompt | 人格プロンプト取得 |
| learning_get_preferences | 学習プリファレンス取得 |
| learning_get_optimizations | 学習最適化取得 |
| autonomy_list_tasks | 自律タスク一覧 |
| autonomy_get_level | 自律レベル取得 |
| memory_recall | 記憶検索 |
| civitai_get_favorites | CivitAI お気に入り |
| civitai_get_images | CivitAI 画像 |
| civitai_get_image_details | CivitAI 画像詳細 |
| civitai_get_creators | CivitAI クリエイター |
| image_stock_search | 画像ストック検索 |
| svi_get_queue_status | SVI キュー状態 |
| pixel7_get_resources | Pixel7 リソース |
| pixel7_get_apps | Pixel7 アプリ一覧 |
| pixel7_screenshot | Pixel7 スクリーンショット |
| mothership_get_resources | 母艦リソース |
| x280_get_resources | X280 リソース |
| google_drive_list_files | Google Drive 一覧 |
| web_search | Web 検索 |
| web_search_simple | Web 検索（簡易） |
| brave_search | Brave 検索 |
| brave_search_simple | Brave 検索（簡易） |
| vscode_search_files | VSCode ファイル検索 |
| pico_hid_mouse_position | Pico HID マウス位置 |
| pico_hid_screen_size | Pico HID 画面サイズ |
| pico_hid_screenshot | Pico HID スクリーンショット |

---

## C1: Append-only

| ツール名 | 用途 |
|----------|------|
| obsidian_create_note | Obsidian ノート作成 |
| rows_send_data | Rows データ送信 |
| memory_store | 記憶保存 |
| notification_send | 通知送信 |
| learning_record | 学習記録 |
| phase1_low_sat_archive | 低満足度アーカイブ追記 |
| phase2_backfill_memos | Phase2 メモバックフィル |

---

## C2: Reversible

| ツール名 | 用途 |
|----------|------|
| file_secretary_organize | ファイル秘書整理 |
| moltbot_submit_plan | MoltBot プラン投入（list_only 等は低リスク） |
| phase2_auto_cleanup | Phase2 自動クリーンアップ |
| personality_update | 人格プロフィール更新 |
| secretary_morning_routine | 秘書朝ルーチン |
| secretary_noon_routine | 秘書昼ルーチン |
| secretary_evening_routine | 秘書夕ルーチン |
| secretary_file_organize | 秘書ファイル整理 |
| learning_analyze | 学習分析 |
| vscode_open_file | VSCode ファイルを開く |
| vscode_open_folder | VSCode フォルダを開く |

---

## C3: Costly（Confirm Token 必須）

| ツール名 | 用途 |
|----------|------|
| llm_chat | LLM チャット |
| base_ai_chat | ベース AI チャット |
| openwebui_create_chat | Open WebUI チャット作成 |
| openwebui_send_message | Open WebUI メッセージ送信 |
| research_quick | リサーチ実行 |
| comfyui_generate_image | ComfyUI 画像生成 |
| svi_generate_video | SVI 動画生成 |
| svi_extend_video | SVI 動画延長 |
| generate_sd_prompt | SD プロンプト生成（LLM） |
| voice_synthesize | 音声合成 |
| pixel7_tts | Pixel7 TTS |
| pixel7_transcribe | Pixel7 文字起こし |
| google_drive_upload | Google Drive アップロード |
| civitai_download_favorites | CivitAI お気に入りダウンロード |
| image_stock_add | 画像ストック追加 |

---

## C4: Destructive（Confirm Token 必須）

| ツール名 | 用途 |
|----------|------|
| n8n_execute_workflow | n8n ワークフロー実行 |
| pixel7_execute | Pixel7 コマンド実行 |
| pixel7_push_file | Pixel7 ファイルプッシュ |
| pixel7_pull_file | Pixel7 ファイルプル |
| mothership_execute | 母艦コマンド実行 |
| x280_execute | X280 コマンド実行 |
| phase1_run_off_3rounds | Phase1 OFF 3 ラウンド |
| phase1_run_on_rounds | Phase1 ON ラウンド |
| phase1_run_extended | Phase1 拡張実行 |
| phase1_save_run | Phase1 スナップショット保存 |
| phase1_phase2_full_run | Phase1/2 フル実行 |
| phase1_run_multi_thread | Phase1 マルチスレッド |
| phase1_low_satisfaction | Phase1 低満足度 |
| phase1_weekly_report | Phase1 週次レポート |
| phase2_dedup_memos | Phase2 メモ重複削除 |
| autonomy_add_task | 自律タスク追加 |
| autonomy_execute_tasks | 自律タスク一括実行 |
| personality_apply | 人格適用 |
| openwebui_update_settings | Open WebUI 設定更新 |
| vscode_execute_command | VSCode コマンド実行 |
| pico_hid_mouse_move | Pico HID マウス移動 |
| pico_hid_mouse_click | Pico HID クリック |
| pico_hid_key_press | Pico HID キー押下 |
| pico_hid_type_text | Pico HID テキスト入力 |
| pico_hid_scroll | Pico HID スクロール |
| pico_hid_mouse_move_absolute | Pico HID 絶対移動 |
| pico_hid_mouse_click_at | Pico HID 指定位置クリック |
| pico_hid_key_combo | Pico HID キーコンボ |
| pico_hid_type_text_auto | Pico HID 自動入力 |
| pico_hid_clear_and_retype_auto | Pico HID クリア＆再入力 |
| pico_hid_click_then_type_auto | Pico HID クリック後入力 |

---

## 更新ルール

- 新規 MCP ツール追加時は `autonomy_gates.py` の `TOOL_ACTION_CLASS` に追加し、本表を同期すること。
- 未登録ツールは C4 として扱う（許可が最も厳しい）。
