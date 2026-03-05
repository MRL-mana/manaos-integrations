# Copilot Instructions for ManaOS (manaos_integrations)

## Goal
You are assisting development and operations of ManaOS: an AI-native automation system with multiple services, routing, and operational checklists.
Always prioritize: stability, reproducibility, low cost, and operational clarity.

## Repo mental model
- `services_ledger.yaml` defines services, tiers, ports, dependencies, and blast notes.
- Operational docs:
  - `OPERATIONAL_STARTUP_CHECKLIST.md`
  - `PRODUCTION_OPERATIONS_GUIDE.md`
- Configs may include:
  - `adaptive_profile.json`
  - `*_automation_config.json`
  - `notification_*_config.json`

## Working directory rule (critical)
All commands must run from the repo root:
`C:\Users\mana4\Desktop\manaos_integrations`
Never assume the working directory is Desktop.
If suggesting VS Code Tasks, always set `options.cwd`.

## Default response style
- First: state what you inferred from files (short).
- Then: propose the smallest safe change.
- Provide exact commands and file paths.
- If there is risk, add a rollback step.

## Ops rules
- Tier 1 services (e.g. trinity/routing) are highest priority.
- Heavy services (e.g. ComfyUI) may be intentionally stopped; ask before auto-enabling.
- Prefer health checks and `check_blast_radius.py` for verification.

## When troubleshooting
1) Confirm correct cwd
2) Confirm ports with `netstat`/`Get-NetTCPConnection`
3) Read last 50 lines of relevant logs in `logs/`
4) Only then propose changes

## Naming conventions
- Tasks use `ManaOS:` prefix
- Keep new scripts and docs consistent with existing conventions

---

## プロジェクト概要

ManaOS は Mana が運用する **23サービス構成の自律型 AI オペレーティングシステム**です。
LLM ルーティング、記憶管理、パーソナリティ、秘書、自律タスク実行など複数の機能を
マイクロサービスとして協調させています。

- **ワークスペースルート**: `C:\Users\mana4\Desktop\manaos_integrations`
- **Python**: `C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe`
- **テスト**: `pytest tests/ -v`（145件以上）

---

## サービス構成（services_ledger.yaml が SSOT）

サービス一覧は `config/services_ledger.yaml` で管理されます。

### Tier 0 — コアインフラ（これが落ちると全体停止）

| サービス     | ポート  | 役割                     |
|------------|--------|--------------------------|
| ollama     | 11434  | ローカル LLM エンジン      |
| llm_routing| 5111   | LLM ルーター（SSOT）       |
| memory     | 5105   | エピソード記憶管理         |
| unified_api| 9502   | 統合 API ゲートウェイ      |

### Tier 1 — 高優先サービス

| サービス         | ポート  | 役割                       |
|----------------|--------|----------------------------|
| learning       | 5101   | 学習・最適化エンジン         |
| personality    | 5102   | パーソナリティ制御           |
| autonomy       | 5103   | 自律タスク実行              |
| secretary      | 5104   | 秘書機能（GTD 管理）        |
| trinity        | 5146   | トリニティ MCP サーバー     |
| intent_router  | 5112   | 意図分類ルーター             |
| task_queue     | 5113   | タスクキュー管理            |

### Tier 2 — オプションサービス

| サービス           | ポート  | 役割                      |
|------------------|--------|---------------------------|
| comfyui          | 8188   | 画像生成エンジン            |
| gallery          | 5559   | 生成画像ギャラリー API     |
| windows_automation| 5115  | Windows 自動化 MCP        |
| pixel7_bridge    | 5122   | Pixel7 ADB ゲートウェイ   |
| slack_integration| 5590   | Slack 通知連携             |
| step_deep_research| 5120  | 深堀りリサーチエンジン      |
| video_pipeline   | 5200   | 動画生成パイプライン        |
| voicevox         | 50000  | 音声合成エンジン            |

---

## ディレクトリ構成

