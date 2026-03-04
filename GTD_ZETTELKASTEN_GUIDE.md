# MANAOS GTD + Zettelkasten ガイド

[dev.classmethod.jp の記事](https://dev.classmethod.jp/articles/ai-driven-gtd-zettelkasten/) の「AI-Driven GTD + Zettelkasten」アプローチを MANAOS に実装したシステムのガイドです。

---

## ディレクトリ構成

```
manaos_integrations/
├── gtd/                          # GTD（タスク・プロジェクト管理）
│   ├── inbox/                    # キャプチャ一時置き場（判断しない）
│   ├── next-actions/             # 次のアクション
│   │   └── items/                # 個別アクションファイル
│   ├── projects/                 # プロジェクト（2ステップ以上）
│   │   └── items/                # プロジェクト別フォルダ
│   ├── waiting/                  # 他者待ち
│   ├── someday/                  # いつかやる / もしかしたら
│   └── daily-logs/               # 日次・週次ログ
│
├── zettelkasten/                 # Zettelkasten（知識管理）
│   ├── permanent/                # 永久ノート（原子的アイデア）
│   ├── literature/               # 文献ノート（情報源の要約）
│   └── fleeting/                 # フリーティングノート（一時メモ）
│
├── skills/                       # Claude Code SKILLS（コマンド定義）
│   ├── morning_skill.mdc         # /morning  朝のルーティン
│   ├── capture_skill.mdc         # /capture  クイックキャプチャ
│   ├── inbox_skill.mdc           # /inbox    Inbox処理
│   ├── review_skill.mdc          # /review   週次レビュー
│   ├── zettel_skill.mdc          # /zettel   Permanentノート作成
│   └── insights_skill.mdc        # /insights 洞察の抽出
│
└── 00_INBOX/                     # MANAOS File Secretary Inbox（自動処理）
```

---

## 日次フロー

```
朝  /morning  → 今日の3大優先事項設定・日次ログ作成
  ↓
随時  /capture → 気になること・タスク・アイデアを即投入
  ↓
空き時間  /inbox → Inboxをゼロにする
  ↓
週1  /review  → GTD全体をリフレッシュ・Zettelkasten整理
```

---

## コマンドリファレンス

| コマンド   | 説明                         | 主な入出力                        |
|-----------|------------------------------|-----------------------------------|
| `/morning` | 朝のルーティン               | `gtd/daily-logs/YYYY-MM-DD.md` 作成 |
| `/capture` | クイックキャプチャ           | `gtd/inbox/YYYYMMDD_HHMM_*.md` 追加 |
| `/inbox`   | Inbox処理（振り分け）        | inbox → next-actions/projects等   |
| `/review`  | 週次レビュー                 | 週次サマリ + 全リスト更新         |
| `/zettel`  | Permanentノート作成          | `zettelkasten/permanent/*.md` 追加 |
| `/insights`| 知識ネットワークの洞察抽出   | 洞察レポート + 新zettel候補       |

---

## MANAOS 既存システムとの統合

| GTD/Zettelkasten要素 | 対応する MANAOS 機能              |
|---------------------|-----------------------------------|
| `/morning`           | `POST /api/secretary/morning` (port 5125) |
| Inbox 自動処理       | `00_INBOX/` + File Secretary      |
| `/research`          | `step_deep_research_service/`     |
| 洞察 (Insights)      | `rl_anything/` 学習ログ           |
| ノート保存           | Obsidian MCP (`mcp_manaos-unifie_obsidian_create_note`) |

---

## ファイル命名規則

| 種別                    | 命名規則                              |
|------------------------|---------------------------------------|
| GTD Inbox              | `YYYYMMDD_HHMM_<slug>.md`            |
| Next Actions           | `YYYYMMDD_@<context>_<action>.md`    |
| Projects               | `items/<project-slug>/_project.md`   |
| Daily Log              | `YYYY-MM-DD.md`                       |
| Weekly Review          | `YYYY-WW_weekly-review.md`           |
| Permanent Note         | `YYYYMMDD_<slug>.md`                  |
| Literature Note        | `YYYYMMDD_<source-slug>.md`          |
| Fleeting Note          | `YYYYMMDD_HHMM_<memo>.md`            |

---

## アーカイブ

完了・不要になったものは `archive/gtd/done/YYYY-MM/` に移動してください。

---

## 参考

- 元記事: https://dev.classmethod.jp/articles/ai-driven-gtd-zettelkasten/
- GTD (Getting Things Done): David Allen
- Zettelkasten: Niklas Luhmann
- MANAOS Skills: `skills/README.md`
