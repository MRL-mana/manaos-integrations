# 母艦・まなOS・サーバー 棚卸し

最終更新: 2025-02-01

> **関連**: 機能・システム・MCP・ツールは `棚卸し_機能システムMCPツール一覧.md`、このはサーバー実機詳細は `棚卸し_このはサーバー詳細.md` を参照

## 1. デバイス構成（全体像）

| デバイスID | 名前 | 種別 | Tailscale IP | 役割 |
|-----------|------|------|--------------|------|
| **mothership** | 母艦 | Windows 11 + WSL (Linux)、**GPUあり** | マナ等 | 開発・運用のメインマシン。ComfyUI、画像・動画生成。manaos_integrations の実行元 |
| **x280** | X280 | ThinkPad Windows | 100.127.121.20（デスクトップasmrkim） | 別PC、SSOT API 等 |
| **konoha** | このはサーバー（Konoha） | **レンタルサーバー（VPS）** Linux VM | 100.93.120.33（vm-8a8820e4-c5-1） | ManaOS Orchestrator、n8n、計算・ストレージ |
| **pixel7** | Pixel 7 | Android | 100.84.2.125 等 | カメラ・ストレージ |

> **注意**: **このはサーバー = Konoha** は同じマシン。レンタルサーバー（VPS）のため SSH・Docker でアクセス可能。

### 関係図（概要）

```
[母艦 Windows + WSL] ←→ manaos_integrations（リポジトリ）
     │
     ├─ ローカル起動: 統合API(9500), System3(5103,5126,5130,5134) 等
     │
     ├─ Tailscale 経由 ─┬─ X280 (100.127.121.20:5120)
     │                  ├─ このは/Konoha (100.93.120.33:5106) ※レンタルVPS
     │                  └─ Pixel7 (100.84.2.125 等)
     │
     └─ ファイル同期: mothership ↔ x280 ↔ konoha (ManaOS_Sync)
```

---

## 2. 母艦（Mothership）で動く主なもの

母艦 = Windows 11 + WSL（Linux サブシステム内蔵）、**GPU 搭載**

### 2.1 統合API・LLM

| ポート | サービス | スクリプト | 備考 |
|--------|----------|------------|------|
| **9502** | ManaOS 統合API | `unified_api_server.py` | メインエントリ。外部サービス連携の窓口 |
| **5111** | LLM Routing MCP | `llm_routing_mcp_server` | LM Studio / Ollama のルーティング（healthのみ） |

### 2.2 コア・オーケストレーション（51xx系）

| ポート | サービス | スクリプト |
|--------|----------|------------|
| 5100 | Intent Router | `intent_router.py` |
| 5101 | Task Planner | `task_planner.py` |
| 5102 | Task Critic | `task_critic.py` |
| 5103 | RAG Memory | `rag_memory_enhanced.py` |
| 5104 | Task Queue | `task_queue_system.py` |
| 5105 | UI Operations | `ui_operations_api.py` |
| 5106 | Unified Orchestrator | `unified_orchestrator.py` |
| 5107 | Executor Enhanced | `task_executor_enhanced.py` |
| 5108 | Portal Integration | `portal_integration_api.py` |
| 5109 | Content Generation | `content_generation_loop.py` |
| 5110 | LLM Optimization | `llm_optimization.py` |
| 5111 | Service Monitor | `service_monitor.py` |
| 5112 | System Status API | `system_status_api.py` |

### 2.3 拡張・System3（51xx〜53xx系）

| ポート | サービス | スクリプト |
|--------|----------|------------|
| 5121 | Step Deep Research | `step_deep_research_service.py` |
| 5123 | Personality System | `personality_system.py` |
| 5124 | Autonomy System | `autonomy_system.py` |
| 5125 | Secretary System | `secretary_system.py` |
| 5126 | Learning System API | `learning_system_api.py` |
| 5127 | Metrics Collector | `metrics_collector.py` |
| 5128 | Performance Dashboard | `performance_dashboard.py` |
| 5130 | Intrinsic Score API | `intrinsic_motivation.py` |
| 5134 | Todo Queue API | `intrinsic_todo_queue.py` |

### 2.4 その他（Slack / UI 等）

| ポート | サービス | 備考 |
|--------|----------|------|
| 5114 | Slack Integration | ngrok で外部公開 |
| 9601 | Evaluation UI | 評価用ダッシュボード |

---

## 3. このはサーバー（Konoha）構成

**このはサーバー = Konoha** は同一。レンタルサーバー（VPS）で、SSH・Docker でフルアクセス可能。

### 3.1 このはサーバー（Konoha）

- **種別**: レンタルサーバー（VPS・Linux VM）
- **Tailscale**: 100.93.120.33（vm-8a8820e4-c5-1）
- **アクセス**: `ssh konoha`、`scp konoha:/path`
- **ポート**: 5106（ManaOS Orchestrator）、5678（n8n）
- **機能**: compute, storage
- **用途**: ManaOS オーケストレーター、n8n (Trinity)

### 3.2 X280

- **IP**: 100.127.121.20（Tailscale、デスクトップasmrkim）
- **ポート**: 5120（SSOT API）
- **備考**: 母艦とは別の ThinkPad Windows PC

---

## 4. 外部サービス・インフラ

| サービス | デフォルトURL | 用途 |
|----------|---------------|------|
| ComfyUI | http://127.0.0.1:8188 | 画像生成 |
| Ollama | http://127.0.0.1:11434 | LLM 実行 |
| LM Studio | http://127.0.0.1:1234/v1 | LLM 実行 |
| n8n | http://127.0.0.1:5678 or 5679 | ワークフロー自動化 |

---

## 5. 起動スクリプト一覧

| スクリプト | 内容 |
|------------|------|
| `start_all_manaos_services.ps1` | コア〜拡張サービス + 統合API（9500）を一括起動 |
| `start_system3_services.ps1` | System3 系のみ（Intrinsic 5130, Todo 5134, Learning 5126, RAG 5103） |
| `start_all_llm_services_auto.ps1` | LM Studio + LLM Routing API（9501） |
| `start_all_services.ps1` | 統合API(9500) + LLM Routing(9501) |
| `auto_restart_services.ps1` | LM Studio, LLM Routing, 統合API の監視・自動再起動 |

---

## 6. 設定ファイル

| ファイル | 用途 |
|----------|------|
| `device_orchestrator_config.json` | デバイス一覧・エンドポイント定義 |
| `device_health_config.json` | デバイス監視設定（自動生成される場合あり） |
| `cross_platform_sync_config.json` | mothership / x280 / konoha 間の同期ルール |
| `env.example` | 環境変数のサンプル（実値は `.env` に） |

---

## 7. 確認用コマンド

```powershell
# サービス状態確認
python check_service_status.py

# System3 ヘルスチェック
python system3_health_check.py

# デバイス監視
python device_health_monitor.py
```

---

## 8. まとめチェックリスト

- [ ] **母艦**: 統合API(9500), LLM Routing(9501), System3 系が期待どおり起動しているか
- [ ] **このは/Konoha（レンタルVPS）**: 100.93.120.33:5106 に接続できるか（Tailscale が有効か）
- [ ] **X280**: 100.127.121.20:5120 に接続できるか
- [ ] **ファイル同期**: mothership ↔ x280 ↔ konoha の ManaOS_Sync が正常か
- [ ] **外部サービス**: ComfyUI, Ollama, n8n が必要なら起動しているか
