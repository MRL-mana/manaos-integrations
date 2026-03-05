"""copilot-instructions.md を最新版で全書き直しするユーティリティスクリプト。"""
import pathlib

content = """\
# ManaOS Copilot Instructions

このリポジトリは **ManaOS** — Mana が運用する自律型 AI オペレーティングシステム — の中核です。
23 サービスが協調し、AI 推論 / 記憶 / 自律行動 / 通知 / 画像生成などを統合しています。

---

## 最重要ルール（必ず守ること）

1. **サービス定義の SSOT は `config/services_ledger.yaml` のみ**
   - 新サービスを追加するときは必ずここに書く
   - ポート / tier / depends_on / health_url / start_cmd を全て記載する
   - `services_ledger.yaml` 以外に新しいサービス設定ファイルを作らない

2. **操作 CLI は `tools/manaosctl.py` に集約する**
   - サービス起動・停止・ヘルスチェック・イベント分析はすべて `manaosctl` 経由
   - 新しい運用コマンドは `manaosctl` のサブコマンドとして追加する
   - スタンドアロンスクリプトは最終手段（`manaosctl` に統合できない場合のみ）

3. **依存関係は `depends_on` で管理する**
   - `manaosctl up` は `depends_on` の topological sort 順で起動する
   - `heal.py` は上流サービスが DOWN なら上流を先に復旧してから下流を起動する
   - 手動で起動順を管理しない — `manaosctl up` に任せる

4. **コストリスクの高いサービスは慎重に扱う**
   - `cost_risk: high`（comfyui など）は確認してから有効化する
   - `manaosctl cost` でリスク一覧を確認してから操作する

---

## アーキテクチャ（Tier 定義）

```
Tier 0  落ちたら全滅（優先復旧）
Tier 1  主要機能が止まる
Tier 2  便利機能が止まる（最後に復旧）
```

### Tier 0 — コアインフラ

| サービス      | ポート | 役割                         | depends_on          |
|-------------|-------|------------------------------|---------------------|
| ollama      | 11434 | ローカル LLM エンジン         | —                   |
| llm_routing | 5111  | LLM ルーター（SSOT）          | ollama              |
| memory      | 5105  | エピソード記憶管理             | —                   |
| unified_api | 9502  | 統合 API ゲートウェイ          | memory, llm_routing |

### Tier 1 — 高優先サービス

| サービス        | ポート | 役割                   | depends_on                        |
|--------------|-------|------------------------|-----------------------------------|
| learning     | 5126  | 学習・最適化エンジン     | memory, unified_api               |
| personality  | 5123  | パーソナリティ制御       | memory, learning                  |
| autonomy     | 5124  | 自律タスク実行           | memory, learning, personality     |
| secretary    | 5125  | 秘書機能（GTD 管理）     | unified_api, memory               |
| trinity      | 5146  | Trinity MCP サーバー    | unified_api, memory, personality  |
| intent_router| 5100  | 意図分類ルーター          | llm_routing                       |
| task_queue   | 5104  | タスクキュー管理          | unified_api                       |

### Tier 2 — オプションサービス

| サービス             | ポート | 役割                        |
|--------------------|-------|------------------------------|
| comfyui            | 8188  | 画像生成エンジン（cost: high）|
| gallery            | 5559  | 生成画像ギャラリー API        |
| video_pipeline     | 5112  | 動画生成パイプライン           |
| windows_automation | 5115  | Windows 自動化 MCP           |
| pico_hid           | 5136  | HID マウス/キーボード MCP     |
| pixel7_bridge      | 5122  | Pixel7 ADB ゲートウェイ       |
| slack_integration  | 5590  | Slack 通知連携                |
| step_deep_research | 5120  | 深堀りリサーチエンジン          |
| n8n                | 5678  | n8n ワークフロー自動化          |
| voicevox           | 50021 | 音声合成エンジン                |

---

## manaosctl — 主要操作コマンド

```powershell
# すべて manaos_integrations/ から実行
cd C:\\Users\\mana4\\Desktop\\manaos_integrations

# 状態確認
python tools/manaosctl.py status              # 全サービス状態
python tools/manaosctl.py status --json       # JSON 出力
python tools/manaosctl.py dashboard           # タイル表示

# 起動（depends_on 順で自動ソート）
python tools/manaosctl.py up                  # Tier0+1 の auto_restart サービス
python tools/manaosctl.py up --all            # Tier2 含む全起動
python tools/manaosctl.py up trinity          # 特定サービスのみ

# 復旧
python tools/manaosctl.py heal                # DOWN サービスを自動復旧
python tools/manaosctl.py heal --dry-run      # ドライラン確認

# 依存関係（新）
python tools/manaosctl.py deps                # 全サービス依存一覧
python tools/manaosctl.py deps --order        # 起動順序リスト（topo sort）
python tools/manaosctl.py deps unified_api    # 特定サービスの上流/下流分析

# イベント・分析
python tools/manaosctl.py events              # イベント履歴（直近30件）
python tools/manaosctl.py analyze             # LLM によるイベント分析
python tools/manaosctl.py cost                # コストリスク一覧

# ポリシー
python tools/manaosctl.py policy --list       # ポリシー一覧
python tools/manaosctl.py policy --check      # ポリシー評価・実行
```

---

## イベントシステム

すべてのサービス操作は `logs/events.jsonl` に自動記録される。

```python
# tools/events.py から import
from tools.events import emit
emit("service_up", service="trinity", detail="started", source="manaosctl")
```

主要イベント種別:

- `service_down` / `service_up` — サービス状態変化
- `heal_trigger` / `heal_ok` / `heal_fail` — 自動復旧
- `cost_alert` — コストリスク警告
- `policy` — ポリシーアクション実行
- `analyze` — LLM 分析実行

Slack 通知対象: `service_down`, `heal_trigger`, `heal_fail`, `cost_alert`

---

## 自動ポリシー（config/policies.yaml）

```yaml
# 例: cost_alert_auto_stop
trigger: cost_alert
condition: { cost_risk: high, within_minutes: 30 }
action: stop
```

`manaosctl policy --check` が 5 分ごとに TaskScheduler から自動実行される。

---

## ディレクトリ構成

```
manaos_integrations/
├── config/
│   ├── services_ledger.yaml         # サービス SSOT（必ず参照）
│   └── policies.yaml                # 自動ポリシー定義
├── tools/
│   ├── manaosctl.py                 # 統合 CLI（メイン操作窓口）
│   ├── heal.py                      # 自動復旧エンジン
│   └── events.py                    # イベントログ共有ライブラリ
├── logs/
│   ├── events.jsonl                 # 全イベントログ（SSOT）
│   ├── events.summary.json          # 直近レポートサマリー
│   └── heal.log                     # 復旧ログ
├── scripts/misc/
│   ├── manaos_daily_report.py       # 1時間おき AI 日報
│   └── manaos_dashboard_server.py   # Control Panel (port 9800)
├── static/
│   └── dashboard.html               # Web UI (http://127.0.0.1:9800)
├── mrl_memory_mcp_server/           # エピソード記憶 MCP（8 ツール）
├── trinity_mcp_server/              # Trinity エージェント MCP
└── tests/                           # pytest テスト群（145 件以上）
```

---

## 作業ディレクトリ（Critical）

**すべてのコマンドはここから実行する：**

```
C:\\Users\\mana4\\Desktop\\manaos_integrations
```

VS Code Tasks を追加するときは必ず `options.cwd` を設定する。  
`Desktop` からの実行は `ModuleNotFoundError` の原因になる。

---

## トラブルシューティング手順

1. `python tools/manaosctl.py status` でサービス状態を確認
2. `python tools/manaosctl.py deps <name>` で上流障害を確認
3. ポート確認: `Get-NetTCPConnection -LocalPort <port>`
4. `logs/` の直近 50 行を確認
5. それでも不明なら `python tools/manaosctl.py analyze` で LLM に診断させる

---

## コーディング規則

- **新サービスの追加**: `services_ledger.yaml` → `manaosctl` の起動コマンド追加 → `health_url` 必須
- **新 CLI コマンド**: `manaosctl.py` の `dispatch` に追加（スタンドアロンスクリプト禁止）
- **イベント記録**: 重要な操作は `tools/events.emit()` で記録する
- **Python バージョン**: 3.10（`C:\\Users\\mana4\\AppData\\Local\\Programs\\Python\\Python310\\python.exe`）
- **コミットメッセージ**: `feat(scope):` / `fix(scope):` / `chore(scope):`
- **VS Code タスク名**: `ManaOS: ` プレフィックス必須

---

## MRL Memory MCP（エピソード記憶システム）

`mrl_memory_mcp_server/server.py` の主要ツール:

| ツール            | 用途                          |
|----------------|-----------------------------|
| `memory_search`  | エピソード記憶を検索            |
| `memory_store`   | エピソード記憶を保存            |
| `memory_context` | セッション注入用コンテキスト    |
| `lessons_record` | 指摘・修正を教訓として記録      |
| `lessons_search` | 教訓を検索・注入               |
| `agent_track`    | エージェント使用履歴を記録      |
| `agent_audit`    | エージェント品質監査            |

---

## 自動化サイクル（TaskScheduler）

| タスク                    | 間隔      | 内容                          |
|-------------------------|-----------|-------------------------------|
| ManaOS_StartAllServices  | PC 起動時 | Tier0+1 サービス全起動         |
| ManaOS_ControlPanel      | ログオン時 | Dashboard 起動 (port 9800)    |
| ManaOS_PolicyCheck       | 5 分おき  | ポリシー評価・自動停止/通知     |
| ManaosHealServices       | 15 分おき | DOWN サービス自動復旧           |
| ManaOS_HourlyAnalysis    | 1 時間おき| AI 日報生成 + summary.json 更新|

---

## 既知の落とし穴

1. `access_count` は初回 `1` から始まる（`0` ではない）
2. `lessons_search(query="")` は全件返却（`query` 省略 = 全教訓取得）
3. ComfyUI の本体コードは `C:\\mana_workspace\\storage500\\ComfyUI\\main.py`
4. Tier 1 ポートは `5123`/`5124`/`5125`/`5126` — 古いドキュメントの `5101`-`5104` は誤り
5. `.github/copilot-instructions.md` は LF (`\\n`) で保存する（CRLF だと replace_string_in_file が失敗する）

---

*Auto-updated: 2026-03-05 | commit 093a5d7+*
"""

dest = pathlib.Path(r'C:\Users\mana4\Desktop\manaos_integrations\.github\copilot-instructions.md')
dest.write_text(content, encoding='utf-8')
print(f"WRITTEN: {len(content)} chars -> {dest}")
