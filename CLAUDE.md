# ManaOS Development Context

このファイルは Claude Code がセッション開始時に自動読み込みします。  
以下のルールを**必ず順守してセッションを開始すること**。

---

## 🚀 セッション開始時の必須手順

### Step 1 — 過去の教訓を注入する

```
lessons_search(query="", limit=20)
```

- 過去に指摘・修正されたパターンを取得し、コンテキストに注入する
- **これを省略すると同じミスを繰り返す** → 必ず最初に実行すること
- `category` フィルタで絞り込む場合: `"output_format"` / `"behavior"` / `"technical"` / `"context"`

### Step 2 — エージェント品質を確認する

```
agent_audit(agents_dir="~/.claude/agents")
```

- 全エージェント定義の品質スコア（100点満点）を確認する
- **70点未満のエージェントがあれば、そのセッション中に改善を提案する**
- `agents_dir` は省略可（デフォルト `~/.claude/agents`）

---

## 📝 指摘・修正があったとき

ユーザーが以下のような表現をした場合、**必ず `lessons_record` を呼ぶ**:

- 「〜は違う」「〜にしてほしい」「なんで〜するの？」
- コードや出力を修正させた場合
- 「NG」「駄目」「直して」などの修正指示

```
lessons_record(
    instruction="<1文で教訓をまとめる>",
    category="<output_format|behavior|technical|context>",
    trigger_text="<ユーザーの発言そのまま（省略可）>",
    session_id="<セッションIDまたは日付 YYYY-MM-DD>",
)
```

**カテゴリ選択ガイド**:
| カテゴリ | 対象 |
|---------|------|
| `output_format` | Markdown書式、コードブロック、リスト形式など表示に関するミス |
| `behavior` | エージェントの振る舞い・判断・優先順位に関するミス |
| `technical` | コード・ライブラリ・API に関するミス |
| `context` | プロジェクト固有の前提・ファイル構成・命名規則に関するミス |

---

## 🤖 サブエージェント（Task）を呼んだとき

Task ツールで Sub-agent を呼んだ直後に **必ず `agent_track` を呼ぶ**:

```
agent_track(
    agent_name="<エージェント名（.mdのbasename）>",
    task_summary="<何をやらせたかを1文で>",
    session_id="<日付 YYYY-MM-DD>",
)
```

- ランクは自動算出: N → N-C → N-B → N-A → N-S（使用0/1/5/10/20回）
- ランク履歴が蓄積されることで「よく使うエージェント」が可視化される

---

## 🏗️ プロジェクト固有の規則

### テスト
- `pytest tests/ -v` で全テスト実行（145件以上）
- テスト一時ファイル (`test_*.txt`) は `.gitignore` 対象 → コミット不要
- テスト前に `python -m pytest --collect-only` で収集確認

### コミット規則
```
feat: <機能> (<N件> tests)
fix: <修正内容>
chore: <雑務・整備>
```

### ファイル構成
```
manaos_integrations/
├── scripts/misc/
│   ├── lessons_recorder.py   # 教訓DB (SQLite)
│   └── agent_tracker.py      # エージェントランク管理 (SQLite)
├── mrl_memory_mcp_server/
│   └── server.py             # MCPサーバー (8ツール)
└── tests/                    # pytest テスト群
```

### MCPサーバー（MRL Memory）
| ツール | 用途 |
|--------|------|
| `memory_search` | エピソード記憶を検索 |
| `memory_store` | エピソード記憶を保存 |
| `memory_context` | セッション注入用コンテキスト取得 |
| `memory_metrics` | 記憶統計 |
| `lessons_record` | 指摘教訓を記録 |
| `lessons_search` | 教訓を検索・注入 |
| `agent_track` | エージェント使用を記録 |
| `agent_audit` | エージェント品質監査 |

---

## ⚠️ 既知の落とし穴

1. **`access_count` は初回 `1` から始まる**（`0` ではない）
2. **`lessons_search(query="")` は全件返却** — `query` を省略すると全教訓テキストが得られる
3. **`agent_tracker` の `:memory:` DB** — テスト時のみ使用、本番は `~/.manaos/agent_tracker.db`
4. **MCPサーバーのシングルトン** — `_lessons_recorder` / `_agent_tracker` は `threading.Lock()` 付き。再利用可

---

*最終更新: セッション開始時に自動生成 by GitHub Copilot*

<!-- LESSONS_AUTO_START -->

## 📖 最新教訓ログ（自動注入）

> 自動更新: 2026-03-08 07:42  |  合計 **0** 件  |  なし
> このセクションは `inject_lessons_to_claude_md.py` が自動更新します。手動編集不可。

*教訓はまだ記録されていません。*

<!-- LESSONS_AUTO_END -->
