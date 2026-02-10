# Skills と MCP の使い分けガイド

最終更新: 2026-02-06

> 他の Skills ドキュメントは [SKILLS_INDEX.md](SKILLS_INDEX.md) を参照。

---

## 方針（一元化）

| 種別 | 用途 | トークン | 呼び出し |
|------|------|----------|----------|
| **Skills（YAML型）** | 反復的・確定的な業務 | 最小 | AI が YAML 出力 → スクリプト実行 |
| **MCP** | 文脈が必要な・リアルタイムな操作 | 多い | Cursor がツール直接呼び出し |
| **Rules（.mdc）** | ManaOS 固有の知識・手順 | - | AI が自動参照 |

---

## Skills を使う場面

- **日次運用**（日報→Obsidian / Slack）
- **バックアップ**（Google Drive 等）
- **Git 操作**（commit, push, pull, tag）
- **n8n ワークフロー**（activate, deactivate, execute, import）
- **データベース / Rows / Notion** などの定型操作
- **サーバー監視・復旧**（YAML で定義）
- **ログ分析・メール送信・カレンダー** などの定型処理

**理由**: フォーマットが決まっていて、トークンを使わずスクリプトで一括処理できる。

| Skill | スクリプト |
|-------|-----------|
| daily_ops | `scripts/apply_skill_daily_ops.py` |
| drive_backup | `scripts/apply_skill_drive_backup.py` |
| git_ops | `scripts/apply_skill_git_ops.py` |
| n8n_workflow | `scripts/apply_skill_n8n_workflow.py` |
| notion_ops | `scripts/apply_skill_notion_ops.py` |
| server_monitor | `scripts/apply_skill_server_monitor.py` |
| database_ops | `scripts/apply_skill_database_ops.py` |
| rows_ops | `scripts/apply_skill_rows_ops.py` |
| file_organize | `scripts/apply_skill_file_organize.py` |
| data_transform | `scripts/apply_skill_data_transform.py` |
| log_analysis | `scripts/apply_skill_log_analysis.py` |
| email_ops | `scripts/apply_skill_email_ops.py` |
| calendar_ops | `scripts/apply_skill_calendar_ops.py` |
| db_backup | `scripts/apply_skill_db_backup.py` |

→ 詳細: [skills/README.md](../../skills/README.md)
→ 方針決定: [SKILLS_INTEGRATION_DECISION.md](SKILLS_INTEGRATION_DECISION.md)

---

## MCP を使う場面

- **画像・動画生成**（ComfyUI, SVI, LTX-2）
- **オーケストレーターへの自然文問い合わせ**（ask_orchestrator）
- **デバイス状態取得**（device_get_status, device_discover）
- **MoltBot 秘書ファイル整理**（moltbot_submit_plan, moltbot_get_result）
- **LLM チャット**（llm_chat）
- **Obsidian 検索・ノート作成**（リアルタイム・文脈あり）
- **Rows 自然言語クエリ**（rows_query）
- **Phase1 実験**（phase1_run_off, phase1_run_on 等）

**理由**: ユーザー意図・文脈・リアルタイム性が必要で、ツール呼び出しが適切。

→ 詳細: [MCP_SERVERS_GUIDE.md](MCP_SERVERS_GUIDE.md)

---

## Rules（.mdc）の役割

`.cursor/rules/` にある ManaOS 固有のルール：

| ファイル | 内容 |
|----------|------|
| manaos-media-skill.mdc | 画像・動画生成の使い分け、トラブル時手順 |
| manaos-orchestrator-skill.mdc | 母艦・このは・X280・Pixel7 の役割、オーケストレーター問い合わせ |
| manaos-system3-skill.mdc | Learning / Intrinsic / Todo / Personality / Autonomy の役割 |
| manaos-voice-skill.mdc | 音声 STT/TTS、起動確認 |

AI が自動参照するため、MCP や Skills の使い分け判断に活用される。

---

## クイック判断フロー

```
ユーザー依頼
    │
    ├─ 定型・反復・バッチ向き？
    │      → Skills（YAML 出力 → apply_skill_*.py）
    │
    └─ 文脈・リアルタイム・生成系？
           → MCP（manaos-*, unified-api, ltx2, phase1 等）
```

---

## 関連ドキュメント

- [MCP サーバー一覧](MCP_SERVERS_GUIDE.md)
- [Skills README](../../skills/README.md)
- [QUICK_REFERENCE](../QUICK_REFERENCE.md)
