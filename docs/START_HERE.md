# ManaOS — START HERE

> **AIも人間も、最初にここを読む。**
> このファイルが「ManaOSの地図」です。

---

## 3つの入口文書（これだけ読めば動く）

| 文書 | 対象 | 内容 |
|------|------|------|
| [README.md](../README.md) | 人間・AI | 最短起動手順・構成概要 |
| [.github/copilot-instructions.md](../.github/copilot-instructions.md) | Copilot/Cursor | コーディングルール・コマンド全覧 |
| **docs/START_HERE.md**（このファイル） | 人間・AI | 詳細地図・どこに何があるか |

**AIへ** : 上の3ファイルを読んだら、他を読む必要はほぼない。詳細は後述の各セクションへ。

---

## ManaOSとは何か（一言）

> **「Unified API（9502）を入口とする自律型AI OS」**

```
外部 / VS Code / Cursor
        ↓
  Unified API (9502)   ← 全操作の入口
        ↓
  [Tier 0] 推論・記憶・ルーティング
        ↓
  [Tier 1] 学習・人格・自律・秘書
        ↓
  [Tier 2] 画像・自動化・通知（必要な時だけ）
```

---

## Tier マップ（完全版）

### Tier 0 — 落ちたら全滅（最優先復旧）

| サービス | ポート | 役割 |
|---------|-------|------|
| ollama | 11434 | ローカル LLM エンジン |
| llm_routing | 5111 | LLM ルーター（SSOT） |
| memory | 5105 | エピソード記憶 |
| unified_api | 9502 | **全操作の入口** |

### Tier 1 — 主要機能（なるべく常時UP）

| サービス | ポート | 役割 |
|---------|-------|------|
| learning | 5126 | 学習・最適化 |
| personality | 5123 | パーソナリティ制御 |
| autonomy | 5124 | 自律タスク実行 |
| secretary | 5125 | 秘書（GTD管理） |
| trinity | 5146 | Trinity MCP |
| intent_router | 5100 | 意図分類 |
| task_queue | 5104 | タスクキュー |

### Tier 2 — オプション（必要な時だけ有効化）

| サービス | ポート | 備考 |
|---------|-------|------|
| comfyui | 8188 | ⚠ cost_risk: high |
| gallery | 5559 | comfyui依存 |
| video_pipeline | 5112 | 動画生成 |
| windows_automation | 5115 | Windows MCP |
| pico_hid | 5136 | HID MCP |
| pixel7_bridge | 5122 | Pixel7 ADB |
| slack_integration | 5590 | Slack通知 |
| step_deep_research | 5120 | 深堀りリサーチ |
| n8n | 5678 | ワークフロー |
| voicevox | 50021 | 音声合成 |

> **ポート番号のSSOT** = `config/services_ledger.yaml`（このファイルは簡易版）

---

## どこに何があるか（完全ディレクトリマップ）

```
manaos_integrations/
│
├── 📌 入口（最初に見る）
│   ├── README.md                  人間向け最短導線
│   ├── .github/copilot-instructions.md  AIルール
│   └── docs/START_HERE.md         ← いまここ
│
├── ⚙ 設定（SSOT群）
│   ├── config/services_ledger.yaml  サービス唯一の真実
│   └── config/policies.yaml         自動ポリシー定義
│
├── 🔧 運用CLI
│   ├── tools/manaosctl.py           統合CLI（メイン）
│   ├── tools/heal.py                自動復旧エンジン
│   └── tools/events.py              イベントログ共有
│
├── 📊 監視・分析
│   ├── logs/events.jsonl            全イベントログ
│   ├── logs/events.summary.json     サマリー（長期記憶）
│   └── scripts/misc/manaos_dashboard_server.py  Web UI (9800)
│
├── 🧠 コアサービス（Tier0-1）
│   ├── mrl_memory_mcp_server/       記憶MCP（8ツール）
│   ├── learning_system_mcp_server/  学習MCP
│   ├── personality_mcp_server/      パーソナリティMCP
│   ├── trinity_mcp_server/          Trinity MCP
│   └── manaos_llm_routing_api/      LLMルーター
│
├── 🔌 Tier2統合サービス
│   ├── comfyui/                     画像生成
│   ├── gallery_api_server/          ギャラリーAPI
│   ├── moltbot_gateway/             MoltBot
│   ├── n8n_mcp_server/              n8n連携
│   └── pico_hid/                    HID制御
│
├── 🧪 実験（Tier3 — 検索除外済み）
│   ├── experiments/
│   ├── ltx2/                       動画生成実験
│   └── castle_ex/                  実験AI
│
├── 📦 アーカイブ（検索除外済み）
│   ├── archive/
│   ├── artifacts/
│   ├── outputs/ / output/
│   └── gallery_images/ / generated_images/
│
└── 📚 ドキュメント
    ├── docs/guides/                 各種ガイド
    └── docs/START_HERE.md          ← このファイル
```

---

## manaosctl クイックリファレンス

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations

# 毎朝確認
python tools/manaosctl.py status

# 何か落ちてたら
python tools/manaosctl.py deps <サービス名>   # 上流障害チェック
python tools/manaosctl.py heal               # 自動復旧

# 異常が続くなら
python tools/manaosctl.py analyze            # LLMに診断させる

# Control Panel
Start-Process 'http://127.0.0.1:9800/'
```

---

## 自律・ポリシーシステム

```
Policy（config/policies.yaml）
    ↓ 5分おきに評価（TaskScheduler: ManaOS_PolicyCheck）
    ↓ trigger条件マッチ → action実行
    ↓ events.jsonl に記録

Autonomy Level:
  read-only   → 情報取得のみ
  suggest     → 提案のみ（人間が承認）
  execute     → 自動実行（runbook定義済みのもののみ）
```

**「実行して良い手順を定義して許可する」** がManaOSの自律哲学。なんでも実行はしない。

---

## トラブルシューティング（5ステップ）

1. `python tools/manaosctl.py status` — 全体状況把握
2. `python tools/manaosctl.py deps <name>` — 上流障害確認
3. `Get-NetTCPConnection -LocalPort <port>` — ポート確認
4. `Get-Content logs/events.jsonl -Tail 30` — 直近イベント
5. `python tools/manaosctl.py analyze` — LLM診断

---

## よくある落とし穴

| 問題 | 原因 | 解決 |
|------|------|------|
| `ModuleNotFoundError` | cwd が違う | `manaos_integrations/` から実行 |
| サービスが起動しない | 上流がDOWN | `manaosctl deps <name>` で確認 |
| ポート衝突 | 二重起動 | `Get-NetTCPConnection -LocalPort <port>` |
| APIキー切れ | 環境変数未設定 | `.env` を確認 |
| Tier1ポート混乱 | 旧資料の誤り | 正しくは 5123/5124/5125/5126（5101-5104ではない） |

---

*このファイルは `docs/START_HERE.md` — 更新は `manaos_integrations/` ルートからの変更に合わせて維持する。*
