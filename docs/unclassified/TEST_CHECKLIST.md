# ManaOS統合サービス テストチェックリスト

**作成日**: 2025-01-28

---

## 📋 MCPサーバーテスト

### Unified API Server MCP
- [ ] `unified_api_health` - ヘルスチェック
- [ ] `unified_api_comfyui_generate` - 画像生成
- [ ] `unified_api_search` - 検索機能
- [ ] `unified_api_memory_store` - 記憶システム

### Step Deep Research Service MCP
- [ ] `step_deep_research_health` - ヘルスチェック
- [ ] `step_deep_research_create` - リサーチジョブ作成
- [ ] `step_deep_research_execute` - リサーチ実行
- [ ] `step_deep_research_status` - ステータス取得

### Gallery API Server MCP
- [ ] `gallery_api_health` - ヘルスチェック
- [ ] `gallery_generate_image` - 画像生成
- [ ] `gallery_get_job_status` - ジョブステータス
- [ ] `gallery_list_images` - 画像一覧

### System Status API MCP
- [ ] `system_status_health` - ヘルスチェック
- [ ] `system_status_get_all` - 全ステータス取得
- [ ] `system_status_get_simple` - 簡易ステータス
- [ ] `system_status_get_resources` - リソース情報

### SSOT API MCP
- [ ] `ssot_api_health` - ヘルスチェック
- [ ] `ssot_get` - SSOTデータ取得
- [ ] `ssot_get_summary` - サマリー取得
- [ ] `ssot_get_services` - サービス状態

### Service Monitor MCP
- [ ] `service_monitor_health` - ヘルスチェック
- [ ] `service_monitor_get_status` - 監視ステータス

### Web Voice Interface MCP
- [ ] `web_voice_health` - ヘルスチェック
- [ ] `web_voice_execute` - 音声実行
- [ ] `web_voice_text_execute` - テキスト実行
- [ ] `web_voice_status` - ステータス取得

### Portal Integration MCP
- [ ] `portal_integration_health` - ヘルスチェック
- [ ] `portal_execute` - タスク実行
- [ ] `portal_get_mode` - モード取得
- [ ] `portal_set_mode` - モード設定

### Slack Integration MCP
- [ ] `slack_integration_health` - ヘルスチェック
- [ ] `slack_send_message` - メッセージ送信
- [ ] `slack_test` - 統合テスト

### Portal Voice Integration MCP
- [ ] `portal_voice_health` - ヘルスチェック
- [ ] `portal_voice_execute` - 音声実行
- [ ] `portal_slack_execute` - Slack実行

---

## 🐳 Dockerコンテナテスト

### APIサービス
- [ ] Unified API Server (9500)
- [ ] Step Deep Research Service (5121)
- [ ] Gallery API Server (5559)
- [ ] System Status API (5112)
- [ ] SSOT API (5120)
- [ ] Service Monitor (5111)
- [ ] Web Voice Interface (5115)
- [ ] Portal Integration API (5108)
- [ ] Slack Integration (5114)
- [ ] Portal Voice Integration (5116)
- [ ] LLM Routing API (9501)
- [ ] Unified Dashboard (5130)
- [ ] Master Control (9700)

### AIサービス
- [ ] Ollama (11434)
- [ ] ComfyUI (8188)
- [ ] Stable Diffusion WebUI (7860)

### オプションサービス
- [ ] LM Studio APIプロキシ (1234)
- [ ] Free-personal-AI-Assistant (8501)
- [ ] Sara-AI-Platform (8000)

---

## 🔗 サービス間連携テスト

### Unified API → ComfyUI
- [ ] 画像生成リクエスト
- [ ] ジョブステータス確認

### Unified API → Ollama
- [ ] LLM呼び出し
- [ ] モデル一覧取得

### Gallery API → ComfyUI
- [ ] 画像生成
- [ ] 出力取得

### Portal Integration → Unified Orchestrator
- [ ] タスク実行
- [ ] ステータス確認

### Web Voice → Unified Orchestrator
- [ ] 音声コマンド実行
- [ ] 結果取得

---

## 📊 パフォーマンステスト

- [ ] レスポンス時間測定
- [ ] 同時リクエスト処理
- [ ] メモリ使用量確認
- [ ] CPU使用率確認
- [ ] GPU使用率確認（AIサービス）

---

## 🔒 セキュリティテスト

- [ ] CORS設定確認
- [ ] 環境変数の機密情報管理
- [ ] ネットワーク分離確認
- [ ] ヘルスチェックエンドポイントの保護

---

## 📝 テスト結果記録

### テスト日時
- 開始: ___________
- 終了: ___________

### テスト環境
- OS: ___________
- Docker Version: ___________
- Python Version: ___________

### 問題点
1. ___________
2. ___________
3. ___________

### 改善提案
1. ___________
2. ___________
3. ___________
