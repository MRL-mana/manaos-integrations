# scripts/

ManaOS Integrations のスクリプト集。

## 起動・疎通確認

| スクリプト | 用途 |
|------------|------|
| `check_manaos_stack.ps1` | 統合API (9500)・MoltBot (8088) の疎通確認 |
| `check_manaos_stack.ps1 -Extended` | 上記＋Portal/SystemStatus/SSOT/StepDeepResearch/Gallery/ServiceMonitor |
| `check_manaos_stack.bat` | 上記の .bat ラッパー |
| `check_mcp_health.ps1` | MCP サーバー（manaos-unified, ltx2, phase1）の list_tools 検証 |
| `check_mcp_health.py` | 同上の Python 実装 |

## Skills 実行

| スクリプト | 用途 |
|------------|------|
| `apply_skill_daily_ops.py` | 日次運用 YAML 実行 |
| `apply_skill_drive_backup.py` | Google Drive バックアップ YAML 実行 |
| `apply_skill_git_ops.py` | Git 操作 YAML 実行 |
| `apply_skill_n8n_workflow.py` | n8n ワークフロー YAML 実行 |
| `apply_skill_*` | 他 10 種（Notion, Rows, DB, ログ分析等） |

→ 詳細: [skills/README.md](../skills/README.md), [SKILLS_AND_MCP_GUIDE.md](../docs/guides/SKILLS_AND_MCP_GUIDE.md)

## Skills 支援

| スクリプト | 用途 |
|------------|------|
| `obsidian_cli.py` | Obsidian ノート作成・検索 |
| `slack_cli.py` | Slack メッセージ送信 |
| `skill_scheduler.py` | Skills の定期実行 |
| `auto_skill_runner.py` | Skills の自動実行 |

## デバイス・オーケストレーター

| スクリプト | 用途 |
|------------|------|
| `quick_start_devices.ps1` | デバイスまとめて起動（リポジトリルート） |
| `start_orchestrator_production.ps1` | オーケストレーター本番起動 |
| `install_devices_health_check_schedule.ps1` | デバイスヘルスチェックのスケジュール登録 |
| `install_pixel7_bridge_autostart.ps1` | Pixel 7 ブリッジの自動起動設定 |

## 音声

| スクリプト | 用途 |
|------------|------|
| `voice/check_voice_ready.bat` | 音声機能の事前チェック |
| `voice/start_pixel7_realtime_voice.bat` | Pixel 7 リアルタイム音声 |
| `voice/start_unified_api_with_voice.bat` | 統合API＋音声起動 |

## その他

| スクリプト | 用途 |
|------------|------|
| `install_requirements.ps1` | 依存関係インストール |
| `upgrade_packages_safe.ps1` | パッケージ安全アップグレード |
| `security/scan_secrets.py` | シークレット漏洩スキャン |
| `windows/install_unified_api_service.ps1` | 統合API を Windows サービスとして登録 |

## 参照

- [STARTUP_DEPENDENCY.md](../docs/guides/STARTUP_DEPENDENCY.md)
- [QUICK_REFERENCE.md](../docs/QUICK_REFERENCE.md)