```
manaos_integrations/
├── config/
│   └── services_ledger.yaml   # サービス SSOT（ポート・tier・blast_note）
├── scripts/misc/
│   ├── lessons_recorder.py    # 教訓DB（SQLite）
│   └── agent_tracker.py       # エージェントランク管理（SQLite）
├── mrl_memory_mcp_server/
│   └── server.py              # MCPサーバー（8ツール）
├── trinity_mcp_server/
│   └── server.py              # Trinity MCP（ヘルス: 5146）
├── pixel7_api_gateway.py      # Pixel7 ブリッジ（uvicorn: 5122）
├── mcp-servers/slack_integration/
│   └── slack_manaos_service.py # Slack 連携（flask: 5590）
├── file_secretary/             # 秘書 + ディープリサーチ（5120）
├── tools/
│   └── check_blast_radius.py  # 障害波及チェックツール
└── tests/                     # pytest テスト群
```

---

## 開発規則

### コミット規則

```
feat: <機能> (<N件> tests)
fix: <修正内容>
chore: <雑務・整備>
```

### テスト

```bash
# 全テスト
pytest tests/ -v

# 収集確認
python -m pytest --collect-only

# 一時出力ファイル（test_*.txt）はコミット不要（.gitignore 対象）
```

### 作業ディレクトリ

`check_blast_radius.py` や他のツールを実行するときは**必ず**
`C:\Users\mana4\Desktop\manaos_integrations` をカレントディレクトリにしてください。

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python tools\check_blast_radius.py --live --json
```

---

## MRL Memory MCP サーバー（エピソード記憶システム）

`mrl_memory_mcp_server/server.py` が提供する 8 ツール:

| ツール           | 用途                              |
|----------------|-----------------------------------|
| `memory_search`  | エピソード記憶を検索              |
| `memory_store`   | エピソード記憶を保存              |
| `memory_context` | セッション注入用コンテキスト取得  |
| `memory_metrics` | 記憶統計                         |
| `lessons_record` | 指摘教訓を記録（修正を受けたとき）|
| `lessons_search` | 教訓を検索・注入                 |
| `agent_track`    | エージェント使用履歴を記録        |
| `agent_audit`    | エージェント品質監査              |

### セッション開始プロトコル（CLAUDE.md 由来）

```python
# セッション開始時に必ず実行
lessons_search(query="", limit=20)
agent_audit()
```

---

## 障害波及（blast radius）の考え方

- Tier 0 への影響がある変更は**最高リスク**
- `config/services_ledger.yaml` の `blast_note` フィールドに各サービスの障害影響を記載
- 変更前に `python tools/check_blast_radius.py --live` で健全性を確認する

---

## サービス起動コマンド早見表

```powershell
# trinity（ヘルス: 5146）
cd C:\Users\mana4\Desktop\manaos_integrations
Start-Process python -ArgumentList "trinity_mcp_server/server.py"

# windows_automation（ヘルス: 5115）
Start-Process python -ArgumentList "-m","windows_automation_mcp_server"

# pixel7_bridge（uvicorn: 5122）
Start-Process python -ArgumentList "pixel7_api_gateway.py"

# slack_integration（flask: 5590）
Start-Process python -ArgumentList "mcp-servers/slack_integration/slack_manaos_service.py"

# comfyui（8188）— C:\mana_workspace\storage500\ComfyUI\main.py を使用
Set-Location "C:\mana_workspace\storage500\ComfyUI"
Start-Process python -ArgumentList "main.py","--port","8188","--listen","127.0.0.1"
```

---

## 重要な落とし穴

1. **cwd を間違えると全ツールが `ModuleNotFoundError`** — 常に `manaos_integrations` から実行
2. **`access_count` は初回 `1` 始まり**（`0` ではない）
3. **`lessons_search(query="")` は全件返却**（`query` 省略 = 全教訓テキスト取得）
4. **MCPサーバーのシングルトン** — `threading.Lock()` 付き。再起動不要で再利用可
5. **ComfyUI の本体コード**は `C:\mana_workspace\storage500\ComfyUI\main.py`（`C:\ComfyUI` は データ/モデルディレクトリ）

---

*Auto-generated from CLAUDE.md + services_ledger.yaml*
